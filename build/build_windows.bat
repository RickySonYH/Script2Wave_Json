@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

echo ============================================
echo   Script2WAVE Windows 빌드 스크립트
echo ============================================
echo.

:: 프로젝트 루트로 이동
cd /d "%~dp0.."
set PROJECT_ROOT=%cd%
echo 프로젝트 경로: %PROJECT_ROOT%
echo.

:: Python 확인
python --version > nul 2>&1
if errorlevel 1 (
    echo [오류] Python이 설치되어 있지 않습니다.
    echo Python 3.10 이상을 설치해주세요.
    pause
    exit /b 1
)

:: 가상환경 생성 (없으면)
if not exist "venv" (
    echo [1/6] 가상환경 생성 중...
    python -m venv venv
)

:: 가상환경 활성화
echo [2/6] 가상환경 활성화...
call venv\Scripts\activate.bat

:: 의존성 설치
echo [3/6] 의존성 설치 중...
pip install -r requirements.txt
pip install pyinstaller

:: ffmpeg 확인
if not exist "build\ffmpeg\ffmpeg.exe" (
    echo.
    echo [경고] ffmpeg.exe가 없습니다!
    echo.
    echo 다음 단계를 수행해주세요:
    echo   1. https://github.com/BtbN/FFmpeg-Builds/releases 방문
    echo   2. ffmpeg-master-latest-win64-gpl.zip 다운로드
    echo   3. 압축 해제 후 bin 폴더의 ffmpeg.exe, ffprobe.exe를
    echo      build\ffmpeg\ 폴더에 복사
    echo.
    pause
    exit /b 1
)

:: 아이콘 변환 안내
if not exist "build\icon.ico" (
    echo.
    echo [경고] icon.ico가 없습니다!
    echo build\icon.svg를 ICO로 변환해주세요.
    echo 온라인 변환: https://convertio.co/svg-ico/
    echo.
)

:: PyInstaller 빌드
echo [4/6] PyInstaller 빌드 중...
pyinstaller --clean build\script2wave.spec

if errorlevel 1 (
    echo [오류] PyInstaller 빌드 실패
    pause
    exit /b 1
)

:: 빌드 결과 확인
if not exist "dist\Script2WAVE\Script2WAVE.exe" (
    echo [오류] 빌드 결과물을 찾을 수 없습니다.
    pause
    exit /b 1
)

echo.
echo [5/6] PyInstaller 빌드 완료!
echo 결과물: dist\Script2WAVE\
echo.

:: Inno Setup 확인
where iscc > nul 2>&1
if errorlevel 1 (
    echo [안내] Inno Setup이 설치되어 있지 않습니다.
    echo 설치 프로그램을 만들려면:
    echo   1. https://jrsoftware.org/isinfo.php 에서 Inno Setup 6 설치
    echo   2. 이 스크립트를 다시 실행하거나
    echo   3. build\setup.iss를 Inno Setup Compiler로 열어서 빌드
    echo.
    echo 현재 상태로 dist\Script2WAVE 폴더를 ZIP으로 배포할 수 있습니다.
    pause
    exit /b 0
)

:: Inno Setup 빌드
echo [6/6] Inno Setup 빌드 중...
iscc build\setup.iss

if errorlevel 1 (
    echo [오류] Inno Setup 빌드 실패
    pause
    exit /b 1
)

echo.
echo ============================================
echo   빌드 완료!
echo ============================================
echo.
echo 설치 프로그램: dist\Script2WAVE-Setup-1.0.0.exe
echo.
pause

