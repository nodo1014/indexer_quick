"""
데이터베이스 접근 계층

데이터베이스 연결 및 기본 CRUD 작업을 처리하는 모듈입니다.
"""

import os
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import List, Dict, Any, Optional, Tuple, Union

from app.config import config


# 로깅 설정
class LogFilter(logging.Filter):
    """특정 유형의 로그만 필터링하는 클래스"""
    
    def __init__(self, allowed_levels=None):
        super().__init__()
        self.allowed_levels = allowed_levels or [logging.ERROR, logging.CRITICAL]
    
    def filter(self, record):
        # 지정된 로그 레벨만 허용
        return record.levelno in self.allowed_levels


def setup_logger():
    """로깅 설정"""
    logger = logging.getLogger("database")
    logger.setLevel(logging.INFO)  # 모든 로그 수집
    
    # 이미 핸들러가 설정되어 있으면 추가하지 않음
    if logger.hasHandlers():
        return logger
    
    # 파일 핸들러 설정 (크기 제한 및 백업 파일 설정)
    file_handler = RotatingFileHandler(
        "database_debug.log", 
        maxBytes=2 * 1024 * 1024,  # 2MB
        backupCount=3,
        encoding='utf-8'
    )
    
    # 디버그 로그는 별도 파일에 저장
    debug_handler = RotatingFileHandler(
        "database_verbose.log",
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=2,
        encoding='utf-8'
    )
    
    # 메인 로그 파일에는 ERROR 이상 로그만 저장
    file_handler.setLevel(logging.ERROR)
    file_handler.addFilter(LogFilter())
    
    # 디버그 로그 파일에는 모든 로그 저장
    debug_handler.setLevel(logging.DEBUG)
    
    # 포맷터 설정
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    debug_handler.setFormatter(formatter)
    
    # 핸들러 추가
    logger.addHandler(file_handler)
    logger.addHandler(debug_handler)
    
    return logger


# 로거 초기화
logger = setup_logger()


class Database:
    """데이터베이스 관리 클래스"""
    
    def __init__(self):
        """데이터베이스 관리 클래스 초기화"""
        self.init_db()
    
    def get_db_path(self) -> Path:
        """데이터베이스 경로 반환"""
        db_path = config.get('db_path', 'media_index.db')
        logger.debug(f"DB 경로 설정: {db_path}")
        
        # 절대 경로 반환
        return Path(db_path).absolute()
    
    def get_connection(self) -> sqlite3.Connection:
        """데이터베이스 연결 객체 반환"""
        # 매번 현재 db_path 확인
        db_path = self.get_db_path()
        
        # 디렉토리가 없으면 생성
        parent_dir = os.path.dirname(db_path)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)
        
        logger.debug(f"데이터베이스 연결: {db_path}")
        
        # 외래 키 제약 조건 활성화
        conn = sqlite3.connect(str(db_path))
        conn.execute("PRAGMA foreign_keys = ON")
        
        # Row를 dict 형태로 반환하도록 설정
        conn.row_factory = self._dict_factory
        
        return conn
    
    @staticmethod
    def _dict_factory(cursor: sqlite3.Cursor, row: tuple) -> Dict[str, Any]:
        """SQLite 쿼리 결과를 딕셔너리로 변환"""
        return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}
    
    def init_db(self) -> None:
        """데이터베이스 초기화 및 필요한 테이블 생성"""
        conn = self.get_connection()
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
        
        # subtitle_tags 테이블 생성 (유글리쉬 클론 태그 기능)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subtitle_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                media_path TEXT NOT NULL,
                start_time REAL NOT NULL,
                tag TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # subtitle_bookmarks 테이블 생성 (유글리쉬 클론 북마크 기능)
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
        
        # FTS 가상 테이블 생성 (전체 텍스트 검색용)
        # 테이블만 생성하고 나중에 rebuild_fts_index()로 데이터 채움
        cursor.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS subtitles_fts USING fts5(
                content,
                content='subtitles',
                content_rowid='id'
            )
        ''')
        
        conn.commit()
        conn.close()
        
        logger.debug("데이터베이스 초기화 완료")
    
    def reset_database(self) -> None:
        """데이터베이스를 완전히 초기화 (모든 데이터 삭제)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 기존 테이블 삭제
        cursor.execute("DROP TABLE IF EXISTS media_files")
        cursor.execute("DROP TABLE IF EXISTS subtitles")
        cursor.execute("DROP TABLE IF EXISTS subtitles_fts")
        
        conn.commit()
        conn.close()
        
        # 테이블 다시 생성
        self.init_db()
        logger.info("데이터베이스 초기화 (모든 데이터 삭제) 완료")
    
    def has_indexed_files(self) -> bool:
        """인덱싱된 파일이 있는지 확인"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='media_files'")
        table_exists = cursor.fetchone()['COUNT(*)'] > 0
        
        if not table_exists:
            conn.close()
            return False
        
        cursor.execute("SELECT COUNT(*) FROM media_files")
        count = cursor.fetchone()['COUNT(*)']
        conn.close()
        
        return count > 0
    
    def insert_media(self, path: str, has_subtitle: bool = False, 
                    size: int = 0, last_modified: Optional[str] = None) -> int:
        """
        미디어 파일 정보 저장
        
        Args:
            path: 미디어 파일 경로
            has_subtitle: 자막 존재 여부
            size: 파일 크기(바이트)
            last_modified: 마지막 수정 시간 (ISO 형식의 문자열)
            
        Returns:
            int: 삽입된 레코드의 ID
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 이미 있는지 확인
        cursor.execute('SELECT id FROM media_files WHERE path = ?', (path,))
        existing = cursor.fetchone()
        
        if existing:
            # 업데이트
            cursor.execute(
                'UPDATE media_files SET has_subtitle = ?, size = ?, last_modified = ? WHERE id = ?',
                (has_subtitle, size, last_modified or datetime.now().isoformat(), existing['id'])
            )
            media_id = existing['id']
        else:
            # 새로 삽입
            cursor.execute(
                'INSERT INTO media_files (path, has_subtitle, size, last_modified) VALUES (?, ?, ?, ?)',
                (path, has_subtitle, size, last_modified or datetime.now().isoformat())
            )
            media_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        return media_id
    
    def upsert_media(self, media_path: str) -> int:
        """
        미디어 파일 정보 갱신 또는 삽입 (indexer.py와 호환성을 위한 메소드)
        
        Args:
            media_path: 미디어 파일 경로
            
        Returns:
            int: 미디어 파일의 ID
        """
        # 자막 파일 확장자를 config에서 가져오기
        subtitle_extension = config.get('subtitle_extension', '.srt').lower()
        
        # 자막 파일 경로 확인
        subtitle_path = os.path.splitext(media_path)[0] + subtitle_extension
        has_subtitle = os.path.exists(subtitle_path)
        
        # 파일 크기 및 수정 시간
        try:
            file_stat = os.stat(media_path)
            file_size = file_stat.st_size
            file_mtime = datetime.fromtimestamp(file_stat.st_mtime)
            last_modified = file_mtime.isoformat()
        except:
            file_size = 0
            last_modified = datetime.now().isoformat()
        
        # insert_media 메소드 활용
        return self.insert_media(media_path, has_subtitle, file_size, last_modified)
    
    def insert_subtitle(self, media_id: int, start_ms: int, end_ms: int, 
                       start_text: str, end_text: str, content: str, 
                       lang: str = 'en') -> Optional[int]:
        """
        자막 정보 저장
        FTS 인덱스는 별도로 업데이트하지 않고, rebuild_fts_index() 메소드로 일괄 처리합니다.
        
        Args:
            media_id: 미디어 파일 ID
            start_ms: 시작 시간 (밀리초)
            end_ms: 종료 시간 (밀리초)
            start_text: 시작 시간 텍스트 (HH:MM:SS,mmm)
            end_text: 종료 시간 텍스트 (HH:MM:SS,mmm)
            content: 자막 내용
            lang: 언어 코드 (기본값: 'en')
            
        Returns:
            Optional[int]: 삽입된 자막 ID 또는 실패 시 None
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 트랜잭션 시작
            conn.execute('BEGIN')
            
            # 자막 테이블에 데이터 삽입
            cursor.execute(
                '''INSERT INTO subtitles 
                   (media_id, start_time, end_time, start_time_text, end_time_text, content, lang)
                   VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (media_id, start_ms, end_ms, start_text, end_text, content, lang)
            )
            subtitle_id = cursor.lastrowid
            
            logger.debug(f"자막 삽입 성공: ID={subtitle_id}, 미디어ID={media_id}, 내용={content[:30]}...")
            
            # 미디어 파일의 has_subtitle 상태를 true로 업데이트
            cursor.execute('UPDATE media_files SET has_subtitle = 1 WHERE id = ?', (media_id,))
            
            # 트랜잭션 커밋
            conn.commit()
            return subtitle_id
            
        except Exception as e:
            # 에러 발생 시 롤백
            conn.rollback()
            logger.error(f"자막 삽입 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
            
        finally:
            conn.close()
    
    def clear_subtitles_for_media(self, media_id: int) -> bool:
        """
        특정 미디어의 모든 자막 삭제
        
        Args:
            media_id: 미디어 파일 ID
            
        Returns:
            bool: 성공 여부
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 트랜잭션 시작
            conn.execute('BEGIN')
            
            # FTS 테이블에서도 해당 자막들 삭제
            cursor.execute('''
                DELETE FROM subtitles_fts WHERE rowid IN (
                    SELECT id FROM subtitles WHERE media_id = ?
                )
            ''', (media_id,))
            
            # 자막 테이블에서 삭제
            cursor.execute('''
                DELETE FROM subtitles WHERE media_id = ?
            ''', (media_id,))
            
            # 미디어 파일 has_subtitle 상태 업데이트
            cursor.execute('''
                UPDATE media_files SET has_subtitle = 0 WHERE id = ?
            ''', (media_id,))
            
            conn.commit()
            logger.debug(f"미디어 ID {media_id}의 자막 삭제 성공")
            return True
            
        except Exception as e:
            conn.rollback()
            logger.error(f"자막 삭제 중 오류 발생: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
            
        finally:
            conn.close()
    
    def search_subtitles(self, query: str, 
                        lang: Optional[str] = None, 
                        start_time: Optional[str] = None, 
                        end_time: Optional[str] = None,
                        page: int = 1, 
                        per_page: int = 50) -> List[Dict[str, Any]]:
        """
        자막 내용 검색 (LIKE 쿼리 사용)
        
        Args:
            query: 검색어
            lang: 언어 필터
            start_time: 시작 시간 필터 (HH:MM:SS)
            end_time: 종료 시간 필터 (HH:MM:SS)
            page: 페이지 번호 (1부터 시작)
            per_page: 페이지당 결과 수
            
        Returns:
            List[Dict[str, Any]]: 검색 결과 목록
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 페이지네이션 처리
            offset = (page - 1) * per_page
            limit = per_page
            
            # 쿼리 파라미터
            params = []
            
            # 기본 쿼리 구성 (FTS 대신 LIKE 사용)
            base_query = """
                SELECT s.id, s.media_id, m.path AS media_path, 
                       s.start_time_text, s.end_time_text, s.content,
                       s.start_time, s.end_time, s.lang
                FROM subtitles AS s
                JOIN media_files AS m ON s.media_id = m.id
                WHERE s.content LIKE ?
            """
            # LIKE 검색을 위한 와일드카드 추가
            params.append(f"%{query}%")
            
            # 필터 조건 추가
            if lang:
                base_query += " AND s.lang = ?"
                params.append(lang)
                
            if start_time:
                # HH:MM:SS 형식을 밀리초로 변환
                start_parts = start_time.split(":")
                if len(start_parts) == 3:
                    h, m, s = map(float, start_parts)
                    start_ms = int((h * 3600 + m * 60 + s) * 1000)
                    base_query += " AND s.start_time >= ?"
                    params.append(start_ms)
            
            if end_time:
                # HH:MM:SS 형식을 밀리초로 변환
                end_parts = end_time.split(":")
                if len(end_parts) == 3:
                    h, m, s = map(float, end_parts)
                    end_ms = int((h * 3600 + m * 60 + s) * 1000)
                    base_query += " AND s.end_time <= ?"
                    params.append(end_ms)
                    
            # 정렬 및 페이지네이션 (rank 제거)
            base_query += " ORDER BY s.media_id, s.start_time LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            # 쿼리 실행
            cursor.execute(base_query, params)
            results = cursor.fetchall()
            
            # 경로 관리가 상대 경로인 경우 절대 경로로 변환해서 반환
            if config.should_store_relative_paths():
                for result in results:
                    # 원본 경로 보존 (참조용)
                    result['original_path'] = result['media_path']
                    # 절대 경로로 변환
                    result['media_path'] = config.get_absolute_media_path(result['media_path'])
            
            return results
            
        except Exception as e:
            logger.error(f"자막 검색 중 오류 발생: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
            
        finally:
            conn.close()
            
    def estimate_total_count(self, query: str, 
                           lang: Optional[str] = None, 
                           start_time: Optional[str] = None,
                           end_time: Optional[str] = None) -> int:
        """
        검색 조건에 맞는 총 결과 수 추정 (LIKE 쿼리 사용)
        
        Args:
            query: 검색어
            lang: 언어 필터
            start_time: 시작 시간 필터 (HH:MM:SS)
            end_time: 종료 시간 필터 (HH:MM:SS)
            
        Returns:
            int: 검색 조건에 맞는 총 결과 수
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 기본 쿼리 (FTS 대신 LIKE 사용)
            count_sql = """
                SELECT COUNT(*) as total
                FROM subtitles s
                JOIN media_files m ON s.media_id = m.id
                WHERE s.content LIKE ?
            """
            
            # LIKE 검색을 위한 와일드카드 추가
            params = [f"%{query}%"]
            
            # 언어 필터 추가
            if lang:
                count_sql += " AND s.lang = ?"
                params.append(lang)
            
            # 시간대 필터 추가
            if start_time:
                # HH:MM:SS 형식을 밀리초로 변환
                start_parts = start_time.split(':')
                if len(start_parts) == 3:
                    h, m, s = map(float, start_parts)
                    start_ms = int((h * 3600 + m * 60 + s) * 1000)
                    count_sql += " AND s.start_time >= ?"
                    params.append(start_ms)
            
            if end_time:
                # HH:MM:SS 형식을 밀리초로 변환
                end_parts = end_time.split(':')
                if len(end_parts) == 3:
                    h, m, s = map(float, end_parts)
                    end_ms = int((h * 3600 + m * 60 + s) * 1000)
                    count_sql += " AND s.end_time <= ?"
                    params.append(end_ms)
            
            cursor.execute(count_sql, params)
            result = cursor.fetchone()
            conn.close()
            
            # 총 개수 반환
            return result['total'] if result else 0
            
        except Exception as e:
            # 오류 발생 시 0 반환
            logger.error(f"검색 결과 수 계산 중 오류 발생: {e}")
            return 0
    
    def get_all_stats(self) -> Dict[str, Any]:
        """
        모든 통계 정보를 반환
        
        Returns:
            Dict[str, Any]: 통계 정보
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 테이블이 존재하는지 확인
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='media_files'")
            table_exists = cursor.fetchone()['COUNT(*)'] > 0
            
            if not table_exists:
                return {
                    "media_count": 0,
                    "subtitle_count": 0,
                    "subtitles_ratio": {
                        "percentage": 0,
                        "has_subtitles": 0,
                        "total": 0
                    },
                    "language_stats": []
                }
            
            # 미디어 파일 수
            cursor.execute("SELECT COUNT(*) FROM media_files")
            media_count = cursor.fetchone()['COUNT(*)']
            
            # 자막 수
            cursor.execute("SELECT COUNT(*) FROM subtitles")
            subtitle_count = cursor.fetchone()['COUNT(*)']
            
            # 자막이 있는 미디어 파일 수
            cursor.execute("SELECT COUNT(*) FROM media_files WHERE has_subtitle=1")
            has_subtitle_count = cursor.fetchone()['COUNT(*)']
            
            # 자막 비율
            subtitle_ratio = {
                "percentage": round((has_subtitle_count / media_count * 100) if media_count > 0 else 0, 1),
                "has_subtitles": has_subtitle_count,
                "total": media_count
            }
            
            # 언어별 통계
            cursor.execute("SELECT lang, COUNT(*) as count FROM subtitles GROUP BY lang ORDER BY COUNT(*) DESC")
            language_stats = cursor.fetchall()
            
            return {
                "media_count": media_count,
                "subtitle_count": subtitle_count,
                "subtitles_ratio": subtitle_ratio,
                "language_stats": language_stats
            }
        except Exception as e:
            logger.error(f"통계 정보 조회 중 오류 발생: {str(e)}")
            return {
                "media_count": 0,
                "subtitle_count": 0,
                "subtitles_ratio": {
                    "percentage": 0,
                    "has_subtitles": 0,
                    "total": 0
                },
                "language_stats": [],
                "error": str(e)
            }
        finally:
            conn.close()
    
    def get_subtitle_length_distribution(self) -> List[Tuple[str, int]]:
        """
        자막 길이 분포를 반환
        
        Returns:
            List[Tuple[str, int]]: 길이 범위별 자막 수
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 자막 길이별 분포
            sql = """
            SELECT 
                CASE 
                    WHEN length(content) <= 20 THEN '~20'
                    WHEN length(content) <= 50 THEN '21~50'
                    WHEN length(content) <= 100 THEN '51~100'
                    WHEN length(content) <= 200 THEN '101~200'
                    ELSE '201~'
                END as length_range,
                COUNT(*) as count
            FROM subtitles
            GROUP BY length_range
            ORDER BY 
                CASE length_range
                    WHEN '~20' THEN 1
                    WHEN '21~50' THEN 2
                    WHEN '51~100' THEN 3
                    WHEN '101~200' THEN 4
                    ELSE 5
                END
            """
            cursor.execute(sql)
            results = [(row['length_range'], row['count']) for row in cursor.fetchall()]
            
            return results
        except Exception as e:
            logger.error(f"자막 길이 분포 조회 중 오류 발생: {str(e)}")
            return []
        finally:
            conn.close()
    
    def get_daily_indexing_stats(self, days: int = 7) -> List[Tuple[str, int]]:
        """
        일일 인덱싱 통계를 반환
        
        Args:
            days: 조회할 일수
            
        Returns:
            List[Tuple[str, int]]: 날짜별 인덱싱된 파일 수
        """
        # 실제 구현은 데이터베이스에 따라 다를 수 있으므로 예시만 반환
        from datetime import datetime, timedelta
        
        # 예시 데이터 생성
        stats = []
        today = datetime.now()
        
        for i in range(days):
            date = (today - timedelta(days=i)).strftime('%Y-%m-%d')
            count = 100 - i * 10  # 예시 데이터
            stats.append((date, max(0, count)))
        
        return list(reversed(stats))
    
    def get_media_info(self, media_id: int) -> Optional[Dict[str, Any]]:
        """
        미디어 파일 정보 조회
        
        Args:
            media_id: 미디어 파일 ID
            
        Returns:
            Optional[Dict[str, Any]]: 미디어 파일 정보
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, path, has_subtitle, size, last_modified
            FROM media_files WHERE id = ?
        ''', (media_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        return result
    
    def get_all_media(self, with_subtitles_only: bool = False, 
                     limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        모든 미디어 파일 정보 조회
        
        Args:
            with_subtitles_only: 자막이 있는 파일만 조회
            limit: 결과 제한 개수
            offset: 결과 시작 위치
            
        Returns:
            List[Dict[str, Any]]: 미디어 파일 정보 목록
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        sql = """
            SELECT id, path, has_subtitle, size, last_modified 
            FROM media_files
        """
        
        params = []
        
        if with_subtitles_only:
            sql += " WHERE has_subtitle = 1"
            
        sql += " ORDER BY last_modified DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(sql, params)
        results = cursor.fetchall()
            
        conn.close()
        return results
    
    def get_subtitles_for_media(self, media_id: int, 
                              limit: Optional[int] = None, 
                              offset: int = 0) -> List[Dict[str, Any]]:
        """
        특정 미디어의 자막 조회
        
        Args:
            media_id: 미디어 파일 ID
            limit: 결과 제한 개수
            offset: 결과 시작 위치
            
        Returns:
            List[Dict[str, Any]]: 자막 정보 목록
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        sql = """
            SELECT id, media_id, start_time, end_time, start_time_text, end_time_text, content, lang
            FROM subtitles
            WHERE media_id = ?
            ORDER BY start_time
        """
        
        params = [media_id]
        
        if limit:
            sql += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
        cursor.execute(sql, params)
        results = cursor.fetchall()
            
        conn.close()
        return results
    
    def rebuild_fts_index(self) -> bool:
        """
        FTS 인덱스 재구축
        전체 자막 데이터를 읽어와 FTS 인덱스를 한 번에 재구축합니다.
        
        Returns:
            bool: 성공 여부
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 트랜잭션 시작
            conn.execute('BEGIN')
            
            # FTS 테이블 초기화
            cursor.execute("DELETE FROM subtitles_fts")
            
            # 모든 자막 데이터를 읽어와 FTS 테이블에 삽입
            cursor.execute("""
                INSERT INTO subtitles_fts(rowid, content)
                SELECT id, content FROM subtitles
            """)
            
            # 트랜잭션 커밋
            conn.commit()
            logger.info(f"FTS 인덱스 재구축 완료")
            return True
            
        except Exception as e:
            conn.rollback()
            logger.error(f"FTS 인덱스 재구축 중 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
            
        finally:
            conn.close()
    
    # === 유글리쉬 클론 태그 관련 메서드 ===
    def add_tag(self, media_path: str, start_time: float, tag: str) -> bool:
        """자막에 태그 추가"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 이미 존재하는 태그인지 확인
            cursor.execute(
                "SELECT id FROM subtitle_tags WHERE media_path = ? AND start_time = ? AND tag = ?",
                (media_path, start_time, tag)
            )
            if cursor.fetchone():
                # 이미 존재하는 태그는 중복 추가하지 않음
                logger.debug(f"이미 존재하는 태그: {media_path}, {start_time}, {tag}")
                return True
                
            # 태그 추가
            cursor.execute(
                "INSERT INTO subtitle_tags (media_path, start_time, tag) VALUES (?, ?, ?)",
                (media_path, start_time, tag)
            )
            conn.commit()
            logger.debug(f"태그 추가 성공: {media_path}, {start_time}, {tag}")
            return True
            
        except Exception as e:
            conn.rollback()
            logger.error(f"태그 추가 실패: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
            
        finally:
            conn.close()
    
    def delete_tag(self, media_path: str, start_time: float, tag: str) -> bool:
        """자막에서 태그 삭제"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "DELETE FROM subtitle_tags WHERE media_path = ? AND start_time = ? AND tag = ?",
                (media_path, start_time, tag)
            )
            conn.commit()
            
            if cursor.rowcount > 0:
                logger.debug(f"태그 삭제 성공: {media_path}, {start_time}, {tag}")
                return True
            else:
                logger.debug(f"삭제할 태그 없음: {media_path}, {start_time}, {tag}")
                return False
                
        except Exception as e:
            conn.rollback()
            logger.error(f"태그 삭제 실패: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
            
        finally:
            conn.close()
    
    def get_tags(self, media_path: str, start_time: float) -> List[str]:
        """특정 자막의 모든 태그 조회"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT tag FROM subtitle_tags WHERE media_path = ? AND start_time = ? ORDER BY tag",
                (media_path, start_time)
            )
            
            return [row['tag'] for row in cursor.fetchall()]
            
        except Exception as e:
            logger.error(f"태그 조회 실패: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
            
        finally:
            conn.close()
    
    # === 유글리쉬 클론 북마크 관련 메서드 ===
    def toggle_bookmark(self, media_path: str, start_time: float, onoff: bool, user_id: str = 'default') -> bool:
        """자막 북마크 추가 또는 삭제"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            if onoff:
                # 북마크 추가 (이미 있으면 무시)
                cursor.execute(
                    """INSERT OR IGNORE INTO subtitle_bookmarks
                       (media_path, start_time, user_id) VALUES (?, ?, ?)""",
                    (media_path, start_time, user_id)
                )
            else:
                # 북마크 삭제
                cursor.execute(
                    "DELETE FROM subtitle_bookmarks WHERE media_path = ? AND start_time = ? AND user_id = ?",
                    (media_path, start_time, user_id)
                )
                
            conn.commit()
            logger.debug(f"북마크 {'추가' if onoff else '삭제'} 성공: {media_path}, {start_time}")
            return True
            
        except Exception as e:
            conn.rollback()
            logger.error(f"북마크 {'추가' if onoff else '삭제'} 실패: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
            
        finally:
            conn.close()
    
    def get_bookmarks(self, user_id: str = 'default') -> List[str]:
        """사용자의 모든 북마크 조회"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT media_path, start_time FROM subtitle_bookmarks WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,)
            )
            
            # "media_path|start_time" 형식으로 반환 (프론트엔드와 일치)
            return [f"{row['media_path']}|{row['start_time']}" for row in cursor.fetchall()]
            
        except Exception as e:
            logger.error(f"북마크 조회 실패: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
            
        finally:
            conn.close()


# 기본 데이터베이스 인스턴스
db = Database()