#!/usr/bin/env python3
"""
Script2WAVE Windows 실행 스크립트
[advice from AI] Windows 환경에서 서버 시작 및 브라우저 자동 열기
"""

import os
import sys
import time
import socket
import webbrowser
import threading
import signal
from pathlib import Path

# [advice from AI] PyInstaller 번들 환경에서 경로 처리
if getattr(sys, 'frozen', False):
    # PyInstaller로 빌드된 경우
    BASE_DIR = Path(sys._MEIPASS)
    APP_DIR = Path(os.path.dirname(sys.executable))
else:
    # 개발 환경
    BASE_DIR = Path(__file__).parent
    APP_DIR = BASE_DIR

# 환경 변수 설정
os.environ['STORAGE_BASE_PATH'] = str(APP_DIR / 'storage')
os.environ['DATABASE_URL'] = f"sqlite:///{APP_DIR / 'storage' / 'script2wave.db'}"

# [advice from AI] storage 디렉토리 생성
storage_path = APP_DIR / 'storage'
(storage_path / 'uploads').mkdir(parents=True, exist_ok=True)
(storage_path / 'outputs').mkdir(parents=True, exist_ok=True)


def is_port_in_use(port: int) -> bool:
    """포트 사용 여부 확인"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


def find_available_port(start_port: int = 8000, max_tries: int = 10) -> int:
    """사용 가능한 포트 찾기"""
    for i in range(max_tries):
        port = start_port + i
        if not is_port_in_use(port):
            return port
    return start_port


def open_browser(port: int, delay: float = 2.0):
    """브라우저 열기 (지연 후)"""
    time.sleep(delay)
    url = f"http://localhost:{port}"
    print(f"\n🌐 브라우저에서 열기: {url}")
    webbrowser.open(url)


def run_server(port: int):
    """FastAPI 서버 실행"""
    import uvicorn
    
    # backend 경로를 sys.path에 추가
    backend_path = BASE_DIR / 'backend'
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))
    
    # frontend 경로 설정
    os.environ['FRONTEND_PATH'] = str(BASE_DIR / 'frontend')
    
    from backend.main import app
    
    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=port,
        log_level="info",
        access_log=True,
    )
    server = uvicorn.Server(config)
    server.run()


def main():
    """메인 함수"""
    print("=" * 50)
    print("  Script2WAVE - 대화록 → 음성 변환기")
    print("=" * 50)
    print()
    
    # 포트 확인
    port = find_available_port(8000)
    if port != 8000:
        print(f"⚠️  포트 8000이 사용 중입니다. 포트 {port}을 사용합니다.")
    
    print(f"📁 저장 경로: {APP_DIR / 'storage'}")
    print(f"🚀 서버 시작 중... (포트: {port})")
    print()
    print("종료하려면 이 창을 닫거나 Ctrl+C를 누르세요.")
    print("-" * 50)
    
    # 브라우저 열기 (별도 스레드)
    browser_thread = threading.Thread(
        target=open_browser,
        args=(port,),
        daemon=True
    )
    browser_thread.start()
    
    # 서버 실행
    try:
        run_server(port)
    except KeyboardInterrupt:
        print("\n\n👋 서버를 종료합니다...")
        sys.exit(0)


if __name__ == "__main__":
    main()

