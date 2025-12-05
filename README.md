# Script2WAVE

대화록(텍스트)을 입력하면 **자연스러운 녹취 WAVE 파일**과 **발화 정보 JSON 파일**을 생성하는 웹 애플리케이션입니다.

## 주요 기능

- **대화록 파싱**: 상담사/고객 대화 형식의 텍스트 파일 처리
- **TTS 변환**: ElevenLabs API를 사용한 고품질 음성 합성
- **타임스탬프 생성**: 자연스러운 대화 속도 기반 타임스탬프 자동 생성
- **결과 파일**: WAV 오디오 파일 + JSON 발화 정보 파일
- **웹 인터페이스**: 파일 업로드, 작업 관리, 미리보기, 다운로드
- **통합 미리보기**: 오디오 재생과 발화 목록 동기화 (클릭 시 해당 시점으로 이동)
- **일괄 처리**: 다중 파일 업로드 및 배치 다운로드 지원

## 기술 스택

- **Backend**: FastAPI, SQLAlchemy, SQLite
- **Frontend**: Vanilla JavaScript, CSS
- **TTS**: ElevenLabs API
- **Container**: Docker, Docker Compose

## 설치 및 실행

### 1. 저장소 클론

```bash
git clone https://github.com/RickySonYH/Script2Wave_Json.git
cd Script2Wave_Json
```

### 2. Docker로 실행

```bash
docker-compose up --build -d
```

### 3. 웹 브라우저에서 접속

```
http://localhost:8000
```

## 사용법

### 1. API 키 설정

1. 웹 페이지 우측 상단 **설정** 버튼 클릭
2. ElevenLabs API 키 입력 후 **저장**
3. API 키는 세션 기반으로, 브라우저 종료 시 삭제됨

### 2. 대화록 업로드

1. 업로드 영역 클릭 또는 드래그앤드롭
2. 다중 파일 선택 시 **Ctrl + 클릭**
3. **변환 시작** 버튼 클릭

### 3. 결과 확인

- **미리보기**: 오디오 재생 + 발화 목록 (클릭 시 해당 위치로 이동)
- **다운로드**: WAV, JSON, 또는 ZIP(전체)

## 대화록 형식

```
상담사: 안녕하세요, 무엇을 도와드릴까요?
고객: 네, 주문한 상품에 문제가 있어서요.
상담사: 어떤 문제가 있으신가요?
[고객이 영수증을 찾는다]
고객: 주문번호는 12345입니다.
```

### 지원 형식

- `상담사:`, `고객:` - 화자 구분
- `[ACTION]` - 대기 시간 (기본 2초)
- `(1.5초 대기)` - 명시적 대기 시간

## JSON 출력 형식

```json
{
  "call_id": "job-uuid",
  "audio_file": "job-uuid.wav",
  "utterances": [
    {
      "turn_idx": 1,
      "role": "agent",
      "utterance": "안녕하세요, 무엇을 도와드릴까요?",
      "started_at": 0.0,
      "ended_at": 2.5
    },
    {
      "turn_idx": 2,
      "role": "customer",
      "utterance": "네, 주문한 상품에 문제가 있어서요.",
      "started_at": 3.0,
      "ended_at": 5.8
    }
  ],
  "file_sizes": {
    "wav": 22016824,
    "json": 6011,
    "total": 22022835
  }
}
```

## 환경 변수

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `ELEVENLABS_API_KEY` | ElevenLabs API 키 | - |
| `TTS_MOCK_MODE` | 테스트용 Mock 모드 | false |
| `DEFAULT_SPEECH_RATE` | 초당 글자 수 | 5.5 |
| `DEFAULT_TURN_GAP` | 화자 교체 간격 (초) | 0.5 |

## 프로젝트 구조

```
Script2WAVE/
├── backend/
│   ├── api/routes/      # API 엔드포인트
│   ├── core/            # 파싱, TTS, 믹싱 로직
│   ├── models/          # DB 모델
│   ├── config.py        # 설정 관리
│   └── main.py          # FastAPI 앱
├── frontend/
│   ├── css/style.css    # 스타일
│   ├── js/app.js        # 프론트엔드 로직
│   └── index.html       # 메인 페이지
├── storage/
│   ├── uploads/         # 업로드된 파일
│   └── outputs/         # 생성된 WAV, JSON
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## API 엔드포인트

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/api/upload/` | POST | 대화록 파일 업로드 |
| `/api/jobs/` | GET | 작업 목록 조회 (검색, 필터, 정렬, 페이지네이션) |
| `/api/jobs/{id}` | GET | 작업 상세 조회 |
| `/api/jobs/{id}` | DELETE | 작업 삭제 |
| `/api/files/{id}/download` | GET | WAV 파일 다운로드 |
| `/api/files/{id}/download-json` | GET | JSON 파일 다운로드 |
| `/api/files/{id}/download-all` | GET | WAV + JSON ZIP 다운로드 |
| `/api/files/{id}/stream` | GET | 오디오 스트리밍 |
| `/api/files/{id}/json-preview` | GET | JSON 미리보기 |
| `/api/config` | GET | 설정 조회 |
| `/api/config/elevenlabs-key` | POST | API 키 설정 |

## 라이선스

MIT License

