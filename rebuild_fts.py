#!/usr/bin/env python
"""
FTS 인덱스 재구축 스크립트

FTS 인덱스에 문제가 있을 때 인덱스를 재구축하는 스크립트입니다.
"""

import os
import sqlite3
import logging
import sys
from pathlib import Path

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_db_path():
    """데이터베이스 파일 경로 반환"""
    # 기본 경로
    db_path = "media_index.db"
    
    # 환경 변수에서 경로를 가져올 수도 있음
    if os.environ.get("DB_PATH"):
        db_path = os.environ.get("DB_PATH")
    
    # 경로가 존재하는지 확인
    if not os.path.exists(db_path):
        logger.error(f"데이터베이스 파일이 존재하지 않습니다: {db_path}")
        return None
    
    return db_path

def rebuild_fts_index(db_path, force=False):
    """FTS 인덱스 재구축"""
    try:
        # 데이터베이스 연결
        conn = sqlite3.connect(db_path)
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
            logger.info("FTS 테이블 생성 중...")
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS subtitles_fts USING fts5(
                    content,
                    content='subtitles',
                    content_rowid='id'
                )
            """)
        
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
            for i in range(0, len(subtitles), batch_size):
                batch = subtitles[i:i + batch_size]
                
                # 배치 삽입
                cursor.executemany(
                    "INSERT INTO subtitles_fts(rowid, content) VALUES (?, ?)",
                    batch
                )
                
                logger.info(f"진행 중: {min(i + batch_size, len(subtitles))}/{len(subtitles)}")
            
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
            
    except sqlite3.Error as e:
        logger.error(f"데이터베이스 오류: {e}")
        if conn:
            conn.rollback()
        return False
    except Exception as e:
        logger.error(f"예기치 않은 오류: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def test_fts_search(db_path, query):
    """FTS 검색 테스트"""
    try:
        # 데이터베이스 연결
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # FTS 검색 수행
        cursor.execute(f"SELECT count(*) FROM subtitles_fts WHERE content MATCH ?", (query,))
        fts_count = cursor.fetchone()[0]
        
        # LIKE 검색 수행 (비교용)
        cursor.execute(f"SELECT count(*) FROM subtitles WHERE content LIKE ?", (f'%{query}%',))
        like_count = cursor.fetchone()[0]
        
        logger.info(f"FTS 검색 결과 ('{query}'): {fts_count}개")
        logger.info(f"LIKE 검색 결과 ('{query}'): {like_count}개")
        
        # 예시 결과 출력
        if fts_count > 0:
            cursor.execute(
                """SELECT s.id, s.content, m.path 
                   FROM subtitles s 
                   JOIN subtitles_fts f ON s.id = f.rowid 
                   JOIN media_files m ON s.media_id = m.id 
                   WHERE f.content MATCH ? LIMIT 5""", 
                (query,)
            )
            
            results = cursor.fetchall()
            logger.info(f"검색 결과 샘플 (상위 {len(results)}개):")
            for result in results:
                logger.info(f"ID: {result[0]}, 미디어: {result[2]}, 내용: {result[1][:50]}...")
        
        return fts_count
    except sqlite3.Error as e:
        logger.error(f"검색 테스트 중 데이터베이스 오류: {e}")
        return -1
    finally:
        if conn:
            conn.close()

def main():
    """메인 함수"""
    # 명령줄 인자 처리
    force_rebuild = False
    test_query = None
    
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if arg == '--force' or arg == '-f':
                force_rebuild = True
            elif arg.startswith('--test='):
                test_query = arg.split('=')[1]
    
    # 데이터베이스 경로 가져오기
    db_path = get_db_path()
    if not db_path:
        return 1
    
    logger.info(f"데이터베이스 경로: {db_path}")
    
    # 기능 선택
    if test_query:
        # 검색 테스트만 수행
        test_fts_search(db_path, test_query)
    else:
        # FTS 인덱스 재구축
        result = rebuild_fts_index(db_path, force=force_rebuild)
        
        if result:
            logger.info("FTS 인덱스 재구축 성공!")
            
            # 기본 검색어로 테스트
            test_queries = ["the", "and", "is", "in", "for"]
            for query in test_queries:
                test_fts_search(db_path, query)
        else:
            logger.error("FTS 인덱스 재구축 실패!")
            return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 