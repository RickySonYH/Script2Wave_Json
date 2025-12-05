# Windows 빌드 가이드

Script2WAVE를 Windows Portable ZIP으로 빌드하는 방법입니다.

## 🚀 자동 빌드 (GitHub Actions)

**가장 쉬운 방법!** 태그만 푸시하면 자동으로 빌드됩니다.

### 릴리스 생성 방법

```bash
# 태그 생성 및 푸시
git tag v1.0.0
git push origin v1.0.0
```

GitHub Actions가 자동으로:
1. Windows 환경에서 빌드
2. Embedded Python 포함
3. ffmpeg 포함
4. Releases 페이지에 ZIP 업로드

### 수동 실행

1. GitHub 저장소 → Actions 탭
2. "Build Portable ZIP" 워크플로우 선택
3. "Run workflow" 클릭

---

## 🔧 수동 빌드

직접 Windows에서 빌드하려면:

### 1. 사전 준비

| 항목 | 다운로드 |
|------|----------|
| Python 3.11 Embedded | https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip |
| ffmpeg | https://github.com/BtbN/FFmpeg-Builds/releases |

### 2. 디렉토리 구조 만들기

```
Script2WAVE/
├── python/              ← Python Embedded 압축 해제
│   ├── python.exe
│   ├── python311.dll
│   └── ...
├── ffmpeg/
│   ├── ffmpeg.exe       ← ffmpeg bin 폴더에서 복사
│   └── ffprobe.exe
├── backend/
├── frontend/
├── storage/
│   ├── uploads/
│   └── outputs/
├── run.bat
└── ...
```

### 3. Python 설정

```cmd
:: python311._pth 파일 수정 (import site 주석 해제)
:: #import site → import site

:: pip 설치
python\python.exe get-pip.py

:: 의존성 설치
python\python.exe -m pip install -r requirements.txt
```

### 4. ZIP 압축

```cmd
:: 필요한 폴더/파일만 ZIP으로 압축
:: backend, frontend, python, ffmpeg, storage, run.bat, README.md, LICENSE
```

---

## 📦 결과물

```
Script2WAVE-Portable-v1.0.0.zip (약 80~100MB)
```

### 사용 방법

1. ZIP 압축 해제
2. `run.bat` 더블클릭
3. 브라우저가 자동으로 열림 (`http://localhost:8000`)

---

## ❓ 문제 해결

### "python을 찾을 수 없습니다"
- `python` 폴더가 ZIP에 포함되어 있는지 확인
- `run.bat`과 같은 위치에 있어야 함

### "ffmpeg를 찾을 수 없습니다"
- `ffmpeg` 폴더에 `ffmpeg.exe`, `ffprobe.exe` 있는지 확인

### "모듈을 찾을 수 없습니다"
- pip로 의존성 재설치: `python\python.exe -m pip install -r requirements.txt`

### 포트 충돌
- 다른 프로그램이 8000번 포트 사용 중
- `run.bat`에서 포트 번호 변경 (8000 → 8080 등)
