"""
상수 정의 모듈

애플리케이션 전반에서 사용되는 상수값을 정의합니다.
"""

# 데이터베이스 관련 상수
DATABASE_PATH = "media_index.db"
DB_TABLES = {
    "MEDIA": "media_files",
    "SUBTITLES": "subtitles",
    "BOOKMARKS": "bookmarks",
    "TAGS": "tags",
    "MEDIA_TAGS": "media_tags"
}

# 미디어 관련 상수
DEFAULT_MEDIA_EXTENSIONS = [".mp4", ".mkv", ".avi", ".mov", ".wmv"]
DEFAULT_SUBTITLE_EXTENSION = ".srt"
DEFAULT_MIN_ENGLISH_RATIO = 0.2

# 인덱싱 관련 상수
DEFAULT_MAX_THREADS = 8
DEFAULT_INDEXING_STRATEGY = "standard"  # 'standard', 'batch', 'parallel', 'delayed_language'
MAX_LOG_ENTRIES = 100
INDEXING_STATUS_FILE = "indexing_status.json"

# 검색 관련 상수
MAX_SEARCH_RESULTS = 1000
DEFAULT_SEARCH_LIMIT = 50
MIN_SEARCH_TERM_LENGTH = 2
SEARCH_HIGHLIGHT_PRE = "<mark>"
SEARCH_HIGHLIGHT_POST = "</mark>"

# 시스템 관련 상수
CONFIG_FILE_PATH = "config.json"
LOG_FILE_NAME = {
    "DATABASE": "logs/database_debug.log",
    "DATABASE_VERBOSE": "logs/database_verbose.log",
    "INDEXER": "logs/indexer.log",
    "INDEXER_VERBOSE": "logs/indexer_verbose.log",
    "API_DOCS": "logs/api_docs_generator.log"
}

# 경로 관련 상수
STATIC_FOLDER = "static"
TEMPLATES_FOLDER = "templates"

# API 관련 상수
API_PREFIX = "/api"
DEFAULT_RESPONSE_LIMIT = 100 