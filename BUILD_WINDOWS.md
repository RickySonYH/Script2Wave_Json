# Windows 빌드 가이드

Script2WAVE를 Windows 설치 프로그램(.exe)으로 빌드하는 방법입니다.

## 사전 준비

### 1. 필수 소프트웨어

| 소프트웨어 | 버전 | 다운로드 |
|-----------|------|----------|
| Python | 3.10+ | https://www.python.org/downloads/ |
| Inno Setup | 6.x | https://jrsoftware.org/isinfo.php |
| ffmpeg | latest | https://github.com/BtbN/FFmpeg-Builds/releases |

### 2. ffmpeg 준비

1. [FFmpeg Builds](https://github.com/BtbN/FFmpeg-Builds/releases)에서 다운로드
   - `ffmpeg-master-latest-win64-gpl.zip` 선택
2. 압축 해제 후 `bin` 폴더에서 다음 파일 복사:
   - `ffmpeg.exe`
   - `ffprobe.exe`
3. `build/ffmpeg/` 폴더에 붙여넣기

```
build/
├── ffmpeg/
│   ├── ffmpeg.exe    ← 여기에
│   └── ffprobe.exe   ← 여기에
├── script2wave.spec
├── setup.iss
└── icon.svg
```

### 3. 아이콘 변환 (선택)

`build/icon.svg`를 `build/icon.ico`로 변환:
- 온라인 변환: https://convertio.co/svg-ico/
- 256x256 크기 권장

---

## 빌드 방법

### 방법 1: 자동 빌드 (권장)

```cmd
build\build_windows.bat
```

더블클릭하면 자동으로:
1. 가상환경 생성
2. 의존성 설치
3. PyInstaller 빌드
4. Inno Setup 빌드 (설치된 경우)

### 방법 2: 수동 빌드

```cmd
:: 1. 가상환경 생성 및 활성화
python -m venv venv
venv\Scripts\activate

:: 2. 의존성 설치
pip install -r requirements.txt
pip install pyinstaller

:: 3. PyInstaller 빌드
pyinstaller --clean build\script2wave.spec

:: 4. Inno Setup 빌드 (Inno Setup Compiler 필요)
iscc build\setup.iss
```

---

## 빌드 결과물

### PyInstaller 빌드 후
```
dist/
└── Script2WAVE/
    ├── Script2WAVE.exe    ← 실행 파일
    ├── backend/
    ├── frontend/
    ├── ffmpeg.exe
    └── (기타 의존성)
```

### Inno Setup 빌드 후
```
dist/
├── Script2WAVE/           ← Portable 버전
└── Script2WAVE-Setup-1.0.0.exe  ← 설치 프로그램
```

---

## 설치 프로그램 사용

### 설치
1. `Script2WAVE-Setup-1.0.0.exe` 실행
2. 설치 경로 선택 (기본: `C:\Users\{사용자}\AppData\Local\Programs\Script2WAVE`)
3. 바탕화면 바로가기 생성 (선택)
4. 설치 완료

### 실행
1. 시작 메뉴 → Script2WAVE
2. 또는 바탕화면 바로가기 더블클릭
3. 콘솔 창이 열리고 브라우저가 자동으로 `http://localhost:8000` 접속

### 제거
1. 설정 → 앱 → Script2WAVE → 제거
2. 또는 시작 메뉴 → Script2WAVE → Uninstall

---

## Portable 버전 배포

Inno Setup 없이 배포하려면:

1. `dist/Script2WAVE` 폴더를 ZIP으로 압축
2. 사용자에게 배포
3. 사용자가 압축 해제 후 `Script2WAVE.exe` 실행

---

## 문제 해결

### "Python이 설치되어 있지 않습니다"
- Python 3.10 이상 설치
- 설치 시 "Add Python to PATH" 체크

### "ffmpeg.exe가 없습니다"
- 위의 "ffmpeg 준비" 섹션 참고
- `build/ffmpeg/` 폴더에 ffmpeg.exe, ffprobe.exe 복사

### "Inno Setup이 설치되어 있지 않습니다"
- Inno Setup 6 설치 후 재시도
- 또는 `dist/Script2WAVE` 폴더를 ZIP으로 배포

### 빌드 시 "ModuleNotFoundError"
```cmd
pip install <모듈명>
```
이후 `build/script2wave.spec`의 `hiddenimports`에 추가

### 실행 시 "포트 8000이 사용 중"
- 다른 프로그램이 8000번 포트 사용 중
- 자동으로 8001, 8002... 포트로 변경됨

---

## 파일 구조 설명

```
build/
├── script2wave.spec   # PyInstaller 빌드 설정
├── setup.iss          # Inno Setup 스크립트
├── build_windows.bat  # 자동 빌드 스크립트
├── icon.svg           # 앱 아이콘 (SVG)
├── icon.ico           # 앱 아이콘 (ICO, 변환 필요)
└── ffmpeg/
    ├── ffmpeg.exe     # 오디오 처리용
    └── ffprobe.exe
```

