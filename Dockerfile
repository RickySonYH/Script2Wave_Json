# [advice from AI] Python 3.11 기반 Docker 이미지 + ffmpeg 포함
FROM python:3.11-slim

# 시스템 의존성 설치 (ffmpeg는 pydub에서 필요)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# Python 의존성 먼저 복사 (캐시 활용)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY . .

# 업로드/출력 디렉토리 생성
RUN mkdir -p /app/storage/uploads /app/storage/outputs

# FastAPI 서버 포트
EXPOSE 8000

# 개발 모드로 실행 (핫 리로드)
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

