"""
미디어 정리 관련 모듈
"""

import logging
import os
from typing import List, Dict, Any, Optional, Tuple, Union

from app.utils.logging import setup_module_logger
from app.database.connection import get_connection, execute_query, fetch_one, fetch_all, connection_context

# 로거 초기화
logger = setup_module_logger("database.media.cleanup")

def remove_missing_media() -> int:
    """
    실제로 존재하지 않는 미디어 파일 정보 삭제
    
    Returns:
        int: 삭제된 미디어 파일 수
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 모든 미디어 파일 경로 가져오기
        cursor.execute("SELECT id, path FROM media_files")
        media_files = cursor.fetchall()
        
        deleted_count = 0
        for media in media_files:
            if not os.path.exists(media["path"]):
                # 자막 먼저 삭제 (외래 키 제약 조건)
                cursor.execute("DELETE FROM subtitles WHERE media_id = ?", (media["id"],))
                
                # 미디어 파일 정보 삭제
                cursor.execute("DELETE FROM media_files WHERE id = ?", (media["id"],))
                
                deleted_count += 1
                
        conn.commit()
        return deleted_count
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"존재하지 않는 미디어 파일 정리 중 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 0
        
    finally:
        if conn:
            conn.close()

def clear_all_media() -> bool:
    """
    모든 미디어 파일 정보 삭제 (주의: 모든 자막 정보도 함께 삭제됨)
    
    Returns:
        bool: 성공 여부
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 자막 먼저 삭제 (외래 키 제약 조건)
        cursor.execute("DELETE FROM subtitles")
        
        # 미디어 파일 정보 삭제
        cursor.execute("DELETE FROM media_files")
        
        conn.commit()
        return True
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"모든 미디어 파일 정보 삭제 중 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
        
    finally:
        if conn:
            conn.close()
