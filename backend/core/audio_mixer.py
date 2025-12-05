# [advice from AI] 오디오 합성 모듈
import os
from typing import List
from pydub import AudioSegment

from backend.config import get_settings
from backend.core.timestamp import TimestampedDialogue


class AudioMixer:
    """오디오 파일 합성기"""
    
    def __init__(self):
        self.settings = get_settings()
        self.sample_rate = self.settings.audio_sample_rate
        self.channels = self.settings.audio_channels
    
    def create_silence(self, duration_ms: int) -> AudioSegment:
        """
        무음 구간 생성
        
        Args:
            duration_ms: 무음 길이 (밀리초)
            
        Returns:
            무음 AudioSegment
        """
        return AudioSegment.silent(
            duration=duration_ms,
            frame_rate=self.sample_rate,
        )
    
    def load_audio(self, file_path: str) -> AudioSegment:
        """
        오디오 파일 로드
        
        Args:
            file_path: 파일 경로
            
        Returns:
            AudioSegment 객체
        """
        # 확장자에 따라 포맷 결정
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == '.mp3':
            audio = AudioSegment.from_mp3(file_path)
        elif ext == '.wav':
            audio = AudioSegment.from_wav(file_path)
        elif ext == '.pcm' or ext == '':
            # PCM raw 데이터
            audio = AudioSegment.from_raw(
                file_path,
                sample_width=2,  # 16-bit
                frame_rate=self.sample_rate,
                channels=1,
            )
        else:
            # 자동 감지
            audio = AudioSegment.from_file(file_path)
        
        return audio
    
    def mix_dialogues(
        self,
        timestamped_dialogues: List[TimestampedDialogue],
        audio_files: List[str],
        output_path: str,
    ) -> str:
        """
        타임스탬프에 따라 오디오 파일들을 합성
        
        Args:
            timestamped_dialogues: 타임스탬프가 적용된 대화 목록
            audio_files: 각 대화에 해당하는 오디오 파일 경로 목록
            output_path: 출력 파일 경로
            
        Returns:
            저장된 파일 경로
        """
        if len(timestamped_dialogues) != len(audio_files):
            raise ValueError("대화 수와 오디오 파일 수가 일치하지 않습니다.")
        
        if not timestamped_dialogues:
            raise ValueError("합성할 대화가 없습니다.")
        
        # 결과 오디오 초기화 (빈 오디오)
        result = AudioSegment.empty()
        current_position = 0  # 밀리초 단위
        
        for ts_dialogue, audio_file in zip(timestamped_dialogues, audio_files):
            # 시작 시간까지 무음 추가
            target_start_ms = int(ts_dialogue.start_time * 1000)
            
            if target_start_ms > current_position:
                silence_duration = target_start_ms - current_position
                result += self.create_silence(silence_duration)
                current_position = target_start_ms
            
            # 오디오 로드 및 추가
            try:
                audio = self.load_audio(audio_file)
                
                # 모노로 변환 (필요시)
                if audio.channels > 1 and self.channels == 1:
                    audio = audio.set_channels(1)
                
                # 샘플레이트 맞추기
                if audio.frame_rate != self.sample_rate:
                    audio = audio.set_frame_rate(self.sample_rate)
                
                result += audio
                current_position += len(audio)
                
            except Exception as e:
                print(f"오디오 로드 실패 ({audio_file}): {e}")
                # 실패 시 예상 길이만큼 무음으로 대체
                expected_duration = int(ts_dialogue.speech_duration * 1000)
                result += self.create_silence(expected_duration)
                current_position += expected_duration
        
        # 마지막에 짧은 무음 추가 (끝부분 정리)
        result += self.create_silence(500)
        
        # WAV 파일로 저장
        result.export(
            output_path,
            format="wav",
            parameters=[
                "-ar", str(self.sample_rate),
                "-ac", str(self.channels),
            ]
        )
        
        return output_path
    
    def get_audio_duration(self, file_path: str) -> float:
        """
        오디오 파일 길이 조회 (초)
        
        Args:
            file_path: 파일 경로
            
        Returns:
            길이 (초)
        """
        audio = self.load_audio(file_path)
        return len(audio) / 1000.0  # 밀리초 -> 초
    
    def normalize_audio(self, audio: AudioSegment, target_dbfs: float = -20.0) -> AudioSegment:
        """
        오디오 볼륨 정규화
        
        Args:
            audio: 오디오 세그먼트
            target_dbfs: 목표 dBFS
            
        Returns:
            정규화된 오디오
        """
        change_in_dbfs = target_dbfs - audio.dBFS
        return audio.apply_gain(change_in_dbfs)

