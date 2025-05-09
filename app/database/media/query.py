"""
미디어 조회 관련 모듈
"""

import logging
from typing import List, Dict, Any, Optional, Tuple, Union

from app.utils.logging import setup_module_logger
from app.database.connection import get_connection, execute_query, fetch_one, fetch_all, connection_context

# 로거 초기화
logger = setup_module_logger("database.media.query")

def get_total_media_count() -> int:
    """
    전체 미디어 파일 수 조회
    
    Returns:
        int: 미디어 파일 수
    """
    try:
        result = fetch_one("SELECT COUNT(*) as count FROM media_files")
        return result["count"] if result else 0
    except Exception as e:
        logger.error(f"미디어 수 조회 중 오류 발생: {e}")
        return 0

def get_media_info(media_id: int) -> Optional[Dict[str, Any]]:
    """
    미디어 파일 정보 조회
    
    Args:
        media_id: 미디어 ID
        
    Returns:
        Optional[Dict[str, Any]]: 미디어 정보 또는 None (없는 경우)
    """
    try:
        return fetch_one("SELECT * FROM media_files WHERE id = ?", (media_id,))
    except Exception as e:
        logger.error(f"미디어 정보 조회 중 오류 발생: {e}")
        return None

def get_media_by_path(path: str) -> Optional[Dict[str, Any]]:
    """
    경로로 미디어 파일 정보 조회
    
    Args:
        path: 미디어 파일 경로
        
    Returns:
        Optional[Dict[str, Any]]: 미디어 정보 또는 None (없는 경우)
    """
    try:
        return fetch_one("SELECT * FROM media_files WHERE path = ?", (path,))
    except Exception as e:
        logger.error(f"경로로 미디어 정보 조회 중 오류 발생: {e}")
        return None

def get_all_media(with_subtitles_only: bool = False, 
                 limit: int = 1000, offset: int = 0) -> List[Dict[str, Any]]:
    """
    모든 미디어 파일 정보 조회
    
    Args:
        with_subtitles_only: 자막이 있는 미디어만 조회할지 여부
        limit: 최대 조회 수
        offset: 조회 시작 위치
        
    Returns:
        List[Dict[str, Any]]: 미디어 정보 목록
    """
    try:
        sql = "SELECT * FROM media_files"
        params = []
        
        if with_subtitles_only:
            sql += " WHERE has_subtitle = 1"
            
        sql += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        return fetch_all(sql, tuple(params))
    except Exception as e:
        logger.error(f"미디어 목록 조회 중 오류 발생: {e}")
        return []

def count_media(with_subtitles_only: bool = False) -> int:
    """
    미디어 파일 수 조회
    
    Args:
        with_subtitles_only: 자막이 있는 미디어만 조회할지 여부
        
    Returns:
        int: 미디어 파일 수
    """
    try:
        sql = "SELECT COUNT(*) as count FROM media_files"
        params = []
        
        if with_subtitles_only:
            sql += " WHERE has_subtitle = 1"
            
        result = fetch_one(sql, tuple(params))
        return result["count"] if result else 0
    except Exception as e:
        logger.error(f"미디어 수 조회 중 오류 발생: {e}")
        return 0

def get_indexed_media_paths() -> List[str]:
    """
    인덱싱된 모든 미디어 파일 경로 조회
    
    Returns:
        List[str]: 미디어 파일 경로 목록
    """
    try:
        results = fetch_all("SELECT path FROM media_files")
        return [item["path"] for item in results] if results else []
    except Exception as e:
        logger.error(f"인덱싱된 미디어 경로 조회 중 오류 발생: {e}")
        return []
