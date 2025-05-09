"""
인코딩/상태 통계 모듈
"""

import logging
from typing import List, Dict, Any, Optional, Tuple, Union

from app.utils.logging import setup_module_logger
from app.config import config
from app.database.connection import get_connection, execute_query, fetch_one, fetch_all, connection_context

# 로거 초기화
logger = setup_module_logger("database.subtitles.stats")

def get_encoding_stats() -> Dict[str, int]:
    """
    자막 인코딩 통계 조회
    
    Returns:
        Dict[str, int]: 인코딩별 자막 수
    """
    try:
        sql = """
        SELECT encoding, COUNT(*) as count
        FROM subtitle_files
        WHERE encoding IS NOT NULL
        GROUP BY encoding
        ORDER BY count DESC
        """
        
        results = fetch_all(sql)
        
        # 딕셔너리로 변환
        stats = {}
        for row in results:
            stats[row['encoding']] = row['count']
            
        return stats
        
    except Exception as e:
        logger.error(f"인코딩 통계 조회 중 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {}

def get_subtitles_by_encoding(encoding: str, limit: int = 1000) -> List[Dict[str, Any]]:
    """
    특정 인코딩의 자막 목록 조회
    
    Args:
        encoding: 인코딩 (예: 'utf-8', 'cp949')
        limit: 최대 조회 개수
        
    Returns:
        List[Dict[str, Any]]: 자막 목록
    """
    try:
        sql = """
        SELECT *
        FROM subtitle_files
        WHERE encoding = ?
        LIMIT ?
        """
        params = (encoding, limit)
        
        results = fetch_all(sql, params)
        return results or []
        
    except Exception as e:
        logger.error(f"인코딩 '{encoding}'의 자막 목록 조회 중 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []

def get_subtitle_encoding_status() -> Dict[str, Any]:
    """
    자막 인코딩 상태 통계 조회
    
    Returns:
        Dict[str, Any]: 인코딩 상태 통계
    """
    try:
        # 전체 자막 수
        total_count = fetch_one("SELECT COUNT(*) as count FROM subtitle_files")
        
        # 인코딩 확인된 자막 수
        encoded_count = fetch_one("SELECT COUNT(*) as count FROM subtitle_files WHERE encoding IS NOT NULL")
        
        # 인코딩 미확인 자막 수
        unknown_count = fetch_one("SELECT COUNT(*) as count FROM subtitle_files WHERE encoding IS NULL")
        
        # 인코딩별 통계
        encoding_stats = get_encoding_stats()
        
        # 결과 조합
        result = {
            "total_count": total_count["count"] if total_count else 0,
            "encoded_count": encoded_count["count"] if encoded_count else 0,
            "unknown_count": unknown_count["count"] if unknown_count else 0,
            "encoding_stats": encoding_stats
        }
        
        return result
        
    except Exception as e:
        logger.error(f"인코딩 상태 통계 조회 중 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {}

def get_subtitle_stats() -> Dict[str, Any]:
    """
    자막 통계 정보 조회
    
    Returns:
        Dict[str, Any]: 자막 통계 정보
    """
    try:
        stats = {}
        
        # 전체 자막 수
        total_count = fetch_one("SELECT COUNT(*) as count FROM subtitles")
        stats["total"] = total_count["count"] if total_count else 0
        stats["total_count"] = total_count["count"] if total_count else 0  # 후방 호환성을 위해 두 개의 키 모두 사용
        
        # 언어별 자막 수
        lang_counts = fetch_all("SELECT lang, COUNT(*) as count FROM subtitles GROUP BY lang ORDER BY count DESC")
        stats["lang_counts"] = lang_counts or []  # 후방 호환성을 위해 유지
        
        # 언어별 자막 수를 디셔너리로 변환
        languages = {}
        for item in lang_counts or []:
            lang = item['lang'] or 'unknown'
            count = item['count']
            languages[lang] = count
        stats["languages"] = languages
        
        # 미디어별 자막 수
        media_counts = fetch_all("""
            SELECT m.id, m.path, COUNT(s.id) as subtitle_count 
            FROM media_files m 
            LEFT JOIN subtitles s ON m.id = s.media_id 
            GROUP BY m.id 
            ORDER BY subtitle_count DESC 
            LIMIT 10
        """)
        stats["media_counts"] = media_counts or []
        
        return stats
        
    except Exception as e:
        logger.error(f"자막 통계 정보 조회 중 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {}

def get_subtitle_length_distribution() -> List[Dict[str, Any]]:
    """
    자막 길이 분포 반환
    
    Returns:
        List[Dict[str, Any]]: 자막 길이 분포 (구간별 개수)
    """
    try:
        # 자막 길이에 따른 분포 계산
        sql = """
            SELECT 
                CASE 
                    WHEN LENGTH(content) <= 10 THEN '0-10'
                    WHEN LENGTH(content) <= 20 THEN '11-20'
                    WHEN LENGTH(content) <= 30 THEN '21-30'
                    WHEN LENGTH(content) <= 50 THEN '31-50'
                    WHEN LENGTH(content) <= 100 THEN '51-100'
                    ELSE '100+'
                END as length_range,
                COUNT(*) as count
            FROM subtitles
            GROUP BY length_range
            ORDER BY 
                CASE length_range
                    WHEN '0-10' THEN 1
                    WHEN '11-20' THEN 2
                    WHEN '21-30' THEN 3
                    WHEN '31-50' THEN 4
                    WHEN '51-100' THEN 5
                    ELSE 6
                END
        """
        
        results = fetch_all(sql)
        return results or []
        
    except Exception as e:
        logger.error(f"자막 길이 분포 조회 중 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []
