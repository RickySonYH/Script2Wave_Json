# [advice from AI] 타임스탬프 생성 모듈
import random
from dataclasses import dataclass
from typing import List

from backend.config import get_settings
from backend.core.parser import Dialogue, ParsedScript


@dataclass
class TimestampedDialogue:
    """타임스탬프가 적용된 대화"""
    dialogue: Dialogue
    start_time: float      # 시작 시간 (초)
    end_time: float        # 종료 시간 (초)
    speech_duration: float # 발화 시간 (초)
    pause_before: float    # 이전 대화 후 무음 시간 (초)


def calculate_speech_duration(text: str, speech_rate: float = 5.5) -> float:
    """
    텍스트 발화 시간 계산
    
    Args:
        text: 발화 텍스트
        speech_rate: 초당 글자 수 (기본 5.5자/초, 한국어 기준)
        
    Returns:
        발화 시간 (초)
    """
    # 공백 제외 글자 수
    char_count = len(text.replace(' ', ''))
    
    if char_count == 0:
        return 0.5  # 최소 발화 시간
    
    duration = char_count / speech_rate
    
    # 최소/최대 제한
    return max(0.5, min(duration, 60.0))


def calculate_pause_duration(
    prev_speaker: str,
    curr_speaker: str,
    delays: List[float],
    turn_gap_min: float = 0.5,
    turn_gap_max: float = 1.5,
) -> float:
    """
    대화 간 무음(pause) 시간 계산
    
    Args:
        prev_speaker: 이전 화자
        curr_speaker: 현재 화자
        delays: [DELAY: Xs] 태그에서 추출된 지연 시간 목록
        turn_gap_min: 화자 교체 시 최소 간격
        turn_gap_max: 화자 교체 시 최대 간격
        
    Returns:
        무음 시간 (초)
    """
    pause = 0.0
    
    # 명시된 DELAY가 있으면 합산
    if delays:
        pause += sum(delays)
    
    # 화자 교체 시 턴테이킹 간격 추가
    if prev_speaker and prev_speaker != curr_speaker:
        pause += random.uniform(turn_gap_min, turn_gap_max)
    elif prev_speaker == curr_speaker:
        # 같은 화자 연속 발화 시 짧은 간격
        pause += random.uniform(0.2, 0.5)
    
    return pause


def calculate_action_duration(actions: List[str], base_duration: float = 2.0) -> float:
    """
    [ACTION] 태그에 따른 추가 시간 계산
    
    Args:
        actions: ACTION 태그 목록
        base_duration: 기본 액션 소요 시간
        
    Returns:
        액션 소요 시간 (초)
    """
    if not actions:
        return 0.0
    
    total = 0.0
    for action in actions:
        action_lower = action.lower()
        
        # 액션 유형에 따른 시간 조정
        if '조회' in action_lower or '확인' in action_lower:
            total += base_duration * 1.5
        elif '등록' in action_lower or '접수' in action_lower:
            total += base_duration * 1.2
        elif '발송' in action_lower:
            total += base_duration * 0.8
        else:
            total += base_duration
    
    return total


def generate_timestamps(parsed: ParsedScript) -> List[TimestampedDialogue]:
    """
    파싱된 대화록에 타임스탬프 생성
    
    Args:
        parsed: 파싱된 대화록
        
    Returns:
        타임스탬프가 적용된 대화 목록
    """
    settings = get_settings()
    
    timestamped: List[TimestampedDialogue] = []
    current_time = 0.0
    prev_speaker = ""
    
    for dialogue in parsed.dialogues:
        # 1. 이전 대화 후 무음 시간 계산
        pause_before = calculate_pause_duration(
            prev_speaker=prev_speaker,
            curr_speaker=dialogue.speaker,
            delays=dialogue.delays,
            turn_gap_min=settings.turn_gap_min,
            turn_gap_max=settings.turn_gap_max,
        )
        
        # 2. ACTION 태그에 따른 추가 시간 (발화 전에 발생)
        action_duration = calculate_action_duration(
            dialogue.actions,
            settings.action_duration,
        )
        
        # 3. 발화 시간 계산
        speech_duration = calculate_speech_duration(
            dialogue.text,
            settings.speech_rate,
        )
        
        # 4. 타임스탬프 계산
        start_time = current_time + pause_before + action_duration
        end_time = start_time + speech_duration + settings.silence_padding
        
        timestamped_dialogue = TimestampedDialogue(
            dialogue=dialogue,
            start_time=start_time,
            end_time=end_time,
            speech_duration=speech_duration,
            pause_before=pause_before + action_duration,
        )
        timestamped.append(timestamped_dialogue)
        
        # 5. 현재 시간 업데이트
        current_time = end_time
        prev_speaker = dialogue.speaker
    
    return timestamped


def get_total_duration(timestamped: List[TimestampedDialogue]) -> float:
    """전체 녹취 시간 계산"""
    if not timestamped:
        return 0.0
    return timestamped[-1].end_time


def format_timestamp(seconds: float) -> str:
    """초를 MM:SS.mmm 형식으로 변환"""
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes:02d}:{secs:06.3f}"

