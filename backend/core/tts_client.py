# [advice from AI] ElevenLabs TTS 클라이언트 모듈
import os
import random
import asyncio
from typing import Optional, List, Dict
from dataclasses import dataclass
from pydub import AudioSegment
from pydub.generators import Sine

from backend.config import get_settings, get_runtime_api_key


@dataclass
class VoiceInfo:
    """음성 정보"""
    voice_id: str
    name: str
    labels: Dict[str, str]


def get_effective_api_key() -> Optional[str]:
    """유효한 API 키 반환 (런타임 키 우선)"""
    runtime_key = get_runtime_api_key()
    if runtime_key:
        return runtime_key
    settings = get_settings()
    return settings.elevenlabs_api_key if settings.elevenlabs_api_key else None


class TTSClient:
    """ElevenLabs TTS 클라이언트"""
    
    # [advice from AI] Mock 모드용 더미 음성 목록
    MOCK_VOICES = [
        VoiceInfo(voice_id="mock_agent_1", name="Mock Agent 1", labels={"gender": "male"}),
        VoiceInfo(voice_id="mock_agent_2", name="Mock Agent 2", labels={"gender": "female"}),
        VoiceInfo(voice_id="mock_customer_1", name="Mock Customer 1", labels={"gender": "male"}),
        VoiceInfo(voice_id="mock_customer_2", name="Mock Customer 2", labels={"gender": "female"}),
    ]
    
    def __init__(self):
        self.settings = get_settings()
        self._voices_cache: Optional[List[VoiceInfo]] = None
        self._voice_assignments: Dict[str, str] = {}  # speaker -> voice_id
        self._init_client()
    
    def _init_client(self):
        """클라이언트 초기화 (API 키 확인)"""
        api_key = get_effective_api_key()
        self.mock_mode = self.settings.tts_mock_mode or not api_key
        
        if not self.mock_mode and api_key:
            # [advice from AI] elevenlabs 1.x 버전 호환 import
            from elevenlabs.client import ElevenLabs
            self.client = ElevenLabs(api_key=api_key)
        else:
            self.client = None
            if self.mock_mode:
                print("⚠️ TTS Mock 모드로 실행됩니다 (테스트용 더미 오디오 생성)")
    
    def refresh_client(self):
        """API 키 변경 시 클라이언트 갱신"""
        self._init_client()
        self._voices_cache = None
        self._voice_assignments = {}
    
    async def get_available_voices(self) -> List[VoiceInfo]:
        """
        사용 가능한 음성 목록 조회
        """
        # [advice from AI] Mock 모드에서는 더미 음성 반환
        if self.mock_mode:
            return self.MOCK_VOICES
        
        if self._voices_cache:
            return self._voices_cache
        
        try:
            # 동기 API를 비동기로 실행
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                self.client.voices.get_all
            )
            
            self._voices_cache = [
                VoiceInfo(
                    voice_id=voice.voice_id,
                    name=voice.name,
                    labels=voice.labels or {},
                )
                for voice in response.voices
            ]
            return self._voices_cache
            
        except Exception as e:
            raise Exception(f"ElevenLabs API 오류: {str(e)}")
    
    async def assign_voices(
        self,
        speakers: List[str],
        voice_agent: Optional[str] = None,
        voice_customer: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        화자별 음성 할당
        
        Args:
            speakers: 화자 목록
            voice_agent: 상담사 음성 ID (없으면 랜덤)
            voice_customer: 고객 음성 ID (없으면 랜덤)
            
        Returns:
            화자 -> 음성 ID 매핑
        """
        voices = await self.get_available_voices()
        
        if not voices:
            raise Exception("사용 가능한 음성이 없습니다.")
        
        available_ids = [v.voice_id for v in voices]
        
        for speaker in speakers:
            if speaker in self._voice_assignments:
                continue
            
            if speaker == "상담사":
                if voice_agent and voice_agent in available_ids:
                    self._voice_assignments[speaker] = voice_agent
                else:
                    self._voice_assignments[speaker] = random.choice(available_ids)
            elif speaker == "고객":
                if voice_customer and voice_customer in available_ids:
                    self._voice_assignments[speaker] = voice_customer
                else:
                    # 상담사와 다른 음성 선택
                    agent_voice = self._voice_assignments.get("상담사")
                    other_voices = [v for v in available_ids if v != agent_voice]
                    if other_voices:
                        self._voice_assignments[speaker] = random.choice(other_voices)
                    else:
                        self._voice_assignments[speaker] = random.choice(available_ids)
            else:
                self._voice_assignments[speaker] = random.choice(available_ids)
        
        return self._voice_assignments
    
    def _generate_mock_audio(self, text: str, speaker: str, output_path: str) -> str:
        """
        [advice from AI] Mock 모드용 더미 오디오 생성
        텍스트 길이에 비례한 톤 오디오를 생성 (화자별 다른 주파수)
        
        Args:
            text: 텍스트 (길이로 오디오 길이 결정)
            speaker: 화자 (주파수 결정)
            output_path: 출력 경로
            
        Returns:
            저장된 파일 경로
        """
        # 텍스트 길이로 오디오 길이 계산 (초당 약 5.5자)
        char_count = len(text.replace(' ', ''))
        duration_ms = int((char_count / 5.5) * 1000)
        duration_ms = max(500, min(duration_ms, 30000))  # 0.5초 ~ 30초
        
        # 화자별 다른 주파수 (상담사: 낮은 톤, 고객: 높은 톤)
        if speaker == "상담사":
            frequency = 220  # A3
        else:
            frequency = 330  # E4
        
        # 톤 생성 (무음 대신 구분 가능한 톤)
        tone = Sine(frequency).to_audio_segment(duration=duration_ms)
        tone = tone - 20  # 볼륨 낮추기
        
        # MP3로 저장
        tone.export(output_path, format="mp3")
        
        return output_path
    
    async def generate_speech(
        self,
        text: str,
        speaker: str,
        output_path: str,
    ) -> str:
        """
        텍스트를 음성으로 변환하여 파일로 저장
        
        Args:
            text: 변환할 텍스트
            speaker: 화자
            output_path: 출력 파일 경로
            
        Returns:
            저장된 파일 경로
        """
        # [advice from AI] Mock 모드에서는 더미 오디오 생성
        if self.mock_mode:
            return self._generate_mock_audio(text, speaker, output_path)
        
        voice_id = self._voice_assignments.get(speaker)
        
        if not voice_id:
            raise Exception(f"화자 '{speaker}'에 대한 음성이 할당되지 않았습니다.")
        
        try:
            # 동기 API를 비동기로 실행
            loop = asyncio.get_event_loop()
            
            def _generate():
                audio = self.client.text_to_speech.convert(
                    voice_id=voice_id,
                    text=text,
                    model_id="eleven_multilingual_v2",  # 다국어 지원 모델
                    output_format="pcm_44100",  # PCM 형식으로 받아서 직접 처리
                )
                
                # 오디오 데이터 수집
                audio_data = b''.join(chunk for chunk in audio)
                
                # 파일로 저장 (PCM 데이터)
                with open(output_path, 'wb') as f:
                    f.write(audio_data)
                
                return output_path
            
            result = await loop.run_in_executor(None, _generate)
            return result
            
        except Exception as e:
            raise Exception(f"TTS 생성 실패 ({speaker}): {str(e)}")
    
    async def generate_speech_mp3(
        self,
        text: str,
        speaker: str,
        output_path: str,
    ) -> str:
        """
        텍스트를 MP3 음성으로 변환하여 파일로 저장
        (pydub에서 처리하기 용이한 형식)
        
        Args:
            text: 변환할 텍스트
            speaker: 화자
            output_path: 출력 파일 경로 (.mp3)
            
        Returns:
            저장된 파일 경로
        """
        # [advice from AI] Mock 모드에서는 더미 오디오 생성
        if self.mock_mode:
            return self._generate_mock_audio(text, speaker, output_path)
        
        voice_id = self._voice_assignments.get(speaker)
        
        if not voice_id:
            raise Exception(f"화자 '{speaker}'에 대한 음성이 할당되지 않았습니다.")
        
        try:
            loop = asyncio.get_event_loop()
            
            def _generate():
                audio = self.client.text_to_speech.convert(
                    voice_id=voice_id,
                    text=text,
                    model_id="eleven_multilingual_v2",
                    output_format="mp3_44100_128",  # MP3 형식
                )
                
                # 오디오 데이터 수집
                audio_data = b''.join(chunk for chunk in audio)
                
                # 파일로 저장
                with open(output_path, 'wb') as f:
                    f.write(audio_data)
                
                return output_path
            
            result = await loop.run_in_executor(None, _generate)
            return result
            
        except Exception as e:
            raise Exception(f"TTS 생성 실패 ({speaker}): {str(e)}")
    
    def get_voice_assignment(self, speaker: str) -> Optional[str]:
        """특정 화자의 음성 ID 조회"""
        return self._voice_assignments.get(speaker)
    
    def clear_assignments(self):
        """음성 할당 초기화"""
        self._voice_assignments.clear()
