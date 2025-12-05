# [advice from AI] 파일 관리 API 라우터 - Range 요청 지원 추가
from fastapi import APIRouter, HTTPException, Depends, Request, Header
from fastapi.responses import FileResponse, StreamingResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import os
import zipfile
import io
from urllib.parse import quote

from backend.config import get_settings
from backend.database import get_db
from backend.models.job import Job, JobStatus

router = APIRouter()


@router.get("/{job_id}/download")
async def download_file(
    job_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    생성된 WAVE 파일 다운로드
    """
    settings = get_settings()
    
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")
    
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail="아직 완료되지 않은 작업입니다."
        )
    
    if not job.output_filename:
        raise HTTPException(
            status_code=404,
            detail="출력 파일이 없습니다."
        )
    
    file_path = os.path.join(settings.output_dir, job.output_filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail="파일을 찾을 수 없습니다."
        )
    
    # 다운로드 파일명 생성 (원본 이름 기반)
    download_name = f"{os.path.splitext(job.original_filename)[0]}.wav"
    
    return FileResponse(
        path=file_path,
        filename=download_name,
        media_type="audio/wav",
    )


@router.get("/{job_id}/stream")
async def stream_audio(
    job_id: str,
    request: Request,
    range: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """
    오디오 스트리밍 (미리 듣기용) - Range 요청 지원
    """
    settings = get_settings()
    
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    
    if not job or job.status != JobStatus.COMPLETED or not job.output_filename:
        raise HTTPException(status_code=404, detail="재생 가능한 파일이 없습니다.")
    
    file_path = os.path.join(settings.output_dir, job.output_filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
    
    file_size = os.path.getsize(file_path)
    
    # Range 요청 처리 (브라우저 오디오 재생 지원)
    if range:
        try:
            range_str = range.replace("bytes=", "")
            start_str, end_str = range_str.split("-")
            start = int(start_str) if start_str else 0
            end = int(end_str) if end_str else file_size - 1
            
            if start >= file_size:
                raise HTTPException(status_code=416, detail="Range not satisfiable")
            
            end = min(end, file_size - 1)
            content_length = end - start + 1
            
            def iter_file():
                with open(file_path, "rb") as f:
                    f.seek(start)
                    remaining = content_length
                    while remaining > 0:
                        chunk_size = min(8192, remaining)
                        data = f.read(chunk_size)
                        if not data:
                            break
                        remaining -= len(data)
                        yield data
            
            return StreamingResponse(
                iter_file(),
                status_code=206,
                media_type="audio/wav",
                headers={
                    "Content-Range": f"bytes {start}-{end}/{file_size}",
                    "Accept-Ranges": "bytes",
                    "Content-Length": str(content_length),
                },
            )
        except ValueError:
            pass
    
    # Range 요청이 없는 경우 전체 파일 반환
    return FileResponse(
        path=file_path,
        media_type="audio/wav",
        headers={
            "Accept-Ranges": "bytes",
            "Content-Length": str(file_size),
        },
    )


# [advice from AI] 발화 정보 JSON 파일 다운로드 API 추가
@router.get("/{job_id}/download-json")
async def download_json(
    job_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    발화 정보 JSON 파일 다운로드
    """
    settings = get_settings()
    
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")
    
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail="아직 완료되지 않은 작업입니다."
        )
    
    if not job.json_filename:
        raise HTTPException(
            status_code=404,
            detail="JSON 파일이 없습니다."
        )
    
    file_path = os.path.join(settings.output_dir, job.json_filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail="JSON 파일을 찾을 수 없습니다."
        )
    
    # 다운로드 파일명 생성 (원본 이름 기반)
    download_name = f"{os.path.splitext(job.original_filename)[0]}.json"
    
    return FileResponse(
        path=file_path,
        filename=download_name,
        media_type="application/json",
    )


@router.get("/{job_id}/download-all")
async def download_all(
    job_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    WAV + JSON 파일 함께 다운로드 (ZIP)
    """
    settings = get_settings()
    
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")
    
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="아직 완료되지 않은 작업입니다.")
    
    base_name = os.path.splitext(job.original_filename)[0]
    
    # ZIP 파일 생성
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # WAV 파일 추가
        if job.output_filename:
            wav_path = os.path.join(settings.output_dir, job.output_filename)
            if os.path.exists(wav_path):
                zip_file.write(wav_path, f"{base_name}.wav")
        
        # JSON 파일 추가
        if job.json_filename:
            json_path = os.path.join(settings.output_dir, job.json_filename)
            if os.path.exists(json_path):
                zip_file.write(json_path, f"{base_name}.json")
    
    zip_buffer.seek(0)
    zip_content = zip_buffer.getvalue()
    
    # [advice from AI] 한글 파일명 인코딩 (RFC 5987)
    encoded_filename = quote(f"{base_name}.zip")
    
    return Response(
        content=zip_content,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
            "Content-Length": str(len(zip_content)),
        },
    )


@router.post("/download-batch")
async def download_batch(
    job_ids: List[str],
    db: AsyncSession = Depends(get_db),
):
    """
    여러 파일 일괄 다운로드 (ZIP)
    """
    settings = get_settings()
    
    # 완료된 작업만 필터링
    result = await db.execute(
        select(Job).where(
            Job.id.in_(job_ids),
            Job.status == JobStatus.COMPLETED,
            Job.output_filename.isnot(None),
        )
    )
    jobs = result.scalars().all()
    
    if not jobs:
        raise HTTPException(
            status_code=404,
            detail="다운로드 가능한 파일이 없습니다."
        )
    
    # [advice from AI] ZIP 파일 생성 - WAV와 JSON 모두 포함
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for job in jobs:
            base_name = os.path.splitext(job.original_filename)[0]
            
            # WAV 파일 추가
            if job.output_filename:
                wav_path = os.path.join(settings.output_dir, job.output_filename)
                if os.path.exists(wav_path):
                    zip_file.write(wav_path, f"{base_name}.wav")
            
            # JSON 파일 추가
            if job.json_filename:
                json_path = os.path.join(settings.output_dir, job.json_filename)
                if os.path.exists(json_path):
                    zip_file.write(json_path, f"{base_name}.json")
    
    zip_buffer.seek(0)
    zip_content = zip_buffer.getvalue()
    
    return Response(
        content=zip_content,
        media_type="application/zip",
        headers={
            "Content-Disposition": "attachment; filename=script2wave_batch.zip",
            "Content-Length": str(len(zip_content)),
        },
    )


@router.delete("/{job_id}")
async def delete_file(
    job_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    작업 및 관련 파일 삭제
    """
    settings = get_settings()
    
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")
    
    # 업로드 파일 삭제
    upload_path = os.path.join(settings.upload_dir, job.filename)
    if os.path.exists(upload_path):
        os.remove(upload_path)
    
    # 출력 WAV 파일 삭제
    if job.output_filename:
        output_path = os.path.join(settings.output_dir, job.output_filename)
        if os.path.exists(output_path):
            os.remove(output_path)
    
    # [advice from AI] 출력 JSON 파일 삭제
    if job.json_filename:
        json_path = os.path.join(settings.output_dir, job.json_filename)
        if os.path.exists(json_path):
            os.remove(json_path)
    
    # DB에서 삭제
    await db.delete(job)
    await db.commit()
    
    return {"message": "작업이 삭제되었습니다.", "job_id": job_id}


@router.get("/{job_id}/original")
async def get_original_content(
    job_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    원본 대화록 내용 조회
    """
    settings = get_settings()
    
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")
    
    file_path = os.path.join(settings.upload_dir, job.filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="원본 파일을 찾을 수 없습니다.")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    return {
        "job_id": job_id,
        "filename": job.original_filename,
        "content": content,
    }


# [advice from AI] JSON 발화 정보 미리보기 API 추가 (파일 크기 포함)
@router.get("/{job_id}/json-preview")
async def get_json_preview(
    job_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    발화 정보 JSON 내용 조회 (미리보기) + 파일 크기 정보
    """
    import json
    settings = get_settings()
    
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")
    
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="아직 완료되지 않은 작업입니다.")
    
    if not job.json_filename:
        raise HTTPException(status_code=404, detail="JSON 파일이 없습니다.")
    
    json_path = os.path.join(settings.output_dir, job.json_filename)
    
    if not os.path.exists(json_path):
        raise HTTPException(status_code=404, detail="JSON 파일을 찾을 수 없습니다.")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
    
    # 파일 크기 정보 추가
    wav_size = 0
    json_size = os.path.getsize(json_path)
    
    if job.output_filename:
        wav_path = os.path.join(settings.output_dir, job.output_filename)
        if os.path.exists(wav_path):
            wav_size = os.path.getsize(wav_path)
    
    json_data['file_sizes'] = {
        'wav': wav_size,
        'json': json_size,
        'total': wav_size + json_size
    }
    
    return json_data

