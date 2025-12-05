# -*- mode: python ; coding: utf-8 -*-
"""
Script2WAVE PyInstaller 빌드 스펙
[advice from AI] Windows EXE 빌드를 위한 PyInstaller 설정

사용법:
    pyinstaller build/script2wave.spec
"""

import os
from pathlib import Path

# 프로젝트 루트 경로
PROJECT_ROOT = Path(SPECPATH).parent

block_cipher = None

# [advice from AI] 수집할 데이터 파일들
datas = [
    # 프론트엔드 정적 파일
    (str(PROJECT_ROOT / 'frontend'), 'frontend'),
    # 백엔드 소스 (동적 임포트용)
    (str(PROJECT_ROOT / 'backend'), 'backend'),
]

# [advice from AI] 숨겨진 임포트 (동적으로 로드되는 모듈)
hiddenimports = [
    'uvicorn',
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'fastapi',
    'starlette',
    'pydantic',
    'sqlalchemy',
    'sqlalchemy.dialects.sqlite',
    'aiosqlite',
    'httpx',
    'pydub',
    'elevenlabs',
    'elevenlabs.client',
    'aiofiles',
    'python_multipart',
    'email_validator',
]

# [advice from AI] 바이너리 파일 (ffmpeg)
binaries = []
ffmpeg_path = PROJECT_ROOT / 'build' / 'ffmpeg' / 'ffmpeg.exe'
if ffmpeg_path.exists():
    binaries.append((str(ffmpeg_path), '.'))

ffprobe_path = PROJECT_ROOT / 'build' / 'ffmpeg' / 'ffprobe.exe'
if ffprobe_path.exists():
    binaries.append((str(ffprobe_path), '.'))

a = Analysis(
    [str(PROJECT_ROOT / 'run_windows.py')],
    pathex=[str(PROJECT_ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy.tests',
        'scipy',
        'pandas',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Script2WAVE',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # [advice from AI] 콘솔 창 표시 (로그 확인용)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(PROJECT_ROOT / 'build' / 'icon.ico') if (PROJECT_ROOT / 'build' / 'icon.ico').exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Script2WAVE',
)

