import os
import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import List, Dict, Any, Optional, Tuple, Union

class LogFilter(logging.Filter):
    """특정 유형의 로그만 필터링하는 클래스"""
    
    def __init__(self, allowed_levels=None):
        super().__init__()
        self.allowed_levels = allowed_levels or [logging.ERROR, logging.CRITICAL]
    
    def filter(self, record):
        # 지정된 로그 레벨만 허용
        return record.levelno in self.allowed_levels

# 로깅 설정
logger = logging.getLogger("database")
logger.setLevel(logging.INFO)  # 모든 로그 수집

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

# 설정 파일 관리
def load_config():
    config_path = Path('config.json')
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    return {}

def save_config(config):
    config_path = Path('config.json')
    with open(config_path, 'w', encoding='utf-8') as file:
        json.dump(config, file, indent=4)

# 데이터베이스 초기화 및 연결 관리
class Database:
    def __init__(self):
        self.config = load_config()
        self.init_db()
    
    def get_db_path(self):
        # 항상 최신 설정을 로드하도록 수정
        config = load_config()
        
        db_path = config.get('db_path', 'media_index.db')
        logger.debug(f"DB 경로 설정: {db_path}")
        
        # 절대 경로 반환
        return Path(db_path).absolute()
    
    def init_db(self):
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
        cursor.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS subtitles_fts USING fts5(
                content,
                content='subtitles',
                content_rowid='id'
            )
        ''')
        
        # FTS 테이블이 비어있을 경우 초기화
        cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='subtitles_fts'")
        table_exists = cursor.fetchone()[0] > 0
        
        if table_exists:
            cursor.execute("SELECT count(*) FROM subtitles_fts LIMIT 1")
            is_empty = cursor.fetchone()[0] == 0
            if is_empty:
                cursor.execute("INSERT INTO subtitles_fts(subtitles_fts) VALUES('rebuild')")
        
        conn.commit()
        conn.close()
        
        logger.debug("데이터베이스 초기화 완료")
    
    def get_connection(self):
        """데이터베이스 연결 객체 반환"""
        # 매번 현재 db_path 확인
        self.db_path = self.get_db_path()
        
        # 디렉토리가 없으면 생성
        os.makedirs(os.path.dirname(self.db_path) if os.path.dirname(self.db_path) else '.', exist_ok=True)
        
        logger.debug(f"데이터베이스 연결: {self.db_path}")
        return sqlite3.connect(str(self.db_path))
    
    def insert_media(self, relative_path, has_subtitle, size=0, last_modified=None):
        """미디어 파일 정보 저장"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 이미 있는지 확인
        cursor.execute('SELECT id FROM media_files WHERE path = ?', (relative_path,))
        existing = cursor.fetchone()
        
        if existing:
            # 업데이트
            cursor.execute(
                'UPDATE media_files SET has_subtitle = ?, size = ?, last_modified = ? WHERE id = ?',
                (has_subtitle, size, last_modified or datetime.now().isoformat(), existing[0])
            )
            media_id = existing[0]
        else:
            # 새로 삽입
            cursor.execute(
                'INSERT INTO media_files (path, has_subtitle, size, last_modified) VALUES (?, ?, ?, ?)',
                (relative_path, has_subtitle, size, last_modified or datetime.now().isoformat())
            )
            media_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        return media_id
    
    def upsert_media(self, media_path):
        """미디어 파일 정보 갱신 또는 삽입 (indexer.py와 호환성을 위한 메소드)"""
        # 자막 파일 확장자를 config에서 가져오기
        subtitle_extension = self.config.get('subtitle_extension', '.srt').lower()
        
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
    
    def insert_subtitle(self, media_id, start_ms, end_ms, start_text, end_text, content, lang='en', verified=True):
        """자막 정보 저장"""
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
    
    def clear_subtitles_for_media(self, media_id):
        """특정 미디어의 모든 자막 삭제"""
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
    
    def search_subtitles(self, query, limit=100, offset=0, lang=None, start_time=None, end_time=None, page=None, per_page=None):
        """자막 내용 검색 (FTS 이용)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 페이지 및 항목 수 처리 (main.py와의 호환성)
        if page is not None and per_page is not None:
            offset = (page - 1) * per_page
            limit = per_page
        
        # 쿼리 파라미터
        params = []
        
        # 기본 검색 쿼리
        sql = """
            SELECT 
                s.id, s.media_id, s.start_time, s.end_time,
                s.start_time_text, s.end_time_text, s.content, s.lang,
                m.path as media_path,
                snippet(subtitles_fts, 0, '<b>', '</b>', '...', 20) as highlight
            FROM 
                subtitles s
            JOIN 
                media_files m ON s.media_id = m.id
            JOIN 
                subtitles_fts f ON s.id = f.rowid
            WHERE 
                subtitles_fts MATCH ?
        """
        params.append(query)
        
        # 언어 필터 추가
        if lang:
            sql += " AND s.lang = ?"
            params.append(lang)
        
        # 시간대 필터 추가
        if start_time and end_time:
            # 시간 형식 변환 (HH:MM:SS -> 초)
            def time_to_seconds(time_str):
                parts = time_str.split(':')
                if len(parts) == 3:
                    h, m, s = map(int, parts)
                    return h * 3600 + m * 60 + s
                return 0
            
            start_seconds = time_to_seconds(start_time)
            end_seconds = time_to_seconds(end_time)
            
            sql += " AND s.start_time >= ? AND s.end_time <= ?"
            params.append(start_seconds)
            params.append(end_seconds)
            
        # 정렬 및 제한
        sql += " ORDER BY s.media_id, s.start_time LIMIT ? OFFSET ?"
        params.append(limit)
        params.append(offset)
        
        cursor.execute(sql, params)
        results = []
        
        for row in cursor.fetchall():
            results.append({
                'id': row[0],
                'media_id': row[1],
                'start_time': row[2],
                'end_time': row[3],
                'start_time_text': row[4],
                'end_time_text': row[5],
                'content': row[6],
                'lang': row[7],
                'media_path': row[8],
                'highlight': row[9]
            })
        
        conn.close()
        return results
    
    def get_media_info(self, media_id):
        """미디어 파일 정보 조회"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, path, has_subtitle, size, last_modified
            FROM media_files WHERE id = ?
        ''', (media_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
            
        return {
            'id': row[0],
            'path': row[1],
            'has_subtitle': bool(row[2]),
            'size': row[3],
            'last_modified': row[4]
        }
    
    def get_all_media(self, with_subtitles_only=False, limit=100, offset=0):
        """모든 미디어 파일 정보 조회"""
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
        results = []
        
        for row in cursor.fetchall():
            results.append({
                'id': row[0],
                'path': row[1],
                'has_subtitle': bool(row[2]),
                'size': row[3],
                'last_modified': row[4]
            })
            
        conn.close()
        return results
    
    def count_media(self, with_subtitles_only=False):
        """미디어 파일 수 조회"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        sql = "SELECT COUNT(*) FROM media_files"
        
        if with_subtitles_only:
            sql += " WHERE has_subtitle = 1"
            
        cursor.execute(sql)
        count = cursor.fetchone()[0]
        
        conn.close()
        return count
    
    def get_subtitles_for_media(self, media_id, limit=None, offset=0):
        """특정 미디어의 자막 조회"""
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
        results = []
        
        for row in cursor.fetchall():
            results.append({
                'id': row[0],
                'media_id': row[1],
                'start_time': row[2],
                'end_time': row[3],
                'start_time_text': row[4],
                'end_time_text': row[5],
                'content': row[6],
                'lang': row[7]
            })
            
        conn.close()
        return results
    
    def rebuild_fts_index(self):
        """FTS 인덱스 전체 재구축 (대량 인덱싱 후 호출)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 트랜잭션 시작
            conn.execute('BEGIN')
            
            # FTS 테이블 삭제 후 재생성
            cursor.execute('DROP TABLE IF EXISTS subtitles_fts')
            
            # FTS 테이블 생성
            cursor.execute('''
                CREATE VIRTUAL TABLE IF NOT EXISTS subtitles_fts USING fts5(
                    content,
                    content='subtitles',
                    content_rowid='id'
                )
            ''')
            
            # 모든 자막 데이터를 FTS 테이블에 삽입
            cursor.execute('''
                INSERT INTO subtitles_fts(rowid, content)
                SELECT id, content FROM subtitles
            ''')
            
            # 트랜잭션 커밋
            conn.commit()
            logger.info(f"FTS 인덱스 재구축 완료")
            return True
            
        except Exception as e:
            # 에러 발생 시 롤백
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
            
            return [row[0] for row in cursor.fetchall()]
            
        except Exception as e:
            logger.error(f"태그 조회 실패: {e}")
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
            return [f"{row[0]}|{row[1]}" for row in cursor.fetchall()]
            
        except Exception as e:
            logger.error(f"북마크 조회 실패: {e}")
            return []
            
        finally:
            conn.close()