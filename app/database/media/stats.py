"""
미디어 통계 관련 모듈
"""

import logging
from typing import List, Dict, Any, Optional, Tuple, Union

from app.utils.logging import setup_module_logger
from app.database.connection import get_connection, execute_query, fetch_one, fetch_all, connection_context

# 로거 초기화
logger = setup_module_logger("database.media.stats")

def get_media_stats() -> Dict[str, Any]:
    """
    미디어 파일 통계 정보 조회
    
    Returns:
        Dict[str, Any]: 통계 정보
    """
    try:
        stats = {}
        
        # 전체 미디어 수
        total_count = fetch_one("SELECT COUNT(*) as count FROM media_files")
        stats["total"] = total_count["count"] if total_count else 0
        stats["total_count"] = stats["total"]  # 호환성을 위해 두 가지 키 모두 제공
        
        # 자막 있는 미디어 수
        with_subtitle = fetch_one("SELECT COUNT(*) as count FROM media_files WHERE has_subtitle = 1")
        stats["with_subtitle"] = with_subtitle["count"] if with_subtitle else 0
        
        # 자막 없는 미디어 수
        without_subtitle = fetch_one("SELECT COUNT(*) as count FROM media_files WHERE has_subtitle = 0")
        stats["without_subtitle"] = without_subtitle["count"] if without_subtitle else 0
        
        # 최근 추가된 미디어 수 - created_at 컴럼이 없으므로 고정값 사용
        stats["recent_24h"] = 0  # 현재 스키마에서는 추적 불가능
        
        # 파일 크기 통계
        size_stats = fetch_one("""
        SELECT 
            SUM(size) as total_size,
            AVG(size) as avg_size,
            MAX(size) as max_size,
            MIN(CASE WHEN size > 0 THEN size ELSE NULL END) as min_size
        FROM media_files
        """)
        
        if size_stats:
            stats["total_size"] = size_stats["total_size"] or 0
            stats["avg_size"] = size_stats["avg_size"] or 0
            stats["max_size"] = size_stats["max_size"] or 0
            stats["min_size"] = size_stats["min_size"] or 0
        else:
            stats["total_size"] = 0
            stats["avg_size"] = 0
            stats["max_size"] = 0
            stats["min_size"] = 0
            
        # 자막 커버리지 비율 계산
        if stats["total"] > 0:
            stats["subtitle_coverage_percent"] = round((stats["with_subtitle"] / stats["total"]) * 100, 2)
        else:
            stats["subtitle_coverage_percent"] = 0
        
        return stats
        
    except Exception as e:
        logger.error(f"미디어 통계 조회 중 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "total": 0,
            "total_count": 0,
            "with_subtitle": 0,
            "without_subtitle": 0,
            "recent_24h": 0,
            "total_size": 0,
            "avg_size": 0,
            "max_size": 0,
            "min_size": 0,
            "subtitle_coverage_percent": 0
        }
