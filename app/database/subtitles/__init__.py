"""
자막 데이터 관리 모듈

자막 정보의 저장, 조회, 검색 등을 담당하는 모듈입니다.
"""

from app.database.subtitles.init import init_subtitle_db
from app.database.subtitles.insert import insert_subtitle
from app.database.subtitles.info import (
    get_subtitle_info, save_subtitle_info,
    get_media_subtitle_info, save_media_subtitle_info,
    log_processing, get_subtitles_for_media
)
from app.database.subtitles.stats import (
    get_encoding_stats, get_subtitles_by_encoding,
    get_subtitle_encoding_status, get_subtitle_stats,
    get_subtitle_length_distribution
)
from app.database.subtitles.search import (
    search_subtitles, estimate_total_count
)
from app.database.subtitles.fts import (
    rebuild_fts_index, add_subtitle_to_fts
)
from app.database.subtitles.cleanup import (
    clear_subtitles_for_media
)

# 처리 대기 자막 관련 함수
from app.database.subtitles.info import (
    get_unprocessed_subtitles, get_broken_subtitles,
    get_multi_subtitles, get_media_without_subtitles
)

__all__ = [
    # 초기화
    'init_subtitle_db',
    
    # 자막 정보 관리
    'get_subtitle_info', 'save_subtitle_info',
    'get_media_subtitle_info', 'save_media_subtitle_info',
    'log_processing', 'get_subtitles_for_media',
    
    # 자막 삽입
    'insert_subtitle',
    
    # 통계
    'get_encoding_stats', 'get_subtitles_by_encoding',
    'get_subtitle_encoding_status', 'get_subtitle_stats',
    'get_subtitle_length_distribution',
    
    # 검색
    'search_subtitles', 'estimate_total_count',
    
    # FTS
    'rebuild_fts_index', 'add_subtitle_to_fts',
    
    # 정리
    'clear_subtitles_for_media',
    
    # 처리 대기 자막
    'get_unprocessed_subtitles', 'get_broken_subtitles',
    'get_multi_subtitles', 'get_media_without_subtitles',
]
