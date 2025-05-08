"""
도움 함수 모듈

애플리케이션 전반에서 사용되는 유틸리티 함수를 정의합니다.
"""

import os
import re
import chardet
import time
from pathlib import Path
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from typing import Dict, List, Any, Optional, Tuple, Union


def time_to_ms(time_obj) -> int:
    """
    pysrt의 SubRipTime 객체를 밀리초로 변환
    
    Args:
        time_obj: SubRipTime 객체
        
    Returns:
        int: 밀리초 단위의 시간
    """
    return (time_obj.hours * 3600 + time_obj.minutes * 60 + time_obj.seconds) * 1000 + time_obj.milliseconds


def ms_to_timestamp(ms: int) -> str:
    """
    밀리초를 시:분:초.밀리초 형식의 타임스탬프로 변환
    
    Args:
        ms: 밀리초 단위의 시간
        
    Returns:
        str: HH:MM:SS.mmm 형식의 타임스탬프
    """
    seconds, milliseconds = divmod(ms, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    
    return f"{hours:02}:{minutes:02}:{seconds:02}.{milliseconds:03}"


def timestamp_to_ms(timestamp: str) -> int:
    """
    HH:MM:SS.mmm 형식의 타임스탬프를 밀리초로 변환
    
    Args:
        timestamp: HH:MM:SS.mmm 형식의 타임스탬프
        
    Returns:
        int: 밀리초 단위의 시간
    """
    pattern = r'(\d+):(\d+):(\d+)(?:\.(\d+))?'
    match = re.match(pattern, timestamp)
    
    if not match:
        raise ValueError(f"잘못된 타임스탬프 형식: {timestamp}")
    
    hours, minutes, seconds, milliseconds = match.groups()
    hours = int(hours)
    minutes = int(minutes)
    seconds = int(seconds)
    milliseconds = int(milliseconds or 0)
    
    return (hours * 3600 + minutes * 60 + seconds) * 1000 + milliseconds


def remove_html_tags(text: str) -> str:
    """
    HTML 태그 제거
    
    Args:
        text: HTML 태그가 포함된 텍스트
        
    Returns:
        str: HTML 태그가 제거된 텍스트
    """
    soup = BeautifulSoup(f"<div>{text}</div>", 'html.parser')
    return soup.div.get_text()


def detect_encoding(file_path: str) -> str:
    """
    파일의 인코딩 탐지
    
    Args:
        file_path: 파일 경로
        
    Returns:
        str: 탐지된 인코딩 (기본값: utf-8)
    """
    try:
        with open(file_path, 'rb') as file:
            raw_data = file.read(4096)  # 샘플 데이터만 읽음
            result = chardet.detect(raw_data)
            return result['encoding'] or 'utf-8'
    except Exception:
        return 'utf-8'


def is_english_subtitle(text: str, min_ratio: float = 0.7) -> bool:
    """
    텍스트가 주로 영어인지 판별
    
    Args:
        text: 검사할 텍스트
        min_ratio: 영어로 판단할 최소 영문 비율 (0.0 ~ 1.0)
        
    Returns:
        bool: 영어 자막 여부
    """
    # 간단한 영어 단어 패턴 (공백으로 구분된 영문자)
    english_word_pattern = re.compile(r'[a-zA-Z]+')
    
    # 모든 단어 추출
    words = text.lower().split()
    if not words:
        return False
        
    # 영어 단어 개수
    english_words = [w for w in words if english_word_pattern.fullmatch(w)]
    english_ratio = len(english_words) / len(words)
    
    return english_ratio >= min_ratio


def get_file_extension(file_path: str) -> str:
    """
    파일 확장자 추출
    
    Args:
        file_path: 파일 경로
        
    Returns:
        str: 소문자로 변환된 파일 확장자 (.포함)
    """
    return os.path.splitext(file_path)[1].lower()


def get_file_name(file_path: str) -> str:
    """
    파일 이름 추출 (확장자 제외)
    
    Args:
        file_path: 파일 경로
        
    Returns:
        str: 파일 이름 (확장자 제외)
    """
    return os.path.splitext(os.path.basename(file_path))[0]


def get_relative_path(base_path: str, full_path: str) -> str:
    """
    기준 경로에 대한 상대 경로 반환
    
    Args:
        base_path: 기준 경로
        full_path: 전체 경로
        
    Returns:
        str: 상대 경로
    """
    return os.path.relpath(full_path, base_path)


def get_media_paths(
    media_path: str, 
    subtitle_extension: str = ".srt"
) -> Tuple[str, Optional[str]]:
    """
    미디어 파일 경로로부터 자막 파일 경로 추정
    
    Args:
        media_path: 미디어 파일 경로
        subtitle_extension: 자막 파일 확장자
        
    Returns:
        Tuple[str, Optional[str]]: (미디어 파일 경로, 자막 파일 경로 또는 None)
    """
    media_base = os.path.splitext(media_path)[0]
    subtitle_path = f"{media_base}{subtitle_extension}"
    
    if os.path.exists(subtitle_path):
        return media_path, subtitle_path
    
    # 대체 자막 파일 이름 패턴 확인
    alt_patterns = [
        f"{media_base}.en{subtitle_extension}",
        f"{media_base}.eng{subtitle_extension}",
        f"{media_base}_eng{subtitle_extension}",
        f"{media_base}_en{subtitle_extension}",
        f"{media_base}.english{subtitle_extension}"
    ]
    
    for alt_path in alt_patterns:
        if os.path.exists(alt_path):
            return media_path, alt_path
    
    return media_path, None


def format_bytes(size: int) -> str:
    """
    바이트 크기를 사람이 읽기 쉬운 형식으로 변환
    
    Args:
        size: 바이트 단위 크기
        
    Returns:
        str: 사람이 읽기 쉬운 형식의 크기 (예: "1.23 MB")
    """
    # 2^10 = 1024
    power = 2**10
    n = 0
    power_labels = {0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    
    while size > power and n <= 4:
        size /= power
        n += 1
        
    return f"{size:.2f} {power_labels.get(n, '')}B"


def format_time_duration(seconds: Union[int, float]) -> str:
    """
    초 단위 시간을 사람이 읽기 쉬운 형식으로 변환
    
    Args:
        seconds: 초 단위 시간
        
    Returns:
        str: 사람이 읽기 쉬운 형식의 시간 (예: "2시간 30분", "5분 10초")
    """
    if seconds < 60:
        return f"{seconds:.0f}초"
    
    minutes, seconds = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes:.0f}분 {seconds:.0f}초"
    
    hours, minutes = divmod(minutes, 60)
    if hours < 24:
        return f"{hours:.0f}시간 {minutes:.0f}분"
    
    days, hours = divmod(hours, 24)
    return f"{days:.0f}일 {hours:.0f}시간"


def get_estimated_completion_time(
    processed: int, 
    total: int, 
    start_time: Optional[datetime] = None,
    elapsed_seconds: Optional[float] = None
) -> Optional[str]:
    """
    진행 상황을 기반으로 예상 완료 시간 계산
    
    Args:
        processed: 처리된 항목 수
        total: 전체 항목 수
        start_time: 시작 시간 (None인 경우 elapsed_seconds 사용)
        elapsed_seconds: 경과 시간 (초) (start_time이 None인 경우에만 사용)
        
    Returns:
        Optional[str]: 예상 완료 시간 (HH:MM:SS 형식) 또는 None
    """
    if processed <= 0 or total <= 0:
        return None
    
    try:
        # 경과 시간 계산
        if start_time is not None:
            elapsed_seconds = (datetime.now() - start_time).total_seconds()
        elif elapsed_seconds is None:
            return None
        
        # 평균 처리 시간 계산
        avg_time_per_item = elapsed_seconds / processed
        
        # 남은 항목 수
        remaining_items = total - processed
        
        # 남은 시간 계산
        eta_seconds = remaining_items * avg_time_per_item
        
        # 남은 시간을 시:분:초 형태로 변환
        eta = str(timedelta(seconds=int(eta_seconds)))
        
        return eta
    except Exception:
        return None


def wait_with_timeout(condition_func, timeout_seconds=10, check_interval=0.1):
    """
    조건이 만족될 때까지 대기 (타임아웃 포함)
    
    Args:
        condition_func: 조건 확인 함수 (True/False 반환)
        timeout_seconds: 최대 대기 시간 (초)
        check_interval: 조건 확인 간격 (초)
        
    Returns:
        bool: 조건 만족 여부 (타임아웃 시 False)
    """
    start_time = time.time()
    
    while time.time() - start_time < timeout_seconds:
        if condition_func():
            return True
        time.sleep(check_interval)
    
    return False 