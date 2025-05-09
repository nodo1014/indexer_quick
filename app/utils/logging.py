"""
로깅 설정 모듈

애플리케이션 전반에서 사용되는 로깅 설정을 정의합니다.
"""

import logging
import logging.handlers
import os
from pathlib import Path
from .constants import LOG_FILE_NAME


def setup_module_logger(
    module_name: str,
    log_file: str = None,
    level: int = logging.INFO,
    verbose_file: str = None,
    console_level: int = logging.INFO,
    max_size: int = 5 * 1024 * 1024,  # 5MB
    backup_count: int = 3
):
    """
    모듈별 로거 설정 함수
    
    Args:
        module_name: 모듈 이름 (예: "database.connection")
        log_file: 로그 파일 경로 (None인 경우 기본 로그 파일 사용)
        level: 기본 로그 레벨
        verbose_file: 상세 로그를 저장할 파일 경로
        console_level: 콘솔 출력 로그 레벨
        max_size: 로그 파일 최대 크기 (바이트)
        backup_count: 백업 파일 수
        
    Returns:
        logging.Logger: 설정된 로거 객체
    """
    # 로그 파일이 지정되지 않은 경우 모듈 이름을 바탕으로 기본 경로 설정
    if log_file is None:
        main_module = module_name.split('.')[0]
        if main_module in LOG_FILE_NAME:
            log_file = LOG_FILE_NAME[main_module.upper()]
        else:
            log_dir = os.path.join('logs', main_module)
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, f"{module_name.replace('.', '_')}.log")
    
    # 상세 로그 파일이 지정되지 않은 경우 기본 로그 파일 경로에 _verbose 추가
    if verbose_file is None and log_file:
        verbose_file = log_file.replace('.log', '_verbose.log')
    
    # 기본 로거 설정 함수 호출
    return setup_logger(
        name=module_name,
        log_file=log_file,
        level=level,
        verbose_file=verbose_file,
        console_level=console_level,
        max_size=max_size,
        backup_count=backup_count
    )


def setup_logger(
    name: str,
    log_file: str = None,
    level: int = logging.INFO,
    verbose_file: str = None,
    console_level: int = logging.INFO,
    max_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
):
    """
    로거 설정 함수
    
    Args:
        name: 로거 이름
        log_file: 로그 파일 경로 (None인 경우 파일 로깅 비활성화)
        level: 기본 로그 레벨
        verbose_file: 상세 로그를 저장할 파일 경로 (None인 경우 상세 로깅 비활성화)
        console_level: 콘솔 출력 로그 레벨
        max_size: 로그 파일 최대 크기 (바이트)
        backup_count: 백업 파일 수
        
    Returns:
        logging.Logger: 설정된 로거 객체
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)  # 로거 자체는 모든 레벨 허용
    
    # 핸들러 초기화 - 이미 설정된 핸들러가 있으면 제거
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # 포맷 설정
    log_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    verbose_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(pathname)s:%(lineno)d - %(message)s'
    )
    
    # 파일 핸들러 설정 (기본 로그)
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(log_format)
        logger.addHandler(file_handler)
    
    # 상세 로그용 파일 핸들러 설정
    if verbose_file:
        os.makedirs(os.path.dirname(verbose_file), exist_ok=True)
        verbose_handler = logging.handlers.RotatingFileHandler(
            verbose_file,
            maxBytes=max_size * 2,  # 상세 로그는 더 큰 용량
            backupCount=backup_count,
            encoding='utf-8'
        )
        verbose_handler.setLevel(logging.DEBUG)
        verbose_handler.setFormatter(verbose_format)
        logger.addHandler(verbose_handler)
    
    # 콘솔 핸들러 설정
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(log_format)
    logger.addHandler(console_handler)
    
    return logger


def get_database_logger():
    """
    데이터베이스 로거를 반환합니다.
    
    Returns:
        logging.Logger: 데이터베이스 로거
    """
    return setup_logger(
        name="database",
        log_file=LOG_FILE_NAME["DATABASE"],
        verbose_file=LOG_FILE_NAME["DATABASE_VERBOSE"],
        level=logging.INFO
    )


def get_indexer_logger():
    """
    인덱서 로거를 반환합니다.
    
    Returns:
        logging.Logger: 인덱서 로거
    """
    return setup_module_logger(
        module_name="indexer",
        log_file=LOG_FILE_NAME["INDEXER"],
        level=logging.INFO,  # 기본 로그 레벨을 INFO로 설정
        verbose_file=LOG_FILE_NAME["INDEXER_VERBOSE"],
        console_level=logging.INFO
    )


def get_api_logger():
    """
    API 로거를 반환합니다.
    
    Returns:
        logging.Logger: API 로거
    """
    return setup_logger(
        name="api",
        log_file=LOG_FILE_NAME["API_DOCS"],
        level=logging.INFO
    )


# 로깅 필터 클래스
class PathStrippingFilter(logging.Filter):
    """
    경로 정보를 간소화하는 로깅 필터
    
    긴 파일 경로를 짧게 표시하여 로그 가독성을 높입니다.
    """
    
    def __init__(self, base_path=None):
        """
        필터 초기화
        
        Args:
            base_path: 기준 경로 (None인 경우 현재 작업 디렉토리)
        """
        super().__init__()
        self.base_path = Path(base_path or os.getcwd())
    
    def filter(self, record):
        """
        로그 레코드 필터링
        
        Args:
            record: 로그 레코드
            
        Returns:
            bool: 항상 True (모든 레코드 통과, 단 pathname 수정)
        """
        if hasattr(record, 'pathname'):
            try:
                # 상대 경로로 변환
                relative_path = Path(record.pathname).relative_to(self.base_path)
                record.pathname = str(relative_path)
            except (ValueError, AttributeError):
                # 상대 경로 변환 실패 시 원래 경로 유지
                pass
        return True