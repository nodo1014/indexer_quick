"""
작업 재시도 정책 관리 모듈
"""

import logging
from typing import List, Dict, Any, Optional, Tuple, Union

from app.utils.logging import setup_module_logger
from app.database.connection import get_connection, execute_query, fetch_one, fetch_all, connection_context

# 로거 초기화
logger = setup_module_logger("database.jobs.retry_policy")

# 기본 최대 재시도 횟수
DEFAULT_MAX_RETRIES = 3

def should_retry_job(job_id: int, max_retries: int = DEFAULT_MAX_RETRIES) -> bool:
    """
    작업을 재시도해야 하는지 확인
    
    Args:
        job_id: 작업 ID
        max_retries: 최대 재시도 횟수
        
    Returns:
        bool: 재시도 여부
    """
    try:
        job = fetch_one(
            "SELECT retry_count FROM jobs WHERE id = ?", 
            (job_id,)
        )
        
        if not job:
            return False
            
        return job["retry_count"] < max_retries
        
    except Exception as e:
        logger.error(f"작업 재시도 확인 중 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def increment_retry_count(job_id: int) -> bool:
    """
    작업 재시도 횟수 증가
    
    Args:
        job_id: 작업 ID
        
    Returns:
        bool: 성공 여부
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        UPDATE jobs 
        SET retry_count = retry_count + 1, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        ''', (job_id,))
        
        conn.commit()
        return True
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"작업 재시도 횟수 증가 중 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
        
    finally:
        if conn:
            conn.close()

def reset_retry_count(job_id: int) -> bool:
    """
    작업 재시도 횟수 초기화
    
    Args:
        job_id: 작업 ID
        
    Returns:
        bool: 성공 여부
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        UPDATE jobs 
        SET retry_count = 0, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        ''', (job_id,))
        
        conn.commit()
        return True
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"작업 재시도 횟수 초기화 중 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
        
    finally:
        if conn:
            conn.close()

def get_failed_jobs_for_retry(max_retries: int = DEFAULT_MAX_RETRIES) -> List[Dict[str, Any]]:
    """
    재시도 가능한 실패한 작업 목록 조회
    
    Args:
        max_retries: 최대 재시도 횟수
        
    Returns:
        List[Dict[str, Any]]: 작업 정보 목록
    """
    try:
        return fetch_all('''
        SELECT * FROM jobs 
        WHERE status = 'failed' AND retry_count < ?
        ORDER BY updated_at ASC
        ''', (max_retries,))
        
    except Exception as e:
        logger.error(f"재시도 가능한 실패 작업 조회 중 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []

def set_retry_delay(job_id: int, delay_seconds: int) -> bool:
    """
    작업 재시도 지연 시간 설정
    
    Args:
        job_id: 작업 ID
        delay_seconds: 지연 시간 (초)
        
    Returns:
        bool: 성공 여부
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        UPDATE jobs 
        SET retry_after = datetime('now', '+' || ? || ' seconds'), 
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        ''', (delay_seconds, job_id))
        
        conn.commit()
        return True
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"작업 재시도 지연 시간 설정 중 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
        
    finally:
        if conn:
            conn.close()

def get_jobs_ready_for_retry() -> List[Dict[str, Any]]:
    """
    재시도 준비된 작업 목록 조회
    
    Returns:
        List[Dict[str, Any]]: 작업 정보 목록
    """
    try:
        return fetch_all('''
        SELECT * FROM jobs 
        WHERE status = 'failed' 
          AND retry_count < ? 
          AND (retry_after IS NULL OR retry_after <= datetime('now'))
        ORDER BY updated_at ASC
        ''', (DEFAULT_MAX_RETRIES,))
        
    except Exception as e:
        logger.error(f"재시도 준비된 작업 조회 중 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []
