"""
FTS 전용 (재인덱싱, 상태 확인) 모듈
"""

import logging
from typing import List, Dict, Any, Optional, Tuple, Union

from app.utils.logging import setup_module_logger
from app.config import config
from app.database.connection import get_connection, execute_query, fetch_one, fetch_all, connection_context

# 로거 초기화
logger = setup_module_logger("database.subtitles.fts")

def rebuild_fts_index(force: bool = False) -> bool:
    """
    FTS 인덱스 재구축
    
    Args:
        force: 강제 재구축 여부
        
    Returns:
        bool: 성공 여부
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # FTS 테이블 존재 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='subtitles_fts'")
        fts_exists = cursor.fetchone()
        
        if not fts_exists:
            logger.error("FTS 테이블이 존재하지 않습니다.")
            return False
            
        # 인덱스 상태 확인
        cursor.execute("SELECT * FROM fts_index_status WHERE id = 1")
        status = cursor.fetchone()
        
        if not status:
            cursor.execute('''
            INSERT INTO fts_index_status (id, last_indexed_id, is_complete)
            VALUES (1, 0, 0)
            ''')
            conn.commit()
            status = {"id": 1, "last_indexed_id": 0, "is_complete": 0}
            
        # 강제 재구축이 아니고 이미 완료된 경우 건너뛰기
        if not force and status["is_complete"] == 1:
            logger.info("FTS 인덱스가 이미 최신 상태입니다.")
            return True
            
        # 마지막으로 인덱싱된 ID 가져오기
        last_indexed_id = 0 if force else status["last_indexed_id"]
        
        # FTS 테이블 초기화 (강제 재구축인 경우)
        if force:
            cursor.execute("DELETE FROM subtitles_fts")
            
        # 배치 크기 설정
        batch_size = 1000
        
        # 인덱싱할 자막 가져오기
        cursor.execute(f'''
        SELECT id, content FROM subtitles
        WHERE id > ?
        ORDER BY id
        LIMIT {batch_size}
        ''', (last_indexed_id,))
        
        subtitles = cursor.fetchall()
        
        # 배치 처리
        while subtitles:
            # 트랜잭션 시작
            cursor.execute("BEGIN TRANSACTION")
            
            for subtitle in subtitles:
                subtitle_id = subtitle["id"]
                content = subtitle["content"]
                
                # FTS 인덱스에 추가
                cursor.execute('''
                INSERT OR REPLACE INTO subtitles_fts(rowid, content)
                VALUES (?, ?)
                ''', (subtitle_id, content))
                
                # 마지막 인덱싱 ID 업데이트
                last_indexed_id = subtitle_id
                
            # 상태 업데이트
            cursor.execute('''
            UPDATE fts_index_status
            SET last_indexed_id = ?, last_indexed_at = CURRENT_TIMESTAMP
            WHERE id = 1
            ''', (last_indexed_id,))
            
            # 트랜잭션 커밋
            cursor.execute("COMMIT")
            
            # 다음 배치 가져오기
            cursor.execute(f'''
            SELECT id, content FROM subtitles
            WHERE id > ?
            ORDER BY id
            LIMIT {batch_size}
            ''', (last_indexed_id,))
            
            subtitles = cursor.fetchall()
            
        # 인덱싱 완료 표시
        cursor.execute('''
        UPDATE fts_index_status
        SET is_complete = 1, last_indexed_at = CURRENT_TIMESTAMP
        WHERE id = 1
        ''')
        
        conn.commit()
        logger.info(f"FTS 인덱스 재구축 완료 (마지막 ID: {last_indexed_id})")
        return True
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"FTS 인덱스 재구축 중 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
        
    finally:
        if conn:
            conn.close()

def add_subtitle_to_fts(subtitle_id: int, content: str, external_conn=None) -> bool:
    """
    자막을 FTS 인덱스에 추가
    
    Args:
        subtitle_id: 자막 ID
        content: 자막 내용
        external_conn: 외부에서 전달된 데이터베이스 연결 (있으면 이 연결 사용, 없으면 새로 생성)
        
    Returns:
        bool: 성공 여부
    """
    conn = external_conn
    conn_created = False
    
    try:
        # 외부에서 연결을 전달받지 않은 경우 새로 생성
        if conn is None:
            conn = get_connection()
            conn_created = True
            
        cursor = conn.cursor()
        
        # FTS 테이블 존재 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='subtitles_fts'")
        fts_exists = cursor.fetchone()
        
        if not fts_exists:
            logger.error("FTS 테이블이 존재하지 않습니다.")
            return False
            
        # FTS 인덱스에 추가
        cursor.execute('''
        INSERT OR REPLACE INTO subtitles_fts(rowid, content)
        VALUES (?, ?)
        ''', (subtitle_id, content))
        
        # 인덱스 상태 업데이트
        cursor.execute('''
        UPDATE fts_index_status
        SET last_indexed_id = CASE WHEN last_indexed_id < ? THEN ? ELSE last_indexed_id END,
            last_indexed_at = CURRENT_TIMESTAMP
        WHERE id = 1
        ''', (subtitle_id, subtitle_id))
        
        # 외부에서 연결을 전달받은 경우 커밋은 하지 않음 (외부에서 관리)
        if conn_created:
            conn.commit()
            
        return True
        
    except Exception as e:
        # 외부에서 연결을 전달받은 경우 롤백은 하지 않음 (외부에서 관리)
        if conn_created and conn:
            conn.rollback()
        logger.error(f"자막 FTS 인덱스 추가 중 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
        
    finally:
        # 외부에서 연결을 전달받은 경우 연결을 닫지 않음 (외부에서 관리)
        if conn_created and conn:
            conn.close()
