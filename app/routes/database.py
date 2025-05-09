"""
데이터베이스 관리 라우트 모듈

데이터베이스 관리 관련 API 엔드포인트를 정의합니다.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict, Any

from app.database import db, remove_duplicate_media_files

# 라우터 생성
router = APIRouter(prefix="/api/database", tags=["database"])


@router.post("/cleanup/duplicates", response_model=Dict[str, Any])
async def cleanup_duplicate_media():
    """
    중복된 미디어 파일 레코드를 정리합니다.
    같은 파일명을 가진 미디어 파일 중 현재 media_directory에 존재하지 않는 파일을 삭제합니다.
    
    Returns:
        Dict[str, Any]: 정리 결과 정보
    """
    try:
        result = remove_duplicate_media_files()
        if result["success"]:
            return {
                "success": True,
                "message": f"중복 미디어 파일 정리 완료: {result['removed_count']}개 삭제, {result['kept_count']}개 유지",
                "details": result
            }
        else:
            return {
                "success": False,
                "message": result.get("message", "중복 미디어 파일 정리 중 오류가 발생했습니다."),
                "details": result
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"중복 미디어 파일 정리 중 오류가 발생했습니다: {str(e)}")
