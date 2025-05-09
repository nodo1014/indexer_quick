"""
미디어 데이터 관리 모듈

미디어 파일 정보의 저장, 조회, 통계 등을 담당하는 모듈입니다.
"""

from app.database.media.insert import (
    insert_media,
    upsert_media,
    update_subtitle_status,
    delete_media
)

from app.database.media.query import (
    get_media_info,
    get_media_by_path,
    get_all_media,
    count_media,
    get_total_media_count,
    get_indexed_media_paths
)

from app.database.media.stats import (
    get_media_stats
)

# 향후 cleanup 모듈에서 함수 추가 예정
from app.database.media.cleanup import (
    remove_missing_media,
    clear_all_media
)

__all__ = [
    # 삽입 및 수정
    'insert_media', 'upsert_media', 'update_subtitle_status', 'delete_media',
    
    # 조회
    'get_media_info', 'get_media_by_path', 'get_all_media', 'count_media',
    'get_total_media_count', 'get_indexed_media_paths',
    
    # 통계
    'get_media_stats',
    
    # 정리
    'remove_missing_media', 'clear_all_media',
]
