# [advice from AI] 작업 관리 API 라우터 - 실사용 버전 강화
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, asc, or_
from typing import Optional, List
from datetime import datetime, timedelta

from backend.database import get_db
from backend.models.job import Job, JobStatus, JobResponse, JobListResponse

router = APIRouter()


@router.get("/", response_model=JobListResponse)
async def list_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[JobStatus] = None,
    search: Optional[str] = Query(None, description="파일명 검색"),
    date_from: Optional[str] = Query(None, description="시작일 (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="종료일 (YYYY-MM-DD)"),
    sort_by: str = Query("created_at", description="정렬 기준"),
    sort_order: str = Query("desc", description="정렬 순서 (asc/desc)"),
    db: AsyncSession = Depends(get_db),
):
    """
    작업 목록 조회 (검색, 필터, 정렬 지원)
    """
    # 기본 쿼리
    query = select(Job)
    count_query = select(func.count(Job.id))
    
    # 상태 필터
    if status:
        query = query.where(Job.status == status)
        count_query = count_query.where(Job.status == status)
    
    # 파일명 검색
    if search:
        search_filter = or_(
            Job.original_filename.ilike(f"%{search}%"),
            Job.id.ilike(f"%{search}%")
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    
    # 날짜 필터
    if date_from:
        try:
            from_date = datetime.strptime(date_from, "%Y-%m-%d")
            query = query.where(Job.created_at >= from_date)
            count_query = count_query.where(Job.created_at >= from_date)
        except ValueError:
            pass
    
    if date_to:
        try:
            to_date = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
            query = query.where(Job.created_at < to_date)
            count_query = count_query.where(Job.created_at < to_date)
        except ValueError:
            pass
    
    # 총 개수
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # 정렬
    sort_column = getattr(Job, sort_by, Job.created_at)
    if sort_order == "asc":
        query = query.order_by(asc(sort_column))
    else:
        query = query.order_by(desc(sort_column))
    
    # 페이지네이션
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    jobs = result.scalars().all()
    
    return JobListResponse(
        jobs=[JobResponse.model_validate(job) for job in jobs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/stats/summary")
async def get_stats(
    db: AsyncSession = Depends(get_db),
):
    """
    작업 통계 조회 (강화된 버전)
    """
    # 상태별 카운트
    stats = {}
    for status in JobStatus:
        result = await db.execute(
            select(func.count(Job.id)).where(Job.status == status)
        )
        stats[status.value] = result.scalar() or 0
    
    # 총 작업 수
    total_result = await db.execute(select(func.count(Job.id)))
    total = total_result.scalar() or 0
    
    # 완료된 작업의 평균 처리 시간 (초)
    avg_duration_result = await db.execute(
        select(func.avg(Job.duration_seconds)).where(Job.status == JobStatus.COMPLETED)
    )
    avg_duration = avg_duration_result.scalar() or 0
    
    # 오늘 처리된 작업 수
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_result = await db.execute(
        select(func.count(Job.id)).where(
            Job.completed_at >= today,
            Job.status == JobStatus.COMPLETED
        )
    )
    today_completed = today_result.scalar() or 0
    
    # 처리 중인 작업 수
    processing_statuses = [JobStatus.PARSING, JobStatus.GENERATING_TTS, JobStatus.MIXING]
    processing_result = await db.execute(
        select(func.count(Job.id)).where(Job.status.in_(processing_statuses))
    )
    processing = processing_result.scalar() or 0
    
    return {
        "total": total,
        "by_status": stats,
        "completion_rate": round(stats.get("completed", 0) / total * 100, 1) if total > 0 else 0,
        "avg_duration_seconds": round(avg_duration, 1) if avg_duration else 0,
        "today_completed": today_completed,
        "processing": processing,
    }


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    특정 작업 상세 조회
    """
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")
    
    return JobResponse.model_validate(job)


@router.delete("/{job_id}")
async def delete_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    작업 삭제 (파일 포함)
    """
    from backend.config import get_settings
    import os
    
    settings = get_settings()
    
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")
    
    # 업로드 파일 삭제
    if job.filename:
        upload_path = os.path.join(settings.upload_dir, job.filename)
        if os.path.exists(upload_path):
            os.remove(upload_path)
    
    # 출력 WAV 파일 삭제
    if job.output_filename:
        output_path = os.path.join(settings.output_dir, job.output_filename)
        if os.path.exists(output_path):
            os.remove(output_path)
    
    # JSON 파일 삭제
    if job.json_filename:
        json_path = os.path.join(settings.output_dir, job.json_filename)
        if os.path.exists(json_path):
            os.remove(json_path)
    
    # DB에서 삭제
    await db.delete(job)
    await db.commit()
    
    return {"message": "작업이 삭제되었습니다.", "job_id": job_id}


@router.post("/{job_id}/retry", response_model=JobResponse)
async def retry_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    실패한 작업 재시도
    """
    from backend.core.processor import process_script
    
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")
    
    # 실패한 작업만 재시도 가능
    if job.status != JobStatus.FAILED:
        raise HTTPException(
            status_code=400,
            detail="실패한 작업만 재시도할 수 있습니다."
        )
    
    # 상태 초기화
    job.status = JobStatus.PENDING
    job.progress = 0
    job.error_message = None
    job.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(job)
    
    # 백그라운드에서 재처리
    import asyncio
    asyncio.create_task(process_script(job_id))
    
    return JobResponse.model_validate(job)


# [advice from AI] 일괄 삭제 API
@router.post("/batch/delete")
async def batch_delete(
    job_ids: List[str],
    db: AsyncSession = Depends(get_db),
):
    """
    여러 작업 일괄 삭제
    """
    from backend.config import get_settings
    import os
    
    settings = get_settings()
    deleted_count = 0
    errors = []
    
    for job_id in job_ids:
        try:
            result = await db.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one_or_none()
            
            if not job:
                continue
            
            # 파일 삭제
            if job.filename:
                upload_path = os.path.join(settings.upload_dir, job.filename)
                if os.path.exists(upload_path):
                    os.remove(upload_path)
            
            if job.output_filename:
                output_path = os.path.join(settings.output_dir, job.output_filename)
                if os.path.exists(output_path):
                    os.remove(output_path)
            
            if job.json_filename:
                json_path = os.path.join(settings.output_dir, job.json_filename)
                if os.path.exists(json_path):
                    os.remove(json_path)
            
            await db.delete(job)
            deleted_count += 1
            
        except Exception as e:
            errors.append({"job_id": job_id, "error": str(e)})
    
    await db.commit()
    
    return {
        "message": f"{deleted_count}개 작업이 삭제되었습니다.",
        "deleted_count": deleted_count,
        "errors": errors if errors else None,
    }


# [advice from AI] 일괄 재시도 API
@router.post("/batch/retry")
async def batch_retry(
    job_ids: List[str],
    db: AsyncSession = Depends(get_db),
):
    """
    여러 실패한 작업 일괄 재시도
    """
    from backend.core.processor import process_script
    import asyncio
    
    retried_count = 0
    errors = []
    
    for job_id in job_ids:
        try:
            result = await db.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one_or_none()
            
            if not job or job.status != JobStatus.FAILED:
                continue
            
            job.status = JobStatus.PENDING
            job.progress = 0
            job.error_message = None
            job.updated_at = datetime.utcnow()
            
            asyncio.create_task(process_script(job_id))
            retried_count += 1
            
        except Exception as e:
            errors.append({"job_id": job_id, "error": str(e)})
    
    await db.commit()
    
    return {
        "message": f"{retried_count}개 작업을 재시도합니다.",
        "retried_count": retried_count,
        "errors": errors if errors else None,
    }
