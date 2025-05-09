"""
데이터베이스 연결 관리 모듈

데이터베이스 연결 및 기본 CRUD 작업을 처리하는 모듈입니다.
간단한 직접 연결 방식으로 데이터베이스에 접근합니다.
"""

import os
import sqlite3
import logging
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Union

from app.config import config
from app.utils.logging import setup_module_logger

# 로거 초기화
logger = setup_module_logger("database.connection")

# 기본 설정
DEFAULT_TIMEOUT = 10


def dict_factory(cursor: sqlite3.Cursor, row: tuple) -> Dict[str, Any]:
    """SQLite 쿼리 결과를 딕셔너리로 변환"""
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

def get_db_path() -> Path:
    """데이터베이스 경로 반환"""
    db_path = config.get('db_path', 'media_index.db')
    logger.debug(f"DB 경로 설정: {db_path}")
    
    # 절대 경로 반환
    return Path(db_path).absolute()

def get_connection() -> sqlite3.Connection:
    """
    새로운 데이터베이스 연결 객체 반환

    Returns:
        sqlite3.Connection: 데이터베이스 연결 객체
    """
    db_path = get_db_path()

    # 디렉토리가 없으면 생성
    parent_dir = os.path.dirname(db_path)
    if parent_dir and not os.path.exists(parent_dir):
        os.makedirs(parent_dir, exist_ok=True)

    logger.debug(f"데이터베이스 연결 생성: {db_path}")

    try:
        conn = sqlite3.connect(
            str(db_path),
            timeout=DEFAULT_TIMEOUT,
            isolation_level=None,
            check_same_thread=False
        )
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = dict_factory

        # 성능 최적화 설정
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA cache_size = 10000")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA page_size = 4096")
        conn.execute(f"PRAGMA busy_timeout = {DEFAULT_TIMEOUT * 1000}")

        return conn
    except Exception as e:
        logger.error(f"데이터베이스 연결 생성 실패: {e}")
        raise

@contextmanager
def connection_context():
    """
    컨텍스트 매니저를 이용한 연결 관리
    
    사용법:
    ```python
    with connection_context() as conn:
        conn.execute(...)
    ```
    
    Returns:
        sqlite3.Connection: 데이터베이스 연결 객체
    """
    conn = None
    try:
        # 최대 3번 연결 시도
        retry_count = 0
        max_retries = 3
        last_error = None
        
        while retry_count < max_retries:
            try:
                conn = get_connection()
                yield conn
                return
            except sqlite3.OperationalError as e:
                last_error = e
                error_msg = str(e).lower()
                # 데이터베이스 잠금 또는 손상 오류인 경우 재시도
                if "locked" in error_msg or "malformed" in error_msg or "busy" in error_msg:
                    retry_count += 1
                    if retry_count < max_retries:
                        logger.warning(f"데이터베이스 연결 재시도 ({retry_count}/{max_retries}): {e}")
                        time.sleep(1.0)  # 잠시 대기 후 재시도
                    else:
                        logger.error(f"데이터베이스 연결 최대 재시도 횟수 초과: {e}")
                        raise
                else:
                    # 다른 종류의 오류는 즉시 예외 발생
                    logger.error(f"데이터베이스 연결 오류: {e}")
                    raise
            except Exception as e:
                logger.error(f"데이터베이스 연결 중 예상치 못한 오류: {e}")
                raise
        
        # 모든 재시도 실패 시
        if last_error:
            raise last_error
    finally:
        # 컨텍스트 종료 시 커밋이나 롤백 처리 및 연결 닫기
        if conn:
            try:
                # 트랜잭션 상태 확인 후 롤백
                conn.execute("ROLLBACK")
            except Exception as e:
                logger.debug(f"롤백 중 오류 (무시됨): {e}")
            try:
                conn.close()
            except Exception as e:
                logger.debug(f"연결 종료 중 오류 (무시됨): {e}")

def execute_query(query: str, params: tuple = (), commit: bool = False, timeout: int = None) -> Optional[sqlite3.Cursor]:
    """
    SQL 쿼리 실행
    
    Args:
        query: SQL 쿼리문
        params: 쿼리 파라미터
        commit: 트랜잭션 커밋 여부
        timeout: 쿼리 타임아웃 (초)
        
    Returns:
        Optional[sqlite3.Cursor]: cursor 객체 또는 None (오류 발생 시)
    """
    start_time = time.time()
    max_retries = 3
    retry_count = 0
    last_error = None
    
    while retry_count <= max_retries:
        try:
            conn = get_connection()
            
            # 타임아웃 설정
            if timeout:
                conn.execute(f"PRAGMA busy_timeout = {timeout * 1000}")
            else:
                # 기본 타임아웃 설정 (5초)
                conn.execute(f"PRAGMA busy_timeout = 5000")
            
            cursor = conn.cursor()
            cursor.execute(query, params)
            
            if commit:
                conn.execute("COMMIT")
            
            # 쿼리 시간 측정 (디버그 모드에서만)
            if logger.isEnabledFor(logging.DEBUG):
                elapsed = time.time() - start_time
                if elapsed > 0.5:  # 0.5초 이상 걸린 쿼리만 로깅
                    logger.debug(f"쿼리 실행 시간: {elapsed:.3f}초, 쿼리: {query[:100]}...")
            
            return cursor
            
        except sqlite3.OperationalError as e:
            last_error = e
            error_msg = str(e).lower()
            
            # 데이터베이스 잠금 또는 손상 오류인 경우 재시도
            if "locked" in error_msg or "malformed" in error_msg or "busy" in error_msg:
                retry_count += 1
                
                try:
                    # 트랜잭션 상태 확인 후 롤백
                    conn.execute("ROLLBACK")
                except Exception as rollback_error:
                    logger.debug(f"롤백 중 오류 (무시됨): {rollback_error}")
                
                if retry_count <= max_retries:
                    retry_delay = retry_count * 1.0  # 재시도마다 대기 시간 증가
                    logger.warning(f"쿼리 실행 재시도 ({retry_count}/{max_retries}): {e}, {retry_delay}초 후 재시도")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"쿼리 실행 최대 재시도 횟수 초과: {e}, 쿼리: {query[:100]}...")
                    return None
            else:
                # 다른 종류의 오류는 즉시 실패 처리
                logger.error(f"쿼리 실행 오류: {e}, 쿼리: {query[:100]}...")
                
                try:
                    conn.execute("ROLLBACK")
                except Exception as rollback_error:
                    logger.debug(f"롤백 중 오류 (무시됨): {rollback_error}")
                    
                return None
                
        except Exception as e:
            last_error = e
            logger.error(f"쿼리 실행 중 예상치 못한 오류: {e}, 쿼리: {query[:100]}...")
            
            try:
                conn.execute("ROLLBACK")
            except Exception as rollback_error:
                logger.debug(f"롤백 중 오류 (무시됨): {rollback_error}")
                
            return None
    
    # 모든 재시도 실패 시
    return None

def execute_transaction(queries: List[Tuple[str, tuple]]) -> bool:
    """
    여러 SQL 쿼리를 트랜잭션으로 실행
    
    Args:
        queries: (쿼리문, 파라미터) 튜플의 리스트
        
    Returns:
        bool: 성공 여부
    """
    start_time = time.time()
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        conn.execute("BEGIN")
        
        for query, params in queries:
            cursor.execute(query, params)
            
        conn.execute("COMMIT")
        
        # 쿼리 시간 측정 (디버그 모드에서만)
        if logger.isEnabledFor(logging.DEBUG):
            elapsed = time.time() - start_time
            if elapsed > 0.5:  # 0.5초 이상 걸린 트랜잭션만 로깅
                query_count = len(queries)
                logger.debug(f"트랜잭션 실행 시간: {elapsed:.3f}초, {query_count}개 쿼리")
        
        return True
    except Exception as e:
        try:
            conn.execute("ROLLBACK")
        except:
            pass
        logger.error(f"트랜잭션 실행 오류: {e}")
        return False

def fetch_one(query: str, params: tuple = (), timeout: int = None) -> Optional[Dict[str, Any]]:
    """
    단일 결과 조회
    
    Args:
        query: SQL 쿼리문
        params: 쿼리 파라미터
        timeout: 쿼리 타임아웃 (초)
        
    Returns:
        Optional[Dict[str, Any]]: 조회 결과 또는 None
    """
    start_time = time.time()
    
    try:
        conn = get_connection()
        
        # 타임아웃 설정
        if timeout:
            conn.execute(f"PRAGMA busy_timeout = {timeout * 1000}")
            
        cursor = conn.cursor()
        cursor.execute(query, params)
        result = cursor.fetchone()
        
        # 쿼리 시간 측정 (디버그 모드에서만)
        if logger.isEnabledFor(logging.DEBUG):
            elapsed = time.time() - start_time
            if elapsed > 0.5:  # 0.5초 이상 걸린 쿼리만 로깅
                logger.debug(f"쿼리 실행 시간: {elapsed:.3f}초, 쿼리: {query[:100]}...")
        
        return result
    except Exception as e:
        logger.error(f"데이터 조회 오류: {e}, 쿼리: {query[:100]}...")
        return None

def fetch_all(query: str, params: tuple = (), timeout: int = None) -> list:
    """
    여러 결과 조회
    
    Args:
        query: SQL 쿼리문
        params: 쿼리 파라미터
        timeout: 쿼리 타임아웃 (초)
        
    Returns:
        list: 조회 결과 목록 또는 빈 리스트
    """
    start_time = time.time()
    
    try:
        conn = get_connection()
        
        # 타임아웃 설정
        if timeout:
            conn.execute(f"PRAGMA busy_timeout = {timeout * 1000}")
            
        cursor = conn.cursor()
        cursor.execute(query, params)
        result = cursor.fetchall()
        
        # 쿼리 시간 측정 (디버그 모드에서만)
        if logger.isEnabledFor(logging.DEBUG):
            elapsed = time.time() - start_time
            if elapsed > 0.5:  # 0.5초 이상 걸린 쿼리만 로깅
                logger.debug(f"쿼리 실행 시간: {elapsed:.3f}초, 결과 {len(result)}개, 쿼리: {query[:100]}...")
        
        return result
    except Exception as e:
        logger.error(f"데이터 조회 오류: {e}, 쿼리: {query[:100]}...")
        return []

def execute_with_retry(
    query: str, 
    params: tuple = (), 
    commit: bool = False,
    max_retries: int = 3, 
    retry_delay: float = 1.0
) -> Optional[sqlite3.Cursor]:
    """
    재시도 로직이 포함된 SQL 쿼리 실행
    
    Args:
        query: SQL 쿼리문
        params: 쿼리 파라미터
        commit: 트랜잭션 커밋 여부
        max_retries: 최대 재시도 횟수
        retry_delay: 재시도 간 대기 시간(초)
        
    Returns:
        Optional[sqlite3.Cursor]: cursor 객체 또는 None (모든 시도 실패 시)
    """
    attempt = 0
    while attempt < max_retries:
        attempt += 1
        try:
            result = execute_query(query, params, commit)
            if result is not None:
                return result
        except Exception as e:
            logger.warning(f"쿼리 실행 재시도 {attempt}/{max_retries}: {e}")
            
        # 마지막 시도가 아니면 대기
        if attempt < max_retries:
            time.sleep(retry_delay)
    
    logger.error(f"쿼리 실행 최대 재시도 횟수 초과: {query[:100]}...")
    return None

def backup_database(backup_path: Optional[str] = None) -> bool:
    """
    데이터베이스 백업
    
    Args:
        backup_path: 백업 파일 경로 (None이면 자동 생성)
        
    Returns:
        bool: 성공 여부
    """
    if not backup_path:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        db_path = get_db_path()
        backup_path = f"{db_path}.backup_{timestamp}"
    
    dest_conn = None
    start_time = time.time()
    
    try:
        conn = get_connection()
        dest_conn = sqlite3.connect(backup_path)
        
        # 백업 실행
        conn.execute("BEGIN IMMEDIATE")  # 백업 중 변경을 방지
        conn.backup(dest_conn)
        conn.rollback()  # 트랜잭션 종료
        
        # 백업 파일 최적화
        dest_conn.execute("VACUUM")
        dest_conn.execute("PRAGMA optimize")
        
        elapsed = time.time() - start_time
        logger.info(f"데이터베이스 백업 완료: {backup_path} ({elapsed:.1f}초)")
        return True
    except Exception as e:
        logger.error(f"데이터베이스 백업 실패: {e}")
        return False
    finally:
        if dest_conn:
            try:
                dest_conn.close()
            except:
                pass

def close_connection():
    """(더 이상 사용되지 않음)"""
    pass