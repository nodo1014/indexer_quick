"""
삭제 관련 처리 모듈
"""

import logging
from typing import List, Dict, Any, Optional, Tuple, Union

from app.utils.logging import setup_module_logger
from app.config import config
from app.database.connection import get_connection, execute_query, fetch_one, fetch_all, connection_context

# 로거 초기화
logger = setup_module_logger("database.subtitles.cleanup")

def clear_subtitles_for_media(media_id: int) -> bool:
    """
    특정 미디어의 모든 자막 삭제
    
    Args:
        media_id: 미디어 ID
        
    Returns:
        bool: 성공 여부
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # FTS 테이블에서 삭제
        cursor.execute('''
        DELETE FROM subtitles_fts
        WHERE rowid IN (SELECT id FROM subtitles WHERE media_id = ?)
        ''', (media_id,))
        
        # 자막 테이블에서 삭제
        cursor.execute('DELETE FROM subtitles WHERE media_id = ?', (media_id,))
        
        # 미디어 파일 has_subtitle 상태 업데이트
        cursor.execute('UPDATE media_files SET has_subtitle = 0 WHERE id = ?', (media_id,))
        
        conn.commit()
        logger.debug(f"미디어 ID {media_id}의 자막 삭제 성공")
        return True
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"자막 삭제 중 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
        
    finally:
        if conn:
            conn.close()

def remove_duplicate_subtitles() -> int:
    """
    중복된 자막 제거
    
    Returns:
        int: 제거된 자막 수
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 중복 자막 찾기 (같은 미디어, 같은 시작/종료 시간, 같은 내용)
        cursor.execute('''
        DELETE FROM subtitles
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM subtitles
            GROUP BY media_id, start_ms, end_ms, content
        )
        ''')
        
        removed_count = cursor.rowcount
        
        # FTS 인덱스 재구축
        if removed_count > 0:
            from app.database.subtitles.fts import rebuild_fts_index
            rebuild_fts_index(force=True)
        
        conn.commit()
        logger.info(f"중복 자막 {removed_count}개 제거 완료")
        return removed_count
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"중복 자막 제거 중 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 0
        
    finally:
        if conn:
            conn.close()

def cleanup_orphaned_subtitles() -> int:
    """
    미디어가 없는 고아 자막 제거
    
    Returns:
        int: 제거된 자막 수
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 미디어가 없는 자막 찾기
        cursor.execute('''
        DELETE FROM subtitles
        WHERE media_id NOT IN (
            SELECT id FROM media
        )
        ''')
        
        removed_count = cursor.rowcount
        
        # FTS 인덱스 재구축
        if removed_count > 0:
            from app.database.subtitles.fts import rebuild_fts_index
            rebuild_fts_index(force=True)
        
        conn.commit()
        logger.info(f"고아 자막 {removed_count}개 제거 완료")
        return removed_count
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"고아 자막 제거 중 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 0
        
    finally:
        if conn:
            conn.close()
