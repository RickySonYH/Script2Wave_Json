# [advice from AI] FastAPI 메인 애플리케이션 진입점
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import os

from backend.config import get_settings, set_runtime_api_key, get_runtime_api_key, clear_runtime_api_key
from backend.database import init_db
from backend.api.routes import upload, jobs, files
from pydantic import BaseModel


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    # 시작 시 초기화
    settings = get_settings()
    
    # 디렉토리 생성
    os.makedirs(settings.upload_dir, exist_ok=True)
    os.makedirs(settings.output_dir, exist_ok=True)
    os.makedirs(settings.temp_dir, exist_ok=True)
    
    # 데이터베이스 초기화
    await init_db()
    
    print("🚀 Script2WAVE 서버가 시작되었습니다!")
    print(f"📁 업로드 경로: {settings.upload_dir}")
    print(f"📁 출력 경로: {settings.output_dir}")
    
    yield
    
    # 종료 시 정리
    print("👋 Script2WAVE 서버가 종료됩니다.")


app = FastAPI(
    title="Script2WAVE",
    description="대화록을 자연스러운 녹취 WAVE 파일로 변환하는 서비스",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우터 등록
app.include_router(upload.router, prefix="/api/upload", tags=["Upload"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["Jobs"])
app.include_router(files.router, prefix="/api/files", tags=["Files"])

# 정적 파일 서빙 (프론트엔드)
app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/")
async def root():
    """프론트엔드 메인 페이지"""
    return FileResponse("frontend/index.html")


# [advice from AI] Favicon 라우트 추가
@app.get("/favicon.ico")
async def favicon():
    """파비콘"""
    return FileResponse("frontend/favicon.svg", media_type="image/svg+xml")


@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {"status": "healthy", "service": "Script2WAVE"}


@app.get("/api/config")
async def get_config():
    """클라이언트용 설정 조회"""
    settings = get_settings()
    runtime_key = get_runtime_api_key()
    env_key = settings.elevenlabs_api_key
    
    # API 키 상태 (마스킹)
    has_key = bool(runtime_key or env_key)
    key_source = "runtime" if runtime_key else ("env" if env_key else None)
    
    return {
        "speech_rate": settings.speech_rate,
        "turn_gap_min": settings.turn_gap_min,
        "turn_gap_max": settings.turn_gap_max,
        "action_duration": settings.action_duration,
        "silence_padding": settings.silence_padding,
        "max_concurrent_jobs": settings.max_concurrent_jobs,
        "has_api_key": has_key,
        "api_key_source": key_source,
        "tts_mock_mode": settings.tts_mock_mode,
    }


class ApiKeyRequest(BaseModel):
    api_key: str


@app.post("/api/settings/api-key")
async def set_api_key(request: ApiKeyRequest):
    """런타임 API 키 설정 (세션 기반)"""
    if not request.api_key or len(request.api_key) < 10:
        return {"success": False, "message": "유효하지 않은 API 키입니다."}
    
    set_runtime_api_key(request.api_key)
    
    # 마스킹된 키 표시
    masked_key = request.api_key[:8] + "..." + request.api_key[-4:]
    return {
        "success": True,
        "message": "API 키가 설정되었습니다.",
        "masked_key": masked_key
    }


@app.delete("/api/settings/api-key")
async def delete_api_key():
    """런타임 API 키 삭제"""
    clear_runtime_api_key()
    return {"success": True, "message": "API 키가 삭제되었습니다."}

