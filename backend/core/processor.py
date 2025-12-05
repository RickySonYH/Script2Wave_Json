# [advice from AI] 전체 처리 프로세스 관리 모듈
import os
import json
import asyncio
from datetime import datetime
from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.database import get_session_maker
from backend.models.job import Job, JobStatus
from backend.core.parser import parse_script, validate_script
from backend.core.timestamp import generate_timestamps, get_total_duration, TimestampedDialogue
from backend.core.tts_client import TTSClient
from backend.core.audio_mixer import AudioMixer


async def update_job_status(
    job_id: str,
    status: JobStatus,
    progress: int = 0,
    error_message: Optional[str] = None,
    output_filename: Optional[str] = None,
    duration_seconds: Optional[float] = None,
    json_filename: Optional[str] = None,
):
    """작업 상태 업데이트"""
    async_session = get_session_maker()
    async with async_session() as session:
        result = await session.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        
        if job:
            job.status = status
            job.progress = progress
            job.updated_at = datetime.utcnow()
            
            if error_message:
                job.error_message = error_message
            if output_filename:
                job.output_filename = output_filename
            if duration_seconds:
                job.duration_seconds = duration_seconds
            if json_filename:
                job.json_filename = json_filename
            if status == JobStatus.COMPLETED:
                job.completed_at = datetime.utcnow()
            
            await session.commit()


# [advice from AI] 발화 정보 JSON 파일 생성 함수 추가
def generate_utterances_json(
    call_id: str,
    audio_filename: str,
    timestamped_dialogues: List[TimestampedDialogue],
    output_path: str,
) -> str:
    """
    발화 정보가 담긴 JSON 파일 생성
    
    Args:
        call_id: 통화 식별자
        audio_filename: WAV 파일명
        timestamped_dialogues: 타임스탬프가 적용된 대화 목록
        output_path: JSON 출력 경로
        
    Returns:
        저장된 JSON 파일 경로
    """
    utterances = []
    
    for idx, ts_dialogue in enumerate(timestamped_dialogues, start=1):
        # role 변환: 상담사 -> agent, 고객 -> customer
        role = "agent" if ts_dialogue.dialogue.speaker == "상담사" else "customer"
        
        utterance = {
            "turn_idx": idx,
            "role": role,
            "utterance": ts_dialogue.dialogue.text,
            "started_at": round(ts_dialogue.start_time, 3),
            "ended_at": round(ts_dialogue.end_time, 3),
        }
        utterances.append(utterance)
    
    json_data = {
        "call_id": call_id,
        "audio_file": audio_filename,
        "utterances": utterances,
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    
    return output_path


async def process_script(job_id: str):
    """
    대화록 처리 메인 프로세스
    
    1. 파일 읽기 및 파싱
    2. 타임스탬프 생성
    3. TTS 음성 생성
    4. 오디오 합성
    5. 결과 저장
    """
    settings = get_settings()
    
    try:
        # 작업 정보 조회
        async_session = get_session_maker()
        async with async_session() as session:
            result = await session.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one_or_none()
            
            if not job:
                return
            
            filename = job.filename
        
        # === 1단계: 파싱 ===
        await update_job_status(job_id, JobStatus.PARSING, progress=10)
        
        file_path = os.path.join(settings.upload_dir, filename)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 유효성 검증
        is_valid, errors = validate_script(content)
        if not is_valid:
            await update_job_status(
                job_id,
                JobStatus.FAILED,
                error_message=f"파싱 실패: {', '.join(errors)}"
            )
            return
        
        # 파싱
        parsed = parse_script(content)
        
        await update_job_status(job_id, JobStatus.PARSING, progress=20)
        
        # === 2단계: 타임스탬프 생성 ===
        timestamped = generate_timestamps(parsed)
        total_duration = get_total_duration(timestamped)
        
        await update_job_status(job_id, JobStatus.GENERATING_TTS, progress=30)
        
        # === 3단계: TTS 생성 ===
        tts_client = TTSClient()
        
        # 화자 목록 추출 및 음성 할당
        speakers = list(set(d.speaker for d in parsed.dialogues))
        await tts_client.assign_voices(
            speakers,
            voice_agent=settings.voice_agent,
            voice_customer=settings.voice_customer,
        )
        
        # 각 대화에 대해 TTS 생성
        audio_files = []
        total_dialogues = len(timestamped)
        
        for idx, ts_dialogue in enumerate(timestamped):
            # 진행률 계산 (30% ~ 80%)
            progress = 30 + int((idx / total_dialogues) * 50)
            await update_job_status(job_id, JobStatus.GENERATING_TTS, progress=progress)
            
            # 임시 오디오 파일 경로
            temp_audio_path = os.path.join(
                settings.temp_dir,
                f"{job_id}_{idx}.mp3"
            )
            
            # TTS 생성
            await tts_client.generate_speech_mp3(
                text=ts_dialogue.dialogue.text,
                speaker=ts_dialogue.dialogue.speaker,
                output_path=temp_audio_path,
            )
            
            audio_files.append(temp_audio_path)
            
            # API 레이트 리밋 방지를 위한 짧은 대기
            await asyncio.sleep(0.1)
        
        # === 4단계: 오디오 합성 ===
        await update_job_status(job_id, JobStatus.MIXING, progress=85)
        
        mixer = AudioMixer()
        
        output_filename = f"{job_id}.wav"
        output_path = os.path.join(settings.output_dir, output_filename)
        
        mixer.mix_dialogues(
            timestamped_dialogues=timestamped,
            audio_files=audio_files,
            output_path=output_path,
        )
        
        # 실제 생성된 오디오 길이 확인
        actual_duration = mixer.get_audio_duration(output_path)
        
        # === 5단계: JSON 파일 생성 ===
        await update_job_status(job_id, JobStatus.MIXING, progress=90)
        
        # [advice from AI] 발화 정보 JSON 파일 생성
        json_filename = f"{job_id}.json"
        json_path = os.path.join(settings.output_dir, json_filename)
        
        generate_utterances_json(
            call_id=job_id,
            audio_filename=output_filename,
            timestamped_dialogues=timestamped,
            output_path=json_path,
        )
        
        # === 6단계: 정리 및 완료 ===
        await update_job_status(job_id, JobStatus.MIXING, progress=95)
        
        # 임시 파일 삭제
        for temp_file in audio_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception:
                pass
        
        # 완료
        await update_job_status(
            job_id,
            JobStatus.COMPLETED,
            progress=100,
            output_filename=output_filename,
            duration_seconds=actual_duration,
            json_filename=json_filename,
        )
        
        print(f"✅ 작업 완료: {job_id} ({actual_duration:.1f}초, JSON 포함)")
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ 작업 실패: {job_id} - {error_msg}")
        
        await update_job_status(
            job_id,
            JobStatus.FAILED,
            error_message=error_msg,
        )

