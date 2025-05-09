"""
자막 삽입 및 FTS 동기화 모듈
"""

import logging
from typing import List, Dict, Any, Optional, Tuple, Union

from app.utils.logging import setup_module_logger
from app.config import config
from app.database.connection import get_connection, execute_query, fetch_one, fetch_all, connection_context

# 로거 초기화
logger = setup_module_logger("database.subtitles.insert")

def insert_subtitle(media_id: int, start_ms: int, end_ms: int, 
                   content: str, lang: str = 'en', 
                   start_text: str = None, end_text: str = None,
                   external_conn=None) -> Optional[int]:
    """
    자막 정보 삽입
    
    Args:
        media_id: 미디어 ID
        start_ms: 시작 시간 (밀리초)
        end_ms: 종료 시간 (밀리초)
        content: 자막 내용
        lang: 언어 코드
        start_text: 시작 시간 텍스트 표현
        end_text: 종료 시간 텍스트 표현
        external_conn: 외부에서 전달된 데이터베이스 연결 (있으면 이 연결 사용, 없으면 새로 생성)
        
    Returns:
        Optional[int]: 삽입된 자막 ID 또는 None (실패 시)
    """
    conn = external_conn
    conn_created = False
    
    try:
        # 외부에서 연결을 전달받지 않은 경우 새로 생성
        if conn is None:
            conn = get_connection()
            conn_created = True
            
        cursor = conn.cursor()
        
        # 자막 삽입 (실제 DB 컬럼명에 맞게 수정)
        cursor.execute('''
        INSERT INTO subtitles (media_id, start_time, end_time, content, lang, start_time_text, end_time_text)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (media_id, start_ms, end_ms, content, lang, start_text or '', end_text or ''))
        
        # 삽입된 자막 ID 가져오기
        subtitle_id = cursor.lastrowid
        
        # FTS 인덱스에 추가 - 직접 삽입하지 않고 add_subtitle_to_fts 함수 호출
        try:
            from app.database.subtitles.fts import add_subtitle_to_fts
            add_subtitle_to_fts(subtitle_id, content, conn)
        except Exception as fts_error:
            logger.warning(f"FTS 인덱스 추가 중 오류 발생 (자막은 정상적으로 삽입됨): {fts_error}")
            # FTS 오류가 발생해도 자막 삽입은 유지
        
        # 미디어 파일 has_subtitle 상태 업데이트
        cursor.execute('''
        UPDATE media_files SET has_subtitle = 1
        WHERE id = ?
        ''', (media_id,))
        
        # 외부에서 연결을 전달받은 경우 커밋은 하지 않음 (외부에서 관리)
        if conn_created:
            conn.commit()
            
        return subtitle_id
        
    except Exception as e:
        # 외부에서 연결을 전달받은 경우 롤백은 하지 않음 (외부에서 관리)
        if conn_created and conn:
            conn.rollback()
        logger.error(f"자막 삽입 중 오류: {str(e)} - {content[:20]}...")
        import traceback
        logger.error(traceback.format_exc())
        return None
        
    finally:
        # 외부에서 연결을 전달받은 경우 연결을 닫지 않음 (외부에서 관리)
        if conn_created and conn:
            conn.close()
