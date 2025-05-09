"""
자막 검색 모듈
"""

import logging
from typing import List, Dict, Any, Optional, Tuple, Union

from app.utils.logging import setup_module_logger
from app.config import config
from app.database.connection import get_connection, execute_query, fetch_one, fetch_all, connection_context

# 로거 초기화
logger = setup_module_logger("database.subtitles.search")

def search_subtitles(query: str, lang: str = None, start_time: str = None, end_time: str = None, 
                  page: int = 1, per_page: int = 50, search_method: str = 'fts') -> List[Dict[str, Any]]:
    """
    자막 내용 검색

    Args:
        query: 검색어
        lang: 언어 필터
        start_time: 시작 시간 필터 (HH:MM:SS)
        end_time: 종료 시간 필터 (HH:MM:SS)
        page: 페이지 번호 (1부터 시작)
        per_page: 페이지당 결과 수
        search_method: 검색 방식 ('like' 또는 'fts', 기본값: 'fts')
        
    Returns:
        List[Dict[str, Any]]: 검색 결과 목록
    """
    if not query or query.strip() == "":
        return []
    
    # 검색어 전처리
    query = query.strip()
    
    # 특수 문자 제거 (오류 방지)
    for char in ['"', "'", ";", "--", "/*", "*/", "\\"]:
        query = query.replace(char, " ")
    
    # 빈 검색어 처리
    query = query.strip()
    if not query:
        return []
    
    # 페이지네이션 처리
    offset = (page - 1) * per_page
    
    try:
        # 검색 방식에 따른 쿼리 작성
        if search_method.lower() == 'fts':
            # FTS 테이블 존재 확인
            fts_exists = fetch_one("SELECT name FROM sqlite_master WHERE type='table' AND name='subtitles_fts'")
            if not fts_exists:
                raise ValueError("FTS 테이블이 존재하지 않습니다.")
                
            # FTS 쿼리 작성 (실제 DB 컬럼명에 맞게 수정)
            sql = "SELECT s.id, s.media_id, s.start_time, s.end_time, s.start_time_text, s.end_time_text, s.content, s.lang, m.path as media_path, m.has_subtitle FROM subtitles_fts fts JOIN subtitles s ON fts.rowid = s.id JOIN media_files m ON s.media_id = m.id WHERE subtitles_fts MATCH ?"
            params = [query]
            
        else:  # 'like' 검색 방식
            # LIKE 쿼리 작성 (실제 DB 컬럼명에 맞게 수정)
            sql = "SELECT s.id, s.media_id, s.start_time, s.end_time, s.start_time_text, s.end_time_text, s.content, s.lang, m.path as media_path, m.has_subtitle FROM subtitles s JOIN media_files m ON s.media_id = m.id WHERE s.content LIKE ?"
            params = [f"%{query}%"]
        
        # 추가 필터 적용
        if lang:
            sql += " AND s.lang = ?"
            params.append(lang)
            
        # 시간 필터 적용
        if start_time:
            # HH:MM:SS 형식을 밀리초로 변환
            parts = start_time.split(":")
            if len(parts) == 3:
                hours, minutes, seconds = map(int, parts)
                start_ms = (hours * 3600 + minutes * 60 + seconds) * 1000
                sql += " AND s.end_time >= ?"
                params.append(start_ms)
                
        if end_time:
            # HH:MM:SS 형식을 밀리초로 변환
            parts = end_time.split(":")
            if len(parts) == 3:
                hours, minutes, seconds = map(int, parts)
                end_ms = (hours * 3600 + minutes * 60 + seconds) * 1000
                sql += " AND s.start_time <= ?"
                params.append(end_ms)
        
        # 정렬 및 페이지네이션
        sql += " ORDER BY s.media_id, s.start_time LIMIT ? OFFSET ?"
        params.extend([per_page, offset])
        
        # 쿼리 실행
        results = fetch_all(sql, tuple(params))
        return results or []
        
    except Exception as e:
        logger.error(f"자막 검색 중 오류 발생: {str(e)}")
        logger.error(f"SQL: {sql if 'sql' in locals() else '?'}, Params: {params if 'params' in locals() else '?'}")
        import traceback
        logger.error(traceback.format_exc())
        return []

def estimate_total_count(query: str, lang: str = None, start_time: str = None, end_time: str = None, 
                     search_method: str = 'fts') -> int:
    """
    검색 조건에 맞는 총 결과 수 추정

    Args:
        query: 검색어
        lang: 언어 필터
        start_time: 시작 시간 필터 (HH:MM:SS)
        end_time: 종료 시간 필터 (HH:MM:SS)
        search_method: 검색 방식 ('like' 또는 'fts', 기본값: 'fts')
        
    Returns:
        int: 총 결과 수 추정값
    """
    if not query or query.strip() == "":
        return 0
    
    # 검색어 전처리
    query = query.strip()
    
    # 특수 문자 제거 (오류 방지)
    for char in ['"', "'", ";", "--", "/*", "*/", "\\"]:
        query = query.replace(char, " ")
    
    # 빈 검색어 처리
    query = query.strip()
    if not query:
        return 0
    
    try:
        # 검색 방식에 따른 쿼리 작성
        if search_method.lower() == 'fts':
            # FTS 테이블 존재 확인
            fts_exists = fetch_one("SELECT name FROM sqlite_master WHERE type='table' AND name='subtitles_fts'")
            if not fts_exists:
                raise ValueError("FTS 테이블이 존재하지 않습니다.")
                
            # FTS 쿼리 작성 (실제 DB 컬럼명에 맞게 수정)
            sql = "SELECT COUNT(*) as count FROM subtitles_fts fts JOIN subtitles s ON fts.rowid = s.id WHERE subtitles_fts MATCH ?"
            params = [query]
            
        else:  # 'like' 검색 방식
            # LIKE 쿼리 작성 (실제 DB 컬럼명에 맞게 수정)
            sql = "SELECT COUNT(*) as count FROM subtitles s WHERE s.content LIKE ?"
            params = [f"%{query}%"]
        
        # 추가 필터 적용
        if lang:
            sql += " AND s.lang = ?"
            params.append(lang)
            
        # 시간 필터 적용
        if start_time:
            # HH:MM:SS 형식을 밀리초로 변환
            parts = start_time.split(":")
            if len(parts) == 3:
                hours, minutes, seconds = map(int, parts)
                start_ms = (hours * 3600 + minutes * 60 + seconds) * 1000
                sql += " AND s.end_time >= ?"
                params.append(start_ms)
                
        if end_time:
            # HH:MM:SS 형식을 밀리초로 변환
            parts = end_time.split(":")
            if len(parts) == 3:
                hours, minutes, seconds = map(int, parts)
                end_ms = (hours * 3600 + minutes * 60 + seconds) * 1000
                sql += " AND s.start_time <= ?"
                params.append(end_ms)
        
        # 쿼리 실행
        result = fetch_one(sql, tuple(params))
        return result["count"] if result else 0
        
    except Exception as e:
        logger.error(f"검색 결과 수 추정 중 오류 발생: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 0
