#!/usr/bin/env python3
# 자막 데이터베이스와 FTS 테이블 상태 확인 및 수정 스크립트
import sqlite3
import os
from pathlib import Path
import sys

def load_config():
    """설정 파일을 로드하는 함수"""
    import json
    config_path = Path('config.json')
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    return {'db_path': 'media_index.db'}

def check_database():
    """데이터베이스와 FTS 테이블 상태 확인"""
    config = load_config()
    db_path = config.get('db_path', 'media_index.db')
    print(f"데이터베이스 경로: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"오류: 데이터베이스 파일이 존재하지 않습니다. ({db_path})")
        return
    
    # 데이터베이스 연결
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 테이블 존재 확인
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [table[0] for table in cursor.fetchall()]
    print(f"데이터베이스 테이블 목록: {tables}")
    
    if 'subtitles' not in tables:
        print("오류: subtitles 테이블이 존재하지 않습니다.")
        conn.close()
        return
    
    if 'subtitles_fts' not in tables:
        print("오류: subtitles_fts 테이블이 존재하지 않습니다.")
        conn.close()
        return
    
    # 자막 데이터 확인
    cursor.execute("SELECT COUNT(*) FROM subtitles")
    subtitle_count = cursor.fetchone()[0]
    print(f"자막 데이터 수: {subtitle_count}")
    
    # FTS 테이블 데이터 확인
    cursor.execute("SELECT COUNT(*) FROM subtitles_fts")
    fts_count = cursor.fetchone()[0]
    print(f"FTS 테이블 데이터 수: {fts_count}")
    
    if subtitle_count != fts_count:
        print(f"경고: 자막 테이블({subtitle_count})과 FTS 테이블({fts_count})의 데이터 수가 일치하지 않습니다.")
    
    # 샘플 자막 데이터 출력
    if subtitle_count > 0:
        print("\n=== 샘플 자막 데이터 ===")
        cursor.execute("""
            SELECT s.id, m.path, s.content, s.lang
            FROM subtitles s
            JOIN media_files m ON s.media_id = m.id
            LIMIT 5
        """)
        
        for row in cursor.fetchall():
            print(f"ID: {row[0]}, 미디어: {row[1]}, 언어: {row[3]}")
            print(f"내용: {row[2][:80]}..." if len(row[2]) > 80 else f"내용: {row[2]}")
            print("-" * 50)
    
    # 자막 검색 테스트
    print("\n=== 자막 검색 테스트 ===")
    search_terms = ["the", "and", "hello", "은", "는", "을", "를"]
    
    for term in search_terms:
        cursor.execute("""
            SELECT COUNT(*)
            FROM subtitles_fts
            WHERE subtitles_fts MATCH ?
        """, (term,))
        
        count = cursor.fetchone()[0]
        print(f"검색어 '{term}': {count}개 결과")
    
    # FTS 테이블 재구축 필요 여부 확인
    print("\n=== FTS 테이블 상태 확인 ===")
    try:
        cursor.execute("INSERT INTO subtitles_fts(subtitles_fts) VALUES('integrity-check')")
        print("FTS 테이블 무결성 확인 완료: 문제 없음")
    except sqlite3.Error as e:
        print(f"FTS 테이블 무결성 오류: {e}")
        print("FTS 테이블 재구축이 필요합니다.")
    
    conn.close()
    print("\n검사 완료!")

def rebuild_fts_table():
    """FTS 테이블 재구축"""
    print("FTS 테이블 재구축을 시작합니다...")
    
    config = load_config()
    db_path = config.get('db_path', 'media_index.db')
    
    if not os.path.exists(db_path):
        print(f"오류: 데이터베이스 파일이 존재하지 않습니다. ({db_path})")
        return False
    
    # 데이터베이스 연결
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 트랜잭션 시작
        conn.execute("BEGIN TRANSACTION")
        
        # 1. FTS 테이블 내용 삭제
        print("기존 FTS 테이블 내용 삭제 중...")
        cursor.execute("DELETE FROM subtitles_fts")
        
        # 2. 자막 테이블의 모든 내용을 FTS 테이블에 추가
        print("자막 데이터를 FTS 테이블에 추가 중...")
        cursor.execute("""
            INSERT INTO subtitles_fts(rowid, content)
            SELECT id, content FROM subtitles
        """)
        
        # 3. FTS 테이블 최적화
        print("FTS 테이블 최적화 중...")
        cursor.execute("INSERT INTO subtitles_fts(subtitles_fts) VALUES('optimize')")
        
        # 커밋
        conn.commit()
        print("FTS 테이블 재구축 완료!")
        
        # 테스트 검색 실행
        print("\n재구축 후 검색 테스트:")
        search_terms = ["the", "and", "hello"]
        
        for term in search_terms:
            cursor.execute("""
                SELECT COUNT(*)
                FROM subtitles_fts
                WHERE subtitles_fts MATCH ?
            """, (term,))
            
            count = cursor.fetchone()[0]
            print(f"검색어 '{term}': {count}개 결과")
        
        return True
        
    except sqlite3.Error as e:
        conn.rollback()
        print(f"FTS 테이블 재구축 중 오류 발생: {e}")
        import traceback
        print(traceback.format_exc())
        return False
        
    finally:
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--rebuild":
        rebuild_fts_table()
    else:
        check_database()
        print("\nFTS 테이블을 재구축하려면 다음 명령어를 실행하세요:")
        print("python check_subtitles.py --rebuild")