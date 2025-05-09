#!/usr/bin/env python
"""
검색 기능 디버깅 스크립트

검색이 제대로 작동하지 않는 문제를 진단하기 위한 스크립트입니다.
"""

import os
import sqlite3
import logging
import sys
import json
import argparse

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

def check_fts_table(db_path):
    """FTS 테이블 상태 확인"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 테이블 존재 여부 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='subtitles_fts'")
        if not cursor.fetchone():
            logger.error("FTS 테이블이 존재하지 않습니다.")
            return False
        
        # FTS 테이블 내용 확인
        cursor.execute("SELECT count(*) FROM subtitles_fts")
        fts_count = cursor.fetchone()[0]
        
        # 원본 테이블 개수 확인
        cursor.execute("SELECT count(*) FROM subtitles")
        subtitles_count = cursor.fetchone()[0]
        
        logger.info(f"FTS 테이블 레코드 수: {fts_count}")
        logger.info(f"자막 테이블 레코드 수: {subtitles_count}")
        
        # 차이 확인
        if fts_count != subtitles_count:
            logger.warning(f"FTS 테이블과 자막 테이블의 레코드 수가 일치하지 않습니다. (FTS: {fts_count}, 자막: {subtitles_count})")
        
        # 샘플 검색
        common_words = ["the", "and", "to", "of", "a", "in", "is", "it", "that", "for"]
        for word in common_words:
            cursor.execute("SELECT count(*) FROM subtitles_fts WHERE content MATCH ?", (word,))
            match_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT count(*) FROM subtitles WHERE content LIKE ?", (f"%{word}%",))
            like_count = cursor.fetchone()[0]
            
            if match_count == 0 and like_count > 0:
                logger.warning(f"'{word}' 검색 결과: FTS=0, LIKE={like_count} => FTS 인덱스 문제가 있습니다.")
            else:
                logger.info(f"'{word}' 검색 결과: FTS={match_count}, LIKE={like_count}")
                
        conn.close()
        return True
    except Exception as e:
        logger.error(f"FTS 테이블 확인 중 오류: {e}")
        return False

def search_test(db_path, query):
    """검색 테스트 수행"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # FTS로 검색
        logger.info(f"검색어: '{query}'")
        
        # 1. FTS 검색
        try:
            cursor.execute("SELECT count(*) FROM subtitles_fts WHERE content MATCH ?", (query,))
            fts_count = cursor.fetchone()[0]
            logger.info(f"FTS 검색 결과: {fts_count}개")
            
            if fts_count > 0:
                cursor.execute("""
                    SELECT s.id, s.content, m.path 
                    FROM subtitles s 
                    JOIN subtitles_fts f ON s.id = f.rowid 
                    JOIN media_files m ON s.media_id = m.id 
                    WHERE f.content MATCH ? 
                    LIMIT 5
                """, (query,))
                
                results = cursor.fetchall()
                for idx, result in enumerate(results, 1):
                    logger.info(f"결과 {idx}: ID={result[0]}, 내용='{result[1][:50]}...'")
        except sqlite3.Error as e:
            logger.error(f"FTS 검색 오류: {e}")
        
        # 2. LIKE 검색
        cursor.execute("SELECT count(*) FROM subtitles WHERE content LIKE ?", (f"%{query}%",))
        like_count = cursor.fetchone()[0]
        logger.info(f"LIKE 검색 결과: {like_count}개")
        
        if like_count > 0:
            cursor.execute("""
                SELECT s.id, s.content, m.path 
                FROM subtitles s 
                JOIN media_files m ON s.media_id = m.id 
                WHERE s.content LIKE ? 
                LIMIT 5
            """, (f"%{query}%",))
            
            results = cursor.fetchall()
            for idx, result in enumerate(results, 1):
                logger.info(f"결과 {idx}: ID={result[0]}, 내용='{result[1][:50]}...'")
        
        conn.close()
        return True
    except Exception as e:
        logger.error(f"검색 테스트 중 오류: {e}")
        return False

def rebuild_fts_index(db_path):
    """FTS 인덱스 재구축"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 트랜잭션 시작
        conn.execute('BEGIN')
        
        # FTS 테이블 초기화
        cursor.execute("DELETE FROM subtitles_fts")
        
        # 자막 데이터 가져오기
        cursor.execute("SELECT id, content FROM subtitles")
        subtitles = cursor.fetchall()
        
        # 배치 크기 설정
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
        logger.info(f"인덱스 재구축 완료: {new_fts_count}/{len(subtitles)} 항목 인덱싱됨")
        
        # 인덱스 최적화
        logger.info("FTS 인덱스 최적화 중...")
        cursor.execute("INSERT INTO subtitles_fts(subtitles_fts) VALUES('optimize')")
        conn.commit()
        
        conn.close()
        return True
    except Exception as e:
        logger.error(f"FTS 인덱스 재구축 중 오류: {e}")
        if 'conn' in locals():
            conn.rollback()
        return False

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="검색 기능 디버깅 도구")
    parser.add_argument("--check", action="store_true", help="FTS 테이블 상태 확인")
    parser.add_argument("--search", type=str, help="검색어를 사용하여 테스트")
    parser.add_argument("--rebuild", action="store_true", help="FTS 인덱스 재구축")
    
    args = parser.parse_args()
    
    # 기본 동작 설정
    if not (args.check or args.search or args.rebuild):
        args.check = True  # 기본적으로 상태 확인 수행
    
    # 설정 로드
    config = get_config()
    db_path = config.get("db_path", "media_index.db")
    
    logger.info(f"데이터베이스 경로: {db_path}")
    
    if args.check:
        check_fts_table(db_path)
        
    if args.search:
        search_test(db_path, args.search)
        
    if args.rebuild:
        rebuild_fts_index(db_path)
        
    return 0

if __name__ == "__main__":
    sys.exit(main()) 