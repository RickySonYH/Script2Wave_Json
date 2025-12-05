# [advice from AI] 애플리케이션 설정 관리 모듈
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from functools import lru_cache
import os


# 런타임 API 키 저장소 (세션 기반, 서버 재시작 시 초기화)
_runtime_api_key: Optional[str] = None


def set_runtime_api_key(key: str):
    """런타임에 API 키 설정"""
    global _runtime_api_key
    _runtime_api_key = key if key else None


def get_runtime_api_key() -> Optional[str]:
    """런타임 API 키 조회"""
    return _runtime_api_key


def clear_runtime_api_key():
    """런타임 API 키 삭제"""
    global _runtime_api_key
    _runtime_api_key = None


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # API Keys
    elevenlabs_api_key: str = Field(default="", description="ElevenLabs API Key")
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API Key (optional)")
    
    # [advice from AI] Mock 모드 - API 키 없이 테스트용
    tts_mock_mode: bool = Field(default=False, description="TTS Mock 모드 (테스트용)")
    
    # 타임스탬프 생성 설정
    speech_rate: float = Field(default=5.5, description="초당 글자 수 (한국어 기준)")
    turn_gap_min: float = Field(default=0.5, description="화자 교체 최소 간격 (초)")
    turn_gap_max: float = Field(default=1.5, description="화자 교체 최대 간격 (초)")
    action_duration: float = Field(default=2.0, description="[ACTION] 기본 소요 시간 (초)")
    silence_padding: float = Field(default=0.3, description="문장 끝 여백 (초)")
    
    # TTS 음성 설정
    voice_agent: Optional[str] = Field(default=None, description="상담사 Voice ID")
    voice_customer: Optional[str] = Field(default=None, description="고객 Voice ID")
    
    # 파일 관리 설정
    file_retention_days: int = Field(default=30, description="파일 보관 기간 (일)")
    max_concurrent_jobs: int = Field(default=3, description="동시 작업 수 제한")
    
    # 경로 설정
    base_dir: str = Field(default="/app", description="기본 경로")
    upload_dir: str = Field(default="/app/storage/uploads", description="업로드 경로")
    output_dir: str = Field(default="/app/storage/outputs", description="출력 경로")
    temp_dir: str = Field(default="/app/storage/temp", description="임시 경로")
    db_path: str = Field(default="/app/storage/database.db", description="데이터베이스 경로")
    
    # 오디오 설정
    audio_sample_rate: int = Field(default=44100, description="오디오 샘플레이트")
    audio_channels: int = Field(default=1, description="오디오 채널 수 (1=모노)")
    audio_format: str = Field(default="wav", description="출력 오디오 형식")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """설정 싱글톤 반환"""
    return Settings()


# 개발 환경에서 로컬 경로로 오버라이드
def get_local_settings() -> Settings:
    """로컬 개발용 설정 (Docker 외부)"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return Settings(
        base_dir=base_dir,
        upload_dir=os.path.join(base_dir, "storage", "uploads"),
        output_dir=os.path.join(base_dir, "storage", "outputs"),
        temp_dir=os.path.join(base_dir, "storage", "temp"),
        db_path=os.path.join(base_dir, "storage", "database.db"),
    )

