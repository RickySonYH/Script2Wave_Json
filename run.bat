@echo off
chcp 65001 > nul
title Script2WAVE - 대화록 음성 변환기

echo.
echo ============================================
echo   Script2WAVE - 대화록 → 음성 변환기
echo ============================================
echo.

:: [advice from AI] 현재 디렉토리를 스크립트 위치로 설정
cd /d "%~dp0"

:: Python 경로 설정 (Embedded Python)
set PYTHON_DIR=%~dp0python
set PATH=%PYTHON_DIR%;%PYTHON_DIR%\Scripts;%~dp0ffmpeg;%PATH%

:: 환경 변수 설정
set STORAGE_BASE_PATH=%~dp0storage
set DATABASE_URL=sqlite:///%~dp0storage\script2wave.db
set FRONTEND_PATH=%~dp0frontend

:: storage 폴더 생성
if not exist "storage\uploads" mkdir "storage\uploads"
if not exist "storage\outputs" mkdir "storage\outputs"

echo 저장 경로: %~dp0storage
echo.
echo 서버를 시작합니다...
echo 종료하려면 이 창을 닫거나 Ctrl+C를 누르세요.
echo ============================================
echo.

:: 2초 후 브라우저 열기 (백그라운드)
start /b cmd /c "timeout /t 2 /nobreak > nul && start http://localhost:8000"

:: 서버 실행
python\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

pause

