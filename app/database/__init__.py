"""
데이터베이스 접근 계층 패키지

데이터베이스 연결 및 CRUD 작업을 처리하는 모듈을 제공합니다.
"""

from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Any, Optional

from app.database.schema import (
    init_db, 
    reset_database, 
    rebuild_fts_index,
    get_table_list,
    get_table_data
)

from app.database.connection import (
    get_connection,
    get_db_path,
    backup_database
)

# 미디어 관련 모듈 임포트
from app.database.media import (
    # 삽입 및 수정
    insert_media,
    upsert_media,
    update_subtitle_status,
    delete_media,
    
    # 조회
    get_media_info,
    get_media_by_path,
    get_all_media,
    count_media,
    get_total_media_count,
    get_indexed_media_paths,
    
    # 통계
    get_media_stats
)

# 작업 관련 모듈 임포트
from app.database.jobs import (
    # 작업 상태 관리
    get_job_status,
    update_job_status,
    get_all_jobs,
    create_job,
    complete_job,
    fail_job,
    get_job_progress,
    
    # 재시도 정책
    should_retry_job,
    increment_retry_count,
    reset_retry_count
)

# 자막 관련 모듈 임포트
from app.database.subtitles import (
    # 초기화
    init_subtitle_db,
    
    # 자막 정보 관리
    get_subtitle_info, save_subtitle_info,
    get_media_subtitle_info, save_media_subtitle_info,
    log_processing, get_subtitles_for_media,
    
    # 자막 삽입
    insert_subtitle,
    
    # 통계
    get_encoding_stats, get_subtitles_by_encoding,
    get_subtitle_encoding_status, get_subtitle_stats,
    get_subtitle_length_distribution,
    
    # 검색
    search_subtitles, estimate_total_count,
    
    # FTS
    rebuild_fts_index, add_subtitle_to_fts,
    
    # 정리
    clear_subtitles_for_media,
    
    # 처리 대기 자막
    get_unprocessed_subtitles, get_broken_subtitles,
    get_multi_subtitles, get_media_without_subtitles
)

from app.database.cleanup import (
    remove_duplicate_media_files,
    get_subtitle_file_count
)

def get_daily_indexing_stats(days: int = 7) -> List[Tuple[str, int]]:
    """
    일일 인덱싱 통계를 반환
    
    Args:
        days: 조회할 일수
        
    Returns:
        List[Tuple[str, int]]: 날짜별 인덱싱된 파일 수
    """
    # 실제 구현은 데이터베이스에 따라 다를 수 있으므로 예시만 반환
    # 일단 리팩토링 전 함수와 동일하게 구현
    
    # 예시 데이터 생성
    stats = []
    today = datetime.now()
    
    for i in range(days):
        date = (today - timedelta(days=i)).strftime('%Y-%m-%d')
        count = 100 - i * 10  # 예시 데이터
        stats.append((date, max(0, count)))
    
    return list(reversed(stats))

# 편의를 위한 Database 클래스 정의
class Database:
    """
    데이터베이스 관리 클래스
    기존 코드와의 호환성을 위해 유지되며, 내부적으로는 모듈화된 함수들을 호출합니다.
    """
    
    def __init__(self):
        """데이터베이스 관리 클래스 초기화"""
        self.init_db()
    
    def get_db_path(self):
        """데이터베이스 경로 반환"""
        return get_db_path()
    
    def get_connection(self):
        """데이터베이스 연결 객체 반환"""
        return get_connection()
    
    def init_db(self):
        """데이터베이스 초기화 및 필요한 테이블 생성"""
        return init_db()
    
    def reset_database(self):
        """데이터베이스를 완전히 초기화 (모든 데이터 삭제)"""
        return reset_database()
    
    def has_indexed_files(self):
        """인덱싱된 파일이 있는지 확인"""
        return count_media() > 0
    
    def insert_media(self, path, has_subtitle=False, size=0, last_modified=None):
        """미디어 파일 정보 저장"""
        return insert_media(path, has_subtitle, size, last_modified)
    
    def upsert_media(self, media_path):
        """미디어 파일 정보 갱신 또는 삽입"""
        return upsert_media(media_path)
    
    def insert_subtitle(self, media_id, start_ms, end_ms, start_text, end_text, content, lang='en'):
        """자막 정보 저장"""
        return insert_subtitle(media_id, start_ms, end_ms, start_text, end_text, content, lang)
    
    def clear_subtitles_for_media(self, media_id):
        """특정 미디어의 모든 자막 삭제"""
        return clear_subtitles_for_media(media_id)
    
    def search_subtitles(self, query, lang=None, start_time=None, end_time=None, page=1, per_page=50, search_method='fts'):
        """
        자막 내용 검색
        
        Args:
            query: 검색어
            lang: 언어 필터
            start_time: 시작 시간 필터 (HH:MM:SS)
            end_time: 종료 시간 필터 (HH:MM:SS)
            page: 페이지 번호 (1부터 시작)
            per_page: 페이지당 결과 수
            search_method: 검색 방식 ('like' 또는 'fts', 기본값: 'fts')
            
        Returns:
            List[Dict[str, Any]]: 검색 결과 목록
        """
        return search_subtitles(query, lang, start_time, end_time, page, per_page, search_method)
    
    def estimate_total_count(self, query, lang=None, start_time=None, end_time=None):
        """검색 조건에 맞는 총 결과 수 추정"""
        return estimate_total_count(query, lang, start_time, end_time)
    
    def get_all_stats(self):
        """모든 통계 정보를 반환"""
        media_stats = get_media_stats()
        subtitle_stats = get_subtitle_stats()
        
        return {
            "media_count": media_stats["total"],
            "subtitle_count": subtitle_stats["total"],
            "subtitles_ratio": {
                "percentage": media_stats["subtitle_coverage_percent"],
                "has_subtitles": media_stats["with_subtitle"],
                "total": media_stats["total"]
            },
            "language_stats": [
                {"lang": lang, "count": count} 
                for lang, count in subtitle_stats["languages"].items()
            ]
        }
    
    def get_media_stats(self):
        """미디어 통계 정보를 반환합니다."""
        return get_media_stats()
    
    def get_indexed_media_paths(self):
        """인덱싱된 모든 미디어 파일 경로 목록을 반환합니다."""
        return get_indexed_media_paths()
    
    def get_subtitle_length_distribution(self):
        """자막 길이 분포 반환"""
        return get_subtitle_length_distribution()
    
    def get_subtitle_stats(self):
        """자막 통계 정보 조회"""
        return get_subtitle_stats()
    
    def get_daily_indexing_stats(self, days=7):
        """일일 인덱싱 통계를 반환"""
        return get_daily_indexing_stats(days)
    
    def rebuild_fts_index(self, force: bool = False):
        """
        FTS 인덱스 재구축
        
        Args:
            force: 강제 재구축 여부 (True인 경우 기존 테이블 삭제 후 재생성)
            
        Returns:
            bool: 성공 여부
        """
        return rebuild_fts_index(force=force)
    
    def get_table_list(self):
        """데이터베이스 테이블 목록 조회"""
        return get_table_list()
    
    def get_table_data(self, table_name, limit=100, offset=0):
        """테이블 데이터 조회"""
        return get_table_data(table_name, limit, offset)

# 기본 데이터베이스 인스턴스
db = Database()
