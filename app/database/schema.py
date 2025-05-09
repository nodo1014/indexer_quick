"""
데이터베이스 스키마 정의 및 초기화 모듈

테이블 생성, 인덱스 생성 및 전체 데이터베이스 초기화 기능을 제공합니다.

중요: FTS(Full-Text Search) 인덱스는 외부 콘텐츠 테이블 참조 방식을 사용합니다.
- content='subtitles' 설정으로 subtitles 테이블을 참조합니다.
- content_rowid='id' 설정으로 PK-FK 관계를 설정합니다.
- FTS 인덱스가 손상되면 rebuild_fts_index() 함수로 재구축할 수 있습니다.
"""

import logging
from typing import List, Dict, Any

from app.utils.logging import setup_module_logger
from app.database.connection import get_connection, execute_query, execute_transaction

# 로거 초기화
logger = setup_module_logger("database.schema")

def create_tables() -> bool:
    """
    필요한 모든 테이블 생성
    
    Returns:
        bool: 성공 여부
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # media_files 테이블 생성
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS media_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL,
                has_subtitle BOOLEAN DEFAULT 0,
                size INTEGER DEFAULT 0,
                last_modified TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
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
        
        # jobs 테이블 생성
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_type TEXT NOT NULL,
                target_id INTEGER,
                params TEXT,
                status TEXT DEFAULT 'pending',
                progress REAL DEFAULT 0,
                result TEXT,
                error TEXT,
                retry_count INTEGER DEFAULT 0,
                retry_after TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
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
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs (status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_jobs_type ON jobs (job_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_jobs_target_id ON jobs (target_id)')
        
        conn.commit()
        conn.close()
        
        # FTS 가상 테이블 생성
        create_fts_table()
        
        logger.info("데이터베이스 테이블 생성 완료")
        return True
    except Exception as e:
        logger.error(f"테이블 생성 중 오류 발생: {e}")
        return False

def create_fts_table() -> bool:
    """
    전문 검색(Full-Text Search)을 위한 가상 테이블 생성
    
    외부 콘텐츠 테이블(subtitles)을 참조하는 방식을 사용합니다.
    이 방식은 subtitles 테이블의 데이터가 변경될 때 FTS 인덱스도 자동으로 갱신되지 않으므로,
    대규모 데이터 변경 후에는 rebuild_fts_index() 함수를 호출해야 합니다.
    
    Returns:
        bool: 성공 여부
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # FTS 가상 테이블 생성 - 외부 테이블 참조 방식 사용
        cursor.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS subtitles_fts USING fts5(
                content,
                content='subtitles',
                content_rowid='id'
            )
        ''')
        
        conn.commit()
        conn.close()
        
        logger.info("FTS 테이블 생성 완료")
        return True
    except Exception as e:
        logger.error(f"FTS 테이블 생성 중 오류 발생: {e}")
        return False

def rebuild_fts_index(force: bool = False) -> bool:
    """
    FTS 인덱스 재구축
    전체 자막 데이터를 읽어와 FTS 인덱스를 재구축합니다.
    
    이 함수는 다음과 같은 경우에 호출해야 합니다:
    1. FTS 인덱스가 손상된 경우
    2. subtitles 테이블과 subtitles_fts 테이블의 레코드 수가 불일치할 경우
    3. 대량의 자막 데이터를 추가/수정/삭제한 후
    
    Args:
        force: 강제 재구축 여부 (True인 경우 기존 테이블 삭제 후 재생성)
        
    Returns:
        bool: 성공 여부
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 자막 테이블 확인
        cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='subtitles'")
        if cursor.fetchone()[0] == 0:
            logger.error("자막 테이블이 존재하지 않습니다.")
            return False
        
        # 자막 데이터 수 확인
        cursor.execute("SELECT count(*) FROM subtitles")
        subtitles_count = cursor.fetchone()[0]
        logger.info(f"자막 데이터 수: {subtitles_count}")
        
        # FTS 테이블 있는지 확인
        cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='subtitles_fts'")
        fts_exists = cursor.fetchone()[0] > 0
        
        if force and fts_exists:
            # 기존 FTS 테이블 삭제
            logger.info("기존 FTS 테이블 삭제 중...")
            cursor.execute("DROP TABLE IF EXISTS subtitles_fts")
            fts_exists = False
        
        # FTS 테이블이 없으면 생성
        if not fts_exists:
            create_fts_table()
        
        # FTS 데이터 수 확인
        cursor.execute("SELECT count(*) FROM subtitles_fts")
        fts_count = cursor.fetchone()[0]
        logger.info(f"FTS 데이터 수: {fts_count}")
        
        # 데이터가 일치하지 않거나 force가 True이면 인덱스 재구축
        if subtitles_count != fts_count or force:
            logger.info("FTS 인덱스 재구축 중...")
            
            # 트랜잭션 시작
            conn.execute('BEGIN')
            
            # FTS 테이블 초기화
            cursor.execute("DELETE FROM subtitles_fts")
            
            # 자막 데이터 가져오기
            cursor.execute("SELECT id, content FROM subtitles")
            subtitles = cursor.fetchall()
            
            # 배치 크기 설정 (메모리 효율성을 위해)
            batch_size = 1000
            total_indexed = 0
            
            for i in range(0, len(subtitles), batch_size):
                batch = subtitles[i:i + batch_size]
                
                # 배치 삽입
                cursor.executemany(
                    "INSERT INTO subtitles_fts(rowid, content) VALUES (?, ?)",
                    batch
                )
                
                total_indexed += len(batch)
                logger.info(f"진행 중: {total_indexed}/{len(subtitles)}")
            
            # 트랜잭션 커밋
            conn.commit()
            
            # 결과 확인
            cursor.execute("SELECT count(*) FROM subtitles_fts")
            new_fts_count = cursor.fetchone()[0]
            logger.info(f"인덱스 재구축 완료: {new_fts_count}/{subtitles_count} 항목 인덱싱됨")
            
            # 인덱스 최적화
            logger.info("FTS 인덱스 최적화 중...")
            cursor.execute("INSERT INTO subtitles_fts(subtitles_fts) VALUES('optimize')")
            conn.commit()
            
            return new_fts_count == subtitles_count
        else:
            logger.info("FTS 인덱스가 이미 최신 상태입니다.")
            return True
            
    except Exception as e:
        # 상세한 오류 로깅을 위한 개선
        import traceback
        error_msg = str(e)
        if not error_msg:  # 빈 예외 메시지인 경우
            error_msg = f"예외 유형: {type(e).__name__}"
        logger.error(f"FTS 인덱스 재구축 중 오류: {error_msg}")
        logger.debug(f"스택 트레이스: {traceback.format_exc()}")
        
        if conn:
            try:
                conn.rollback()
            except:
                pass
        return False
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass

def reset_database() -> bool:
    """
    데이터베이스를 완전히 초기화 (모든 데이터 삭제)
    
    Returns:
        bool: 성공 여부
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 기존 테이블 삭제
        tables = ["subtitle_bookmarks", "subtitle_tags", "subtitles_fts", "subtitles", "media_files"]
        
        for table in tables:
            cursor.execute(f"DROP TABLE IF EXISTS {table}")
        
        conn.commit()
        
        # 테이블 다시 생성
        create_tables()
        
        logger.info("데이터베이스 초기화 (모든 데이터 삭제) 완료")
        return True
    except Exception as e:
        logger.error(f"데이터베이스 초기화 중 오류: {e}")
        if conn:
            try:
                conn.rollback()
            except:
                pass
        return False
    finally:
        if conn:
            conn.close()

def init_db() -> None:
    """
    데이터베이스 초기화 및 필요한 테이블 생성
    
    서버 시작 시 자동으로 호출되며, 다음 작업을 수행합니다:
    1. 필요한 테이블 생성
    2. FTS 인덱스 상태 확인
    3. FTS 인덱스와 subtitles 테이블이 불일치하면 자동 재구축
    """
    # 테이블 생성
    create_tables()
    
    # FTS 인덱스 상태 확인
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 자막 테이블이 존재하는지 확인
        cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='subtitles'")
        if cursor.fetchone()[0] == 0:
            logger.debug("자막 테이블이 아직 존재하지 않습니다.")
            return
        
        # 자막과 FTS 테이블의 레코드 수 비교
        cursor.execute("SELECT count(*) FROM subtitles")
        subtitles_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='subtitles_fts'")
        if cursor.fetchone()[0] == 0:
            logger.info("FTS 테이블이 존재하지 않습니다. 생성합니다.")
            create_fts_table()
            rebuild_fts_index(force=False)
            return
        
        cursor.execute("SELECT count(*) FROM subtitles_fts")
        fts_count = cursor.fetchone()[0]
        
        if subtitles_count != fts_count:
            logger.warning(f"FTS 인덱스가 불일치합니다. (자막: {subtitles_count}, FTS: {fts_count})")
            logger.info("FTS 인덱스를 자동으로 재구축합니다.")
            rebuild_fts_index(force=False)
        else:
            logger.debug("FTS 인덱스가 최신 상태입니다.")
        
    except Exception as e:
        logger.error(f"FTS 인덱스 상태 확인 중 오류 발생: {e}")
    finally:
        if conn:
            conn.close()
    
    logger.debug("데이터베이스 초기화 완료")

def get_table_list() -> List[Dict[str, Any]]:
    """
    데이터베이스의 모든 테이블 목록을 반환
    
    Returns:
        List[Dict[str, Any]]: 테이블 목록 (이름, 타입, 행 수 등 포함)
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 테이블 목록 조회
        cursor.execute("""
            SELECT 
                name, 
                type,
                sql
            FROM 
                sqlite_master 
            WHERE 
                type='table' OR type='view'
            ORDER BY 
                name
        """)
        
        tables = cursor.fetchall()
        result = []
        
        # 각 테이블의 행 수 조회
        for table in tables:
            table_name = table['name']
            if not table_name.startswith('sqlite_'):
                try:
                    count_cursor = conn.cursor()
                    count_cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
                    count = count_cursor.fetchone()['count']
                    
                    result.append({
                        'name': table_name,
                        'type': table['type'],
                        'row_count': count,
                        'sql': table['sql']
                    })
                except Exception as e:
                    logger.error(f"테이블 {table_name} 행 수 조회 오류: {e}")
                    result.append({
                        'name': table_name,
                        'type': table['type'],
                        'row_count': '오류',
                        'sql': table['sql']
                    })
        
        return result
    except Exception as e:
        logger.error(f"테이블 목록 조회 오류: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_table_data(table_name: str, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    """
    지정된 테이블의 데이터를 조회
    
    Args:
        table_name: 조회할 테이블 이름
        limit: 조회할 최대 행 수
        offset: 조회 시작 위치
        
    Returns:
        Dict[str, Any]: 테이블 구조와 데이터
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 테이블 존재 여부 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        if not cursor.fetchone():
            return {'error': f"테이블 {table_name}이(가) 존재하지 않습니다."}
        
        # 테이블 구조 조회
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        # 테이블 데이터 조회
        cursor.execute(f"SELECT * FROM {table_name} LIMIT {limit} OFFSET {offset}")
        rows = cursor.fetchall()
        
        # 전체 행 수 조회
        count_cursor = conn.cursor()
        count_cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
        total_count = count_cursor.fetchone()['count']
        
        return {
            'columns': columns,
            'rows': rows,
            'total_count': total_count,
            'limit': limit,
            'offset': offset
        }
    except Exception as e:
        logger.error(f"테이블 {table_name} 데이터 조회 오류: {e}")
        return {'error': str(e)}
    finally:
        if conn:
            conn.close()