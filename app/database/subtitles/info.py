"""
자막/미디어 정보 조회, 저장 모듈
"""

import os
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union

from app.utils.logging import setup_module_logger
from app.config import config
from app.database.connection import get_connection, execute_query, fetch_one, fetch_all, connection_context

# 로거 초기화
logger = setup_module_logger("database.subtitles.info")

def get_subtitle_info(subtitle_path: str) -> Optional[Dict[str, Any]]:
    """
    자막 파일 정보 조회
    
    Args:
        subtitle_path: 자막 파일 경로
        
    Returns:
        Optional[Dict[str, Any]]: 자막 정보 또는 None (조회 실패 시)
    """
    try:
        sql = "SELECT * FROM subtitle_files WHERE path = ?"
        params = (subtitle_path,)
        
        result = fetch_one(sql, params)
        return result
        
    except Exception as e:
        logger.error(f"자막 정보 조회 중 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def save_subtitle_info(subtitle_info: Dict[str, Any]) -> bool:
    """
    자막 파일 정보 저장
    
    Args:
        subtitle_info: 자막 정보 딕셔너리
        
    Returns:
        bool: 성공 여부
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 필수 필드 확인
        if 'path' not in subtitle_info:
            logger.error("자막 정보에 필수 필드(path)가 없습니다.")
            return False
        
        # 이미 존재하는지 확인
        existing = fetch_one("SELECT id FROM subtitle_files WHERE path = ?", (subtitle_info['path'],))
        
        if existing:
            # 업데이트
            fields = []
            params = []
            
            for key, value in subtitle_info.items():
                if key != 'path' and key != 'id':
                    fields.append(f"{key} = ?")
                    params.append(value)
            
            if not fields:
                return True  # 업데이트할 필드가 없음
                
            params.append(subtitle_info['path'])
            
            sql = f"UPDATE subtitle_files SET {', '.join(fields)} WHERE path = ?"
            cursor.execute(sql, tuple(params))
            
        else:
            # 삽입
            fields = []
            values = []
            placeholders = []
            
            for key, value in subtitle_info.items():
                fields.append(key)
                values.append(value)
                placeholders.append('?')
                
            sql = f"INSERT INTO subtitle_files ({', '.join(fields)}) VALUES ({', '.join(placeholders)})"
            cursor.execute(sql, tuple(values))
            
        conn.commit()
        return True
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"자막 정보 저장 중 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
        
    finally:
        if conn:
            conn.close()

def get_media_subtitle_info(media_path: str) -> Optional[Dict[str, Any]]:
    """
    미디어 파일의 자막 정보 조회
    
    Args:
        media_path: 미디어 파일 경로
        
    Returns:
        Optional[Dict[str, Any]]: 미디어 자막 정보 또는 None (조회 실패 시)
    """
    try:
        sql = "SELECT * FROM media WHERE path = ?"
        params = (media_path,)
        
        result = fetch_one(sql, params)
        return result
        
    except Exception as e:
        logger.error(f"미디어 자막 정보 조회 중 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def save_media_subtitle_info(media_info: Dict[str, Any]) -> bool:
    """
    미디어 파일의 자막 정보 저장
    
    Args:
        media_info: 미디어 정보 딕셔너리
        
    Returns:
        bool: 성공 여부
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 필수 필드 확인
        if 'path' not in media_info:
            logger.error("미디어 정보에 필수 필드(path)가 없습니다.")
            return False
        
        # 이미 존재하는지 확인
        existing = fetch_one("SELECT id FROM media WHERE path = ?", (media_info['path'],))
        
        if existing:
            # 업데이트
            fields = []
            params = []
            
            for key, value in media_info.items():
                if key != 'path' and key != 'id':
                    fields.append(f"{key} = ?")
                    params.append(value)
            
            if not fields:
                return True  # 업데이트할 필드가 없음
                
            params.append(media_info['path'])
            
            sql = f"UPDATE media SET {', '.join(fields)} WHERE path = ?"
            cursor.execute(sql, tuple(params))
            
        else:
            # 삽입
            fields = []
            values = []
            placeholders = []
            
            for key, value in media_info.items():
                fields.append(key)
                values.append(value)
                placeholders.append('?')
                
            sql = f"INSERT INTO media ({', '.join(fields)}) VALUES ({', '.join(placeholders)})"
            cursor.execute(sql, tuple(values))
            
        conn.commit()
        return True
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"미디어 자막 정보 저장 중 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
        
    finally:
        if conn:
            conn.close()

def log_processing(subtitle_path: str, process_type: str, status: str, 
                 message: str = None) -> bool:
    """
    자막 처리 로그 기록
    
    Args:
        subtitle_path: 자막 파일 경로
        process_type: 처리 유형 (예: 'parse', 'convert', 'index')
        status: 처리 상태 (예: 'success', 'error', 'warning')
        message: 추가 메시지
        
    Returns:
        bool: 성공 여부
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO subtitle_processing_log (subtitle_path, process_type, status, message)
        VALUES (?, ?, ?, ?)
        ''', (subtitle_path, process_type, status, message))
        
        conn.commit()
        return True
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"자막 처리 로그 기록 중 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
        
    finally:
        if conn:
            conn.close()

def get_unprocessed_subtitles(limit: int = 100) -> List[Dict[str, Any]]:
    """
    처리되지 않은 자막 목록 조회
    
    Args:
        limit: 최대 조회 개수
        
    Returns:
        List[Dict[str, Any]]: 처리되지 않은 자막 목록
    """
    try:
        sql = """
        SELECT sf.*
        FROM subtitle_files sf
        LEFT JOIN subtitle_processing_log spl ON sf.path = spl.subtitle_path
        WHERE spl.id IS NULL
        LIMIT ?
        """
        params = (limit,)
        
        results = fetch_all(sql, params)
        return results or []
        
    except Exception as e:
        logger.error(f"처리되지 않은 자막 목록 조회 중 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []

def get_broken_subtitles(limit: int = 100) -> List[Dict[str, Any]]:
    """
    처리 중 오류가 발생한 자막 목록 조회
    
    Args:
        limit: 최대 조회 개수
        
    Returns:
        List[Dict[str, Any]]: 오류 발생 자막 목록
    """
    try:
        sql = """
        SELECT sf.*, spl.message as error_message
        FROM subtitle_files sf
        JOIN subtitle_processing_log spl ON sf.path = spl.subtitle_path
        WHERE spl.status = 'error'
        GROUP BY sf.id
        LIMIT ?
        """
        params = (limit,)
        
        results = fetch_all(sql, params)
        return results or []
        
    except Exception as e:
        logger.error(f"오류 발생 자막 목록 조회 중 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []

def get_multi_subtitles(limit: int = 100) -> List[Dict[str, Any]]:
    """
    여러 언어가 포함된 자막 목록 조회
    
    Args:
        limit: 최대 조회 개수
        
    Returns:
        List[Dict[str, Any]]: 다중 언어 자막 목록
    """
    try:
        sql = """
        SELECT sf.*
        FROM subtitle_files sf
        WHERE sf.multi_language = 1
        LIMIT ?
        """
        params = (limit,)
        
        results = fetch_all(sql, params)
        return results or []
        
    except Exception as e:
        logger.error(f"다중 언어 자막 목록 조회 중 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []

def get_media_without_subtitles(limit: int = 100) -> List[Dict[str, Any]]:
    """
    자막이 없는 미디어 목록 조회
    
    Args:
        limit: 최대 조회 개수
        
    Returns:
        List[Dict[str, Any]]: 자막 없는 미디어 목록
    """
    try:
        sql = """
        SELECT m.*
        FROM media m
        WHERE m.has_subtitle = 0
        LIMIT ?
        """
        params = (limit,)
        
        results = fetch_all(sql, params)
        return results or []
        
    except Exception as e:
        logger.error(f"자막 없는 미디어 목록 조회 중 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []

def get_subtitles_for_media(media_id: int, limit: int = 1000, offset: int = 0) -> List[Dict[str, Any]]:
    """
    특정 미디어의 자막 목록 조회
    
    Args:
        media_id: 미디어 파일 ID
        limit: 최대 조회 개수
        offset: 조회 시작 위치
        
    Returns:
        List[Dict[str, Any]]: 자막 목록
    """
    try:
        # 실제 DB 컬럼명에 맞게 수정
        sql = "SELECT * FROM subtitles WHERE media_id = ? ORDER BY start_time LIMIT ? OFFSET ?"
        params = (media_id, limit, offset)
        
        results = fetch_all(sql, params)
        return results or []
        
    except Exception as e:
        logger.error(f"미디어 ID {media_id}의 자막 조회 중 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []
