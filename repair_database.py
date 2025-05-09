#!/usr/bin/env python3
# 데이터베이스 복구 및 FTS 재구축 스크립트
import sqlite3
import os
import json
import time
import shutil
from pathlib import Path

def load_config():
    """설정 파일을 로드하는 함수"""
    config_path = Path('config.json')
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    return {'db_path': 'media_index.db'}

def create_backup(db_path):
    """데이터베이스 백업 생성"""
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_path}.backup_{timestamp}"
    shutil.copy2(db_path, backup_path)
    print(f"백업 생성 완료: {backup_path}")
    return backup_path

def create_new_database():
    """새로운 데이터베이스 생성 및 스키마 설정"""
    print("새 데이터베이스 생성 중...")
    new_db_path = "media_index.db.new"
    
    # 이미 존재하는 경우 삭제
    if os.path.exists(new_db_path):
        os.remove(new_db_path)
    
    conn = sqlite3.connect(new_db_path)
    cursor = conn.cursor()
    
    # 미디어 파일 테이블 생성
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS media_files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        path TEXT UNIQUE,
        size INTEGER,
        last_modified INTEGER,
        duration REAL,
        video_codec TEXT,
        audio_codec TEXT,
        width INTEGER,
        height INTEGER,
        indexed_at INTEGER
    )''')
    
    # 자막 테이블 생성
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS subtitles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        media_id INTEGER,
        content TEXT,
        start_time REAL,
        end_time REAL,
        lang TEXT,
        FOREIGN KEY (media_id) REFERENCES media_files(id)
    )''')
    
    # FTS 가상 테이블 생성
    cursor.execute('''
    CREATE VIRTUAL TABLE IF NOT EXISTS subtitles_fts USING fts5(
        content,
        content='subtitles',
        content_rowid='id'
    )''')
    
    conn.commit()
    conn.close()
    print(f"새 데이터베이스 생성 완료: {new_db_path}")
    return new_db_path

def migrate_data(old_db_path, new_db_path):
    """이전 데이터베이스에서 새 데이터베이스로 데이터 마이그레이션"""
    print("데이터 마이그레이션 시작...")
    
    # 이전 데이터베이스 연결
    old_conn = sqlite3.connect(old_db_path)
    old_cursor = old_conn.cursor()
    
    # 새 데이터베이스 연결
    new_conn = sqlite3.connect(new_db_path)
    new_cursor = new_conn.cursor()
    
    try:
        # 1. media_files 테이블 데이터 이전
        print("미디어 파일 데이터 마이그레이션 중...")
        
        # 이전 데이터베이스의 컬럼 정보 가져오기
        old_cursor.execute("PRAGMA table_info(media_files)")
        old_columns = [col[1] for col in old_cursor.fetchall()]
        
        # 새 데이터베이스의 컬럼 정보 가져오기 
        new_cursor.execute("PRAGMA table_info(media_files)")
        new_columns = [col[1] for col in new_cursor.fetchall()]
        
        # 공통 컬럼만 선택
        common_columns = [col for col in old_columns if col in new_columns]
        columns_str = ", ".join(common_columns)
        
        print(f"미디어 파일 테이블 마이그레이션 - 사용 컬럼: {columns_str}")
        
        # 데이터 조회 (공통 컬럼만)
        old_cursor.execute(f"SELECT {columns_str} FROM media_files")
        media_files = old_cursor.fetchall()
        
        # 데이터 삽입
        for media_file in media_files:
            placeholders = ", ".join(["?"] * len(media_file))
            new_cursor.execute(f"INSERT INTO media_files ({columns_str}) VALUES ({placeholders})", media_file)
        
        # 2. subtitles 테이블 데이터 이전 (배치 처리)
        print("자막 데이터 마이그레이션 중...")
        
        # 이전 데이터베이스의 자막 테이블 컬럼 정보 가져오기
        old_cursor.execute("PRAGMA table_info(subtitles)")
        old_subtitle_columns = [col[1] for col in old_cursor.fetchall()]
        
        # 새 데이터베이스의 자막 테이블 컬럼 정보 가져오기
        new_cursor.execute("PRAGMA table_info(subtitles)")
        new_subtitle_columns = [col[1] for col in new_cursor.fetchall()]
        
        # 공통 컬럼만 선택
        common_subtitle_columns = [col for col in old_subtitle_columns if col in new_subtitle_columns]
        subtitle_columns_str = ", ".join(common_subtitle_columns)
        
        print(f"자막 테이블 마이그레이션 - 사용 컬럼: {subtitle_columns_str}")
        
        # 전체 자막 수 조회
        old_cursor.execute("SELECT COUNT(*) FROM subtitles")
        total_subtitles = old_cursor.fetchone()[0]
        
        batch_size = 5000
        processed = 0
        
        while processed < total_subtitles:
            old_cursor.execute(f"SELECT {subtitle_columns_str} FROM subtitles LIMIT {batch_size} OFFSET {processed}")
            subtitles_batch = old_cursor.fetchall()
            
            if not subtitles_batch:
                break
            
            # 배치 삽입
            new_conn.executemany(
                f"INSERT INTO subtitles ({subtitle_columns_str}) VALUES ({', '.join(['?'] * len(common_subtitle_columns))})",
                subtitles_batch
            )
            
            processed += len(subtitles_batch)
            print(f"자막 데이터 처리 중: {processed}/{total_subtitles} ({processed/total_subtitles*100:.1f}%)")
            
            # 주기적으로 커밋
            new_conn.commit()
        
        # 3. subtitles_fts 테이블 데이터 구축
        print("FTS 테이블 구축 중...")
        new_cursor.execute("""
            INSERT INTO subtitles_fts(rowid, content)
            SELECT id, content FROM subtitles
        """)
        
        # FTS 테이블 최적화
        print("FTS 테이블 최적화 중...")
        new_cursor.execute("INSERT INTO subtitles_fts(subtitles_fts) VALUES('optimize')")
        
        # 커밋
        new_conn.commit()
        
        print(f"데이터 마이그레이션 완료: {processed} 자막 항목 처리됨")
        
        # 검색 테스트
        print("\n마이그레이션 후 FTS 검색 테스트:")
        search_terms = ["the", "and", "hello", "good"]
        
        for term in search_terms:
            new_cursor.execute("""
                SELECT COUNT(*)
                FROM subtitles_fts
                WHERE subtitles_fts MATCH ?
            """, (term,))
            
            count = new_cursor.fetchone()[0]
            print(f"검색어 '{term}': {count}개 결과")
        
        return True
        
    except sqlite3.Error as e:
        print(f"마이그레이션 중 오류 발생: {e}")
        new_conn.rollback()
        return False
    
    finally:
        old_conn.close()
        new_conn.close()

def replace_database(old_db_path, new_db_path):
    """새 데이터베이스로 이전 데이터베이스 대체"""
    print("데이터베이스 교체 중...")
    
    try:
        # 이전 데이터베이스 삭제 전 한번 더 백업
        create_backup(old_db_path)
        
        # SQLite 관련 파일도 처리 (-shm, -wal)
        for ext in ['', '-shm', '-wal']:
            old_file = f"{old_db_path}{ext}"
            new_file = f"{new_db_path}{ext}"
            
            # 이전 파일 삭제
            if os.path.exists(old_file):
                os.remove(old_file)
            
            # 새 파일 이름 변경 (있는 경우만)
            if os.path.exists(new_file):
                shutil.move(new_file, old_file)
        
        print("데이터베이스 교체 완료")
        return True
        
    except Exception as e:
        print(f"데이터베이스 교체 중 오류 발생: {e}")
        return False

def main():
    # 설정 로드
    config = load_config()
    db_path = config.get('db_path', 'media_index.db')
    
    # 1. 백업 생성
    create_backup(db_path)
    
    # 2. 새 데이터베이스 생성
    new_db_path = create_new_database()
    
    # 3. 데이터 마이그레이션
    success = migrate_data(db_path, new_db_path)
    
    if success:
        # 4. 데이터베이스 교체
        replace_database(db_path, new_db_path)
        print("복구 작업이 성공적으로 완료되었습니다.")
    else:
        print("데이터 마이그레이션에 실패하여 데이터베이스 교체를 취소합니다.")

if __name__ == "__main__":
    main()