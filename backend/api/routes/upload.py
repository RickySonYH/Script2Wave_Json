# [advice from AI] 파일 업로드 API 라우터
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid
import os
import aiofiles

from backend.config import get_settings
from backend.database import get_db
from backend.models.job import Job, JobStatus, JobResponse
from backend.core.processor import process_script

router = APIRouter()


@router.post("/", response_model=JobResponse)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    단일 대화록 파일 업로드 및 작업 생성
    """
    settings = get_settings()
    
    # 파일 확장자 검증
    if file.filename and not file.filename.endswith(('.txt', '')):
        # 확장자 없는 파일도 허용 (SampleCon1 같은 경우)
        pass
    
    # 고유 파일명 생성
    job_id = str(uuid.uuid4())
    safe_filename = f"{job_id}_{file.filename or 'script'}"
    file_path = os.path.join(settings.upload_dir, safe_filename)
    
    # 파일 저장
    try:
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 저장 실패: {str(e)}")
    
    # 작업 생성
    job = Job(
        id=job_id,
        filename=safe_filename,
        original_filename=file.filename or "script",
        status=JobStatus.PENDING,
        progress=0,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    
    # 백그라운드에서 처리 시작
    background_tasks.add_task(process_script, job_id)
    
    return JobResponse.model_validate(job)


@router.post("/batch", response_model=List[JobResponse])
async def upload_files_batch(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    다중 대화록 파일 업로드 (배치)
    """
    settings = get_settings()
    jobs_created = []
    
    for file in files:
        job_id = str(uuid.uuid4())
        safe_filename = f"{job_id}_{file.filename or 'script'}"
        file_path = os.path.join(settings.upload_dir, safe_filename)
        
        # 파일 저장
        try:
            async with aiofiles.open(file_path, 'wb') as f:
                content = await file.read()
                await f.write(content)
        except Exception as e:
            # 실패한 파일은 건너뛰고 계속 진행
            continue
        
        # 작업 생성
        job = Job(
            id=job_id,
            filename=safe_filename,
            original_filename=file.filename or "script",
            status=JobStatus.PENDING,
            progress=0,
        )
        db.add(job)
        jobs_created.append(job)
    
    await db.commit()
    
    # 각 작업에 대해 백그라운드 처리 시작
    for job in jobs_created:
        await db.refresh(job)
        background_tasks.add_task(process_script, job.id)
    
    return [JobResponse.model_validate(job) for job in jobs_created]


@router.post("/preview")
async def preview_script(
    file: UploadFile = File(...),
):
    """
    대화록 미리보기 (파싱 결과 확인)
    """
    from backend.core.parser import parse_script
    
    content = await file.read()
    text = content.decode('utf-8')
    
    try:
        parsed = parse_script(text)
        return {
            "success": True,
            "dialogue_count": len(parsed.dialogues),
            "dialogues": [
                {
                    "speaker": d.speaker,
                    "text": d.text[:100] + "..." if len(d.text) > 100 else d.text,
                    "actions": d.actions,
                    "delays": d.delays,
                }
                for d in parsed.dialogues[:10]  # 최대 10개만 미리보기
            ],
            "has_summary": parsed.summary is not None,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }

