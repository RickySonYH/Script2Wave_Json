# [advice from AI] 작업(Job) 모델 정의
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Enum as SQLEnum
from sqlalchemy.sql import func
from enum import Enum
from typing import Optional
from pydantic import BaseModel
from datetime import datetime

from backend.database import Base


class JobStatus(str, Enum):
    """작업 상태"""
    PENDING = "pending"           # 대기 중
    PARSING = "parsing"           # 파싱 중
    GENERATING_TTS = "generating_tts"  # TTS 생성 중
    MIXING = "mixing"             # 오디오 합성 중
    COMPLETED = "completed"       # 완료
    FAILED = "failed"             # 실패
    CANCELLED = "cancelled"       # 취소됨


class Job(Base):
    """작업 테이블"""
    __tablename__ = "jobs"
    
    id = Column(String(36), primary_key=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    status = Column(SQLEnum(JobStatus), default=JobStatus.PENDING, nullable=False)
    
    # 진행률 (0-100)
    progress = Column(Integer, default=0)
    
    # 설정값 (JSON 문자열로 저장)
    settings = Column(Text, nullable=True)
    
    # 결과
    output_filename = Column(String(255), nullable=True)
    json_filename = Column(String(255), nullable=True)  # [advice from AI] 발화 정보 JSON 파일
    duration_seconds = Column(Float, nullable=True)
    
    # 에러 정보
    error_message = Column(Text, nullable=True)
    
    # 타임스탬프
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime, nullable=True)


# Pydantic 스키마
class JobCreate(BaseModel):
    """작업 생성 요청"""
    filename: str
    settings: Optional[dict] = None


class JobResponse(BaseModel):
    """작업 응답"""
    id: str
    filename: str
    original_filename: str
    status: JobStatus
    progress: int
    output_filename: Optional[str] = None
    json_filename: Optional[str] = None  # [advice from AI] 발화 정보 JSON 파일
    duration_seconds: Optional[float] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    """작업 목록 응답"""
    jobs: list[JobResponse]
    total: int
    page: int
    page_size: int

