#!/usr/bin/env python
"""
손상된 데이터베이스 복구 스크립트

데이터베이스가 손상되었을 때 기존 데이터베이스를 백업하고 새로 생성하는 스크립트입니다.
"""

import os
import shutil
import sqlite3
import logging
import json
import time
import sys
from datetime import datetime
from pathlib import Path


# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_config():
    """설정 파일에서 데이터베이스 경로를 로드"""
    config_path = "config.json"
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config
        except Exception as e:
            logger.error(f"설정 파일 로드 오류: {e}")
            
    return {"db_path": "media_index.db"}


def backup_database(db_path):
    """데이터베이스 백업"""
    if not os.path.exists(db_path):
        logger.warning(f"백업할 데이터베이스가 존재하지 않습니다: {db_path}")
        return None
        
    # 백업 파일명 생성 (원본 파일명 + 타임스탬프)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_path}.backup_{timestamp}"
    
    try:
        # 파일 복사
        shutil.copy2(db_path, backup_path)
        logger.info(f"데이터베이스 백업 생성: {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"데이터베이스 백업 실패: {e}")
        return None


def create_new_database(db_path):
    """새 데이터베이스 생성"""
    try:
        # 기존 파일이 있으면 삭제
        if os.path.exists(db_path):
            os.remove(db_path)
            
        # 새 연결 생성
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # media_files 테이블 생성
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS media_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL,
                has_subtitle BOOLEAN DEFAULT 0,
                size INTEGER DEFAULT 0,
                last_modified TEXT
            )
        ''')
        
        # subtitles 테이블 생성 (시간을 밀리초 정수로 저장)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subtitles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                media_id INTEGER NOT NULL,
                start_time INTEGER NOT NULL,
                end_time INTEGER NOT NULL,
                start_time_text TEXT NOT NULL,
                end_time_text TEXT NOT NULL,
                content TEXT NOT NULL,
                lang TEXT DEFAULT 'en',
                FOREIGN KEY (media_id) REFERENCES media_files (id) ON DELETE CASCADE
            )
        ''')
        
        # subtitle_tags 테이블 생성
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subtitle_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                media_path TEXT NOT NULL,
                start_time REAL NOT NULL,
                tag TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # subtitle_bookmarks 테이블 생성
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subtitle_bookmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                media_path TEXT NOT NULL,
                start_time REAL NOT NULL,
                user_id TEXT DEFAULT 'default',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(media_path, start_time, user_id)
            )
        ''')
        
        # 인덱스 생성
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_media_path ON media_files (path)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_subtitles_media_id ON subtitles (media_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_subtitles_start_time ON subtitles (start_time)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tags_media_path ON subtitle_tags (media_path)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tags_start_time ON subtitle_tags (start_time)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_bookmarks_media_path ON subtitle_bookmarks (media_path)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_bookmarks_start_time ON subtitle_bookmarks (start_time)')
        
        # FTS 가상 테이블 생성
        cursor.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS subtitles_fts USING fts5(
                content,
                content='subtitles',
                content_rowid='id'
            )
        ''')
        
        conn.commit()
        conn.close()
        
        logger.info(f"새 데이터베이스 생성 완료: {db_path}")
        return True
    except Exception as e:
        logger.error(f"새 데이터베이스 생성 실패: {e}")
        return False


def is_database_corrupted(db_path):
    """데이터베이스 손상 여부 확인"""
    if not os.path.exists(db_path):
        return False
        
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 간단한 쿼리 실행
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()
        
        conn.close()
        
        # 결과가 'ok'가 아니면 손상된 것
        return result[0] != 'ok'
    except Exception:
        # 예외가 발생하면 손상된 것으로 간주
        return True


def main():
    """메인 함수"""
    # 명령행 인자 처리
    force_rebuild = False
    if len(sys.argv) > 1 and sys.argv[1] == '--force':
        force_rebuild = True
        logger.info("강제 재구축 모드 활성화")
    
    # 설정 로드
    config = get_config()
    db_path = config.get("db_path", "media_index.db")
    
    logger.info(f"데이터베이스 경로: {db_path}")
    
    # 손상 여부 확인 또는 강제 재구축
    if force_rebuild or is_database_corrupted(db_path):
        reason = "손상" if is_database_corrupted(db_path) else "강제 재구축 요청"
        logger.warning(f"데이터베이스 {reason}. 복구를 시작합니다.")
        
        # 백업 생성
        backup_path = backup_database(db_path)
        if not backup_path:
            logger.error("백업 생성 실패. 복구를 중단합니다.")
            return False
            
        # 새 데이터베이스 생성
        if create_new_database(db_path):
            logger.info("데이터베이스 복구 완료. 이제 데이터를 다시 인덱싱해야 합니다.")
            logger.info(f"백업 파일: {backup_path}")
            return True
        else:
            logger.error("새 데이터베이스 생성 실패.")
            return False
    else:
        logger.info("데이터베이스가 정상입니다.")
        return True


if __name__ == "__main__":
    main() 