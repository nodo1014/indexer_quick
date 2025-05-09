"""
미디어 삽입 및 수정 모듈
"""

import logging
import os
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime

from app.utils.logging import setup_module_logger
from app.config import config
from app.database.connection import get_connection, execute_query, fetch_one, fetch_all, connection_context

# 로거 초기화
logger = setup_module_logger("database.media.insert")

def insert_media(path: str, has_subtitle: bool = False, 
               size: int = 0, last_modified: str = None) -> Optional[int]:
    """
    미디어 파일 정보 저장
    
    Args:
        path: 미디어 파일 경로
        has_subtitle: 자막 포함 여부
        size: 파일 크기 (바이트)
        last_modified: 마지막 수정 시간 (ISO 형식)
        
    Returns:
        Optional[int]: 삽입된 미디어 ID 또는 None (실패 시)
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 이미 존재하는지 확인
        cursor.execute("SELECT id FROM media_files WHERE path = ?", (path,))
        existing = cursor.fetchone()
        
        if existing:
            return existing["id"]
            
        # 마지막 수정 시간이 없으면 현재 시간 사용
        if not last_modified:
            last_modified = datetime.now().isoformat()
            
        # 미디어 파일 정보 삽입
        cursor.execute('''
        INSERT INTO media_files (path, has_subtitle, size, last_modified)
        VALUES (?, ?, ?, ?)
        ''', (path, has_subtitle, size, last_modified))
        
        # 삽입된 ID 반환
        media_id = cursor.lastrowid
        
        conn.commit()
        return media_id
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"미디어 정보 저장 중 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None
        
    finally:
        if conn:
            conn.close()

def upsert_media(media_path: str) -> int:
    """
    미디어 파일 정보 갱신 또는 삽입
    
    Args:
        media_path: 미디어 파일 경로
        
    Returns:
        int: 미디어 ID
    """
    try:
        # 파일 정보 가져오기
        if os.path.exists(media_path):
            size = os.path.getsize(media_path)
            last_modified = datetime.fromtimestamp(os.path.getmtime(media_path)).isoformat()
        else:
            size = 0
            last_modified = datetime.now().isoformat()
            
        # 이미 존재하는지 확인
        existing = fetch_one("SELECT id FROM media_files WHERE path = ?", (media_path,))
        
        if existing:
            # 업데이트
            execute_query('''
            UPDATE media_files 
            SET size = ?, last_modified = ?
            WHERE path = ?
            ''', (size, last_modified, media_path))
            
            return existing["id"]
        else:
            # 삽입
            return insert_media(media_path, False, size, last_modified)
            
    except Exception as e:
        logger.error(f"미디어 정보 갱신 중 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 0

def update_subtitle_status(media_id: int, has_subtitle: bool) -> bool:
    """
    미디어 파일의 자막 상태 업데이트
    
    Args:
        media_id: 미디어 ID
        has_subtitle: 자막 포함 여부
        
    Returns:
        bool: 성공 여부
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        UPDATE media_files 
        SET has_subtitle = ?
        WHERE id = ?
        ''', (has_subtitle, media_id))
        
        conn.commit()
        return True
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"자막 상태 업데이트 중 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
        
    finally:
        if conn:
            conn.close()

def delete_media(media_id: int) -> bool:
    """
    미디어 파일 정보 삭제
    
    Args:
        media_id: 미디어 ID
        
    Returns:
        bool: 성공 여부
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 자막 먼저 삭제 (외래 키 제약 조건)
        cursor.execute("DELETE FROM subtitles WHERE media_id = ?", (media_id,))
        
        # 미디어 파일 정보 삭제
        cursor.execute("DELETE FROM media_files WHERE id = ?", (media_id,))
        
        conn.commit()
        return True
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"미디어 정보 삭제 중 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
        
    finally:
        if conn:
            conn.close()
