"""
작업 상태 관리 모듈
"""

import logging
import json
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime

from app.utils.logging import setup_module_logger
from app.database.connection import get_connection, execute_query, fetch_one, fetch_all, connection_context

# 로거 초기화
logger = setup_module_logger("database.jobs.status")

# 작업 상태 상수
JOB_STATUS_PENDING = "pending"
JOB_STATUS_RUNNING = "running"
JOB_STATUS_COMPLETED = "completed"
JOB_STATUS_FAILED = "failed"
JOB_STATUS_CANCELLED = "cancelled"

def create_job(job_type: str, target_id: Optional[int] = None, 
              params: Optional[Dict[str, Any]] = None) -> Optional[int]:
    """
    새 작업 생성
    
    Args:
        job_type: 작업 유형 (예: 'index_media', 'generate_subtitle', 등)
        target_id: 작업 대상 ID (예: 미디어 ID)
        params: 작업 매개변수
        
    Returns:
        Optional[int]: 생성된 작업 ID 또는 None (실패 시)
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 매개변수가 있으면 JSON으로 직렬화
        params_json = json.dumps(params) if params else None
        
        # 작업 생성
        cursor.execute('''
        INSERT INTO jobs (
            job_type, target_id, params, status, 
            progress, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''', (job_type, target_id, params_json, JOB_STATUS_PENDING, 0))
        
        # 생성된 작업 ID 반환
        job_id = cursor.lastrowid
        
        conn.commit()
        return job_id
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"작업 생성 중 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None
        
    finally:
        if conn:
            conn.close()

def update_job_status(job_id: int, status: str, 
                     progress: Optional[float] = None, 
                     result: Optional[Dict[str, Any]] = None,
                     error: Optional[str] = None) -> bool:
    """
    작업 상태 업데이트
    
    Args:
        job_id: 작업 ID
        status: 작업 상태
        progress: 작업 진행률 (0~100)
        result: 작업 결과
        error: 오류 메시지
        
    Returns:
        bool: 성공 여부
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 결과가 있으면 JSON으로 직렬화
        result_json = json.dumps(result) if result else None
        
        # SQL 쿼리 및 매개변수 구성
        sql = '''
        UPDATE jobs SET 
            status = ?,
            updated_at = CURRENT_TIMESTAMP
        '''
        params = [status]
        
        if progress is not None:
            sql += ", progress = ?"
            params.append(progress)
            
        if result_json is not None:
            sql += ", result = ?"
            params.append(result_json)
            
        if error is not None:
            sql += ", error = ?"
            params.append(error)
            
        sql += " WHERE id = ?"
        params.append(job_id)
        
        # 쿼리 실행
        cursor.execute(sql, tuple(params))
        
        conn.commit()
        return True
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"작업 상태 업데이트 중 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
        
    finally:
        if conn:
            conn.close()

def get_job_status(job_id: int) -> Optional[Dict[str, Any]]:
    """
    작업 상태 조회
    
    Args:
        job_id: 작업 ID
        
    Returns:
        Optional[Dict[str, Any]]: 작업 정보 또는 None (없는 경우)
    """
    try:
        job = fetch_one("SELECT * FROM jobs WHERE id = ?", (job_id,))
        
        if not job:
            return None
            
        # JSON 필드 역직렬화
        if job.get("params"):
            try:
                job["params"] = json.loads(job["params"])
            except:
                job["params"] = {}
                
        if job.get("result"):
            try:
                job["result"] = json.loads(job["result"])
            except:
                job["result"] = {}
                
        return job
        
    except Exception as e:
        logger.error(f"작업 상태 조회 중 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def get_all_jobs(job_type: Optional[str] = None, 
                status: Optional[str] = None,
                limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """
    작업 목록 조회
    
    Args:
        job_type: 작업 유형 필터 (선택 사항)
        status: 작업 상태 필터 (선택 사항)
        limit: 최대 조회 수
        offset: 조회 시작 위치
        
    Returns:
        List[Dict[str, Any]]: 작업 정보 목록
    """
    try:
        sql = "SELECT * FROM jobs"
        params = []
        
        # 필터 적용
        conditions = []
        if job_type:
            conditions.append("job_type = ?")
            params.append(job_type)
            
        if status:
            conditions.append("status = ?")
            params.append(status)
            
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
            
        # 정렬 및 페이지네이션
        sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        # 쿼리 실행
        jobs = fetch_all(sql, tuple(params))
        
        # JSON 필드 역직렬화
        for job in jobs:
            if job.get("params"):
                try:
                    job["params"] = json.loads(job["params"])
                except:
                    job["params"] = {}
                    
            if job.get("result"):
                try:
                    job["result"] = json.loads(job["result"])
                except:
                    job["result"] = {}
                    
        return jobs
        
    except Exception as e:
        logger.error(f"작업 목록 조회 중 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []

def complete_job(job_id: int, result: Optional[Dict[str, Any]] = None) -> bool:
    """
    작업 완료 처리
    
    Args:
        job_id: 작업 ID
        result: 작업 결과
        
    Returns:
        bool: 성공 여부
    """
    return update_job_status(
        job_id=job_id,
        status=JOB_STATUS_COMPLETED,
        progress=100,
        result=result
    )

def fail_job(job_id: int, error: str) -> bool:
    """
    작업 실패 처리
    
    Args:
        job_id: 작업 ID
        error: 오류 메시지
        
    Returns:
        bool: 성공 여부
    """
    return update_job_status(
        job_id=job_id,
        status=JOB_STATUS_FAILED,
        error=error
    )

def get_job_progress(job_id: int) -> Optional[float]:
    """
    작업 진행률 조회
    
    Args:
        job_id: 작업 ID
        
    Returns:
        Optional[float]: 작업 진행률 (0~100) 또는 None (없는 경우)
    """
    try:
        result = fetch_one(
            "SELECT progress FROM jobs WHERE id = ?", 
            (job_id,)
        )
        return result["progress"] if result else None
    except Exception as e:
        logger.error(f"작업 진행률 조회 중 오류 발생: {e}")
        return None
