"""
데이터베이스 정리 모듈

데이터베이스 내의 중복 데이터나 오래된 데이터를 정리하는 함수들을 제공합니다.
"""

import os
from typing import List, Dict, Any, Optional, Tuple
import logging

from app.utils.logging import setup_module_logger
from app.config import config
from app.database.connection import get_connection, execute_query, fetch_one, fetch_all

# 로거 초기화
logger = setup_module_logger("database.cleanup")


def remove_duplicate_media_files() -> Dict[str, Any]:
    """
    중복된 미디어 파일 레코드를 정리합니다.
    같은 파일명을 가진 미디어 파일 중 현재 media_directory에 존재하지 않는 파일을 삭제합니다.
    
    Returns:
        Dict[str, Any]: 정리 결과 정보
    """
    try:
        # 현재 설정된 미디어 디렉토리 가져오기
        media_dir = config.get("media_dir", "")
        if not media_dir:
            return {"success": False, "message": "미디어 디렉토리가 설정되지 않았습니다."}
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # 모든 미디어 파일 가져오기
        cursor.execute("SELECT id, path FROM media_files")
        all_media = cursor.fetchall()
        
        # 파일명 기준으로 그룹화
        filename_groups = {}
        for media in all_media:
            filename = os.path.basename(media["path"])
            if filename not in filename_groups:
                filename_groups[filename] = []
            filename_groups[filename].append(media)
        
        # 중복 파일 처리
        removed_count = 0
        kept_count = 0
        
        for filename, files in filename_groups.items():
            if len(files) > 1:
                # 중복 파일이 있는 경우
                keep_id = None
                
                # 현재 미디어 디렉토리에 있는 파일 우선 유지
                for file in files:
                    if file["path"].startswith(media_dir):
                        keep_id = file["id"]
                        break
                
                # 현재 디렉토리에 없으면 첫 번째 파일 유지
                if keep_id is None and files:
                    keep_id = files[0]["id"]
                
                # 나머지 파일 삭제
                for file in files:
                    if file["id"] != keep_id:
                        # 자막 먼저 삭제
                        cursor.execute("DELETE FROM subtitles WHERE media_id = ?", (file["id"],))
                        # 미디어 파일 삭제
                        cursor.execute("DELETE FROM media_files WHERE id = ?", (file["id"],))
                        removed_count += 1
                
                kept_count += 1
            else:
                kept_count += 1
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "removed_count": removed_count,
            "kept_count": kept_count,
            "total_before": len(all_media),
            "total_after": kept_count
        }
    
    except Exception as e:
        logger.error(f"중복 미디어 파일 정리 중 오류 발생: {e}")
        return {"success": False, "message": f"오류 발생: {str(e)}"}


def get_subtitle_file_count() -> int:
    """
    실제 자막 파일 수를 반환합니다. (자막 대사 수가 아님)
    미디어 파일 중 자막이 있는 파일의 수를 계산합니다.
    
    Returns:
        int: 자막 파일 수
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as count FROM media_files WHERE has_subtitle = 1")
        result = cursor.fetchone()
        conn.close()
        
        return result["count"] if result else 0
    
    except Exception as e:
        logger.error(f"자막 파일 수 조회 중 오류 발생: {e}")
        return 0
