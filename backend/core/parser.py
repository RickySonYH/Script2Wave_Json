# [advice from AI] 대화록 파싱 모듈
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class Dialogue:
    """파싱된 대화 한 줄"""
    line_number: int
    speaker: str              # "상담사" 또는 "고객"
    text: str                 # 순수 대사 텍스트
    raw_text: str             # 원본 텍스트 (태그 포함)
    actions: List[str] = field(default_factory=list)   # [ACTION: ...] 목록
    delays: List[float] = field(default_factory=list)  # [DELAY: Xs] 목록 (초)


@dataclass
class ParsedScript:
    """파싱된 대화록 전체"""
    dialogues: List[Dialogue]
    summary: Optional[str] = None
    raw_content: str = ""


# 정규식 패턴
SPEAKER_PATTERN = re.compile(r'^(상담사|고객)\s*:\s*(.+)$', re.MULTILINE)
ACTION_PATTERN = re.compile(r'\[ACTION:\s*([^\]]+)\]')
DELAY_PATTERN = re.compile(r'\[DELAY:\s*([\d.]+)s?\]')
SUMMARY_START = re.compile(r'^---\s*$', re.MULTILINE)
SUMMARY_TAG = re.compile(r'<SCENARIO_SUMMARY>(.*?)</SCENARIO_SUMMARY>', re.DOTALL)


def extract_actions(text: str) -> List[str]:
    """[ACTION: ...] 태그 추출"""
    return ACTION_PATTERN.findall(text)


def extract_delays(text: str) -> List[float]:
    """[DELAY: Xs] 태그에서 초 단위 시간 추출"""
    delays = []
    for match in DELAY_PATTERN.findall(text):
        try:
            delays.append(float(match))
        except ValueError:
            pass
    return delays


def clean_text(text: str) -> str:
    """태그 제거하고 순수 대사만 추출"""
    # [ACTION: ...] 제거
    text = ACTION_PATTERN.sub('', text)
    # [DELAY: ...] 제거
    text = DELAY_PATTERN.sub('', text)
    # 연속 공백 정리
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def parse_script(content: str) -> ParsedScript:
    """
    대화록 텍스트를 파싱하여 구조화된 데이터로 변환
    
    Args:
        content: 대화록 텍스트 전체
        
    Returns:
        ParsedScript: 파싱된 대화록 객체
    """
    dialogues: List[Dialogue] = []
    summary: Optional[str] = None
    
    # --- 구분자로 본문과 요약 분리
    parts = SUMMARY_START.split(content, maxsplit=1)
    main_content = parts[0]
    
    if len(parts) > 1:
        summary_section = parts[1]
        # <SCENARIO_SUMMARY> 태그 내용 추출
        summary_match = SUMMARY_TAG.search(summary_section)
        if summary_match:
            summary = summary_match.group(1).strip()
    
    # 줄별로 파싱
    lines = main_content.split('\n')
    for line_num, line in enumerate(lines, start=1):
        line = line.strip()
        if not line:
            continue
            
        # 화자:대사 패턴 매칭
        match = SPEAKER_PATTERN.match(line)
        if match:
            speaker = match.group(1)
            raw_text = match.group(2)
            
            # 태그 추출
            actions = extract_actions(raw_text)
            delays = extract_delays(raw_text)
            
            # 순수 대사 추출
            text = clean_text(raw_text)
            
            dialogue = Dialogue(
                line_number=line_num,
                speaker=speaker,
                text=text,
                raw_text=raw_text,
                actions=actions,
                delays=delays,
            )
            dialogues.append(dialogue)
    
    return ParsedScript(
        dialogues=dialogues,
        summary=summary,
        raw_content=content,
    )


def validate_script(content: str) -> Tuple[bool, List[str]]:
    """
    대화록 유효성 검증
    
    Returns:
        (is_valid, errors): 유효 여부와 에러 메시지 목록
    """
    errors = []
    
    if not content or not content.strip():
        errors.append("대화록 내용이 비어있습니다.")
        return False, errors
    
    parsed = parse_script(content)
    
    if not parsed.dialogues:
        errors.append("파싱된 대화가 없습니다. '상담사:' 또는 '고객:'으로 시작하는 줄이 필요합니다.")
        return False, errors
    
    # 화자 확인
    speakers = set(d.speaker for d in parsed.dialogues)
    if len(speakers) < 2:
        errors.append(f"대화에 한 명의 화자({list(speakers)[0]})만 있습니다. 두 명의 화자가 필요합니다.")
    
    return len(errors) == 0, errors

