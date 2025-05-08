"""
유틸리티 모듈 패키지

애플리케이션 전반에서 사용되는 유틸리티 기능을 제공합니다.
"""

# helpers 모듈에서 자주 사용되는 함수 가져오기
from .helpers import (
    time_to_ms,
    ms_to_timestamp,
    timestamp_to_ms,
    remove_html_tags,
    detect_encoding,
    is_english_subtitle,
    get_file_extension,
    get_file_name,
    get_relative_path,
    get_media_paths,
    format_bytes,
    format_time_duration,
    get_estimated_completion_time,
    wait_with_timeout
)

# constants 모듈에서 상수 가져오기
from .constants import (
    DATABASE_PATH,
    DB_TABLES,
    DEFAULT_MEDIA_EXTENSIONS,
    DEFAULT_SUBTITLE_EXTENSION,
    DEFAULT_MIN_ENGLISH_RATIO,
    DEFAULT_MAX_THREADS,
    DEFAULT_INDEXING_STRATEGY,
    MAX_LOG_ENTRIES,
    INDEXING_STATUS_FILE,
    MAX_SEARCH_RESULTS,
    DEFAULT_SEARCH_LIMIT,
    CONFIG_FILE_PATH
)

# logging 모듈에서 로거 생성 함수 가져오기
from .logging import (
    setup_logger,
    get_database_logger,
    get_indexer_logger,
    get_api_logger,
    PathStrippingFilter
)

__all__ = [
    # helpers
    'time_to_ms', 'ms_to_timestamp', 'timestamp_to_ms',
    'remove_html_tags', 'detect_encoding', 'is_english_subtitle',
    'get_file_extension', 'get_file_name', 'get_relative_path',
    'get_media_paths', 'format_bytes', 'format_time_duration',
    'get_estimated_completion_time', 'wait_with_timeout',
    
    # constants
    'DATABASE_PATH', 'DB_TABLES', 'DEFAULT_MEDIA_EXTENSIONS',
    'DEFAULT_SUBTITLE_EXTENSION', 'DEFAULT_MIN_ENGLISH_RATIO',
    'DEFAULT_MAX_THREADS', 'DEFAULT_INDEXING_STRATEGY',
    'MAX_LOG_ENTRIES', 'INDEXING_STATUS_FILE',
    'MAX_SEARCH_RESULTS', 'DEFAULT_SEARCH_LIMIT', 'CONFIG_FILE_PATH',
    
    # logging
    'setup_logger', 'get_database_logger', 'get_indexer_logger',
    'get_api_logger', 'PathStrippingFilter'
]
