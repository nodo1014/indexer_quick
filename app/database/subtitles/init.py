"""
자막 데이터베이스 초기화 모듈
"""

import logging
from typing import List, Dict, Any, Optional, Tuple, Union

from app.utils.logging import setup_module_logger
from app.config import config
from app.database.connection import get_connection, execute_query, connection_context

# 로거 초기화
logger = setup_module_logger("database.subtitles.init")

def init_subtitle_db() -> None:
    """
    자막 관련 데이터베이스 테이블 초기화
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 테이블 존재 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='subtitles'")
        subtitles_exists = cursor.fetchone()
        
        # 자막 테이블 생성 (없는 경우에만)
        if not subtitles_exists:
            # 자막 테이블 생성
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS subtitles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                media_id INTEGER NOT NULL,
                start_ms INTEGER NOT NULL,
                end_ms INTEGER NOT NULL,
                start_text TEXT,
                end_text TEXT,
                content TEXT NOT NULL,
                lang TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (media_id) REFERENCES media(id) ON DELETE CASCADE
            )
            ''')
            conn.commit()
            
            # 인덱스 생성
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_subtitles_media_id ON subtitles(media_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_subtitles_lang ON subtitles(lang)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_subtitles_start_ms ON subtitles(start_ms)')
            conn.commit()
        
        # 자막 처리 로그 테이블 생성
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS subtitle_processing_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subtitle_path TEXT NOT NULL,
            process_type TEXT NOT NULL,
            status TEXT NOT NULL,
            message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        conn.commit()
        
        # FTS 테이블 존재 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='subtitles_fts'")
        fts_exists = cursor.fetchone()
        
        # FTS 테이블이 없는 경우에만 생성
        if not fts_exists:
            # FTS 테이블 생성
            cursor.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS subtitles_fts USING fts5(
                content,
                content='subtitles',
                content_rowid='id'
            )
            ''')
            conn.commit()
        
        # FTS 인덱스 상태 테이블 생성
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS fts_index_status (
            id INTEGER PRIMARY KEY,
            last_indexed_id INTEGER DEFAULT 0,
            last_indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_complete INTEGER DEFAULT 0
        )
        ''')
        conn.commit()
        
        # FTS 인덱스 상태 초기 데이터 삽입
        cursor.execute('''
        INSERT OR IGNORE INTO fts_index_status (id, last_indexed_id, is_complete)
        VALUES (1, 0, 0)
        ''')
        
        conn.commit()
        logger.info("FTS 테이블 생성 완료")
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"자막 데이터베이스 초기화 중 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
    finally:
        if conn:
            conn.close()
