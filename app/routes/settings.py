"""
설정 라우트 모듈

애플리케이션 설정과 관련된 API 엔드포인트를 정의합니다.
"""

import logging
from fastapi import APIRouter, Request, Query, Depends, Form, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, Dict, Any, List
import os
import json

from app.config import config, get_config, save_config, get_default_config
from app.database.connection import get_connection
from fastapi.templating import Jinja2Templates
from pathlib import Path

# 템플릿 디렉토리 설정
TEMPLATES_DIR = Path("templates")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# 로거 설정
logger = logging.getLogger(__name__)

# 템플릿 설정
templates = Jinja2Templates(directory="templates")

# 라우터 생성
router = APIRouter(tags=["settings"])

# API 라우터 생성
api_router = APIRouter(prefix="/api", tags=["settings"])

# 메뉴 설정 저장을 위한 기본값
DEFAULT_MENU_SETTINGS = {
    "categories": {
        "basic": {"visible": True, "order": 0},
        "subtitle": {"visible": True, "order": 1},
        "system": {"visible": True, "order": 2}
    },
    "items": {
        "home": {"visible": True, "category": "basic", "order": 0},
        "search": {"visible": True, "category": "basic", "order": 1},
        "dashboard": {"visible": True, "category": "basic", "order": 2},
        "subtitle_encoding": {"visible": True, "category": "subtitle", "order": 0},
        "subtitle_encoding_status": {"visible": True, "category": "subtitle", "order": 1},
        "indexing_process": {"visible": True, "category": "system", "order": 0},
        "database": {"visible": True, "category": "system", "order": 1},
        "settings": {"visible": True, "category": "system", "order": 2}
    }
}

@router.get("/settings", response_class=HTMLResponse)
async def get_settings(request: Request):
    """환경 설정 페이지 표시"""
    config = get_config()
    
    # 미디어 디렉토리 변경 확인 (새 설정 적용 시)
    show_reset_modal = False
    old_media_dir = request.session.get("old_media_dir", "")
    new_media_dir = request.session.get("new_media_dir", "")
    
    if old_media_dir and new_media_dir and old_media_dir != new_media_dir:
        show_reset_modal = True
        
    # 세션에서 이전 디렉토리 정보 제거
    if "old_media_dir" in request.session:
        del request.session["old_media_dir"]
    if "new_media_dir" in request.session:
        del request.session["new_media_dir"]
    
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "config": config,
        "show_reset_modal": show_reset_modal,
        "old_media_dir": old_media_dir,
        "new_media_dir": new_media_dir
    })

@router.post("/settings")
async def save_settings(
    request: Request,
    media_dir: str = Form(...),
    db_path: str = Form(...),
    indexing_strategy: str = Form(...),
    max_threads: int = Form(4),
    media_extensions_hidden: str = Form(""),
    use_absolute_path: bool = Form(False),
    reset_db: str = Form("false"),
    media_extensions: List[str] = Form(None)
):
    """환경 설정 저장"""
    config = get_config()
    
    # 미디어 디렉토리 변경 감지
    old_media_dir = config.get("media_dir", "")
    is_media_dir_changed = old_media_dir != media_dir and old_media_dir != ""
    
    if is_media_dir_changed and reset_db != "true" and request.query_params.get("skip_db_reset_check") != "true":
        # 미디어 디렉토리 변경 시 DB 초기화 확인 모달 표시를 위해 세션에 정보 저장
        request.session["old_media_dir"] = old_media_dir
        request.session["new_media_dir"] = media_dir
        return RedirectResponse("/settings", status_code=303)
    
    # 설정 저장
    config["media_dir"] = media_dir
    config["db_path"] = db_path
    config["indexing_strategy"] = indexing_strategy
    config["max_threads"] = max_threads
    config["use_absolute_path"] = use_absolute_path
    
    # 미디어 확장자 처리
    if media_extensions:
        config["media_extensions"] = media_extensions
    else:
        config["media_extensions"] = []
    
    # 설정 저장
    save_config(config)
    
    # DB 초기화 후 인덱싱 요청된 경우
    if reset_db == "true":
        # DB 파일 삭제 로직
        db_path = config.get("db_path", "media_index.db")
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except Exception as e:
                print(f"DB 파일 삭제 중 오류 발생: {e}")
        
        # 인덱싱 시작 페이지로 리다이렉트
        return RedirectResponse("/indexing-process?start=true", status_code=303)
    
    # 설정 저장 후 자동 인덱싱 시작 (incremental=true)
    return RedirectResponse("/indexing-process?start=true&incremental=true", status_code=303)

# 인덱서 재시도 설정 API
@router.get("/api/settings/retry")
async def get_retry_settings():
    """인덱서 재시도 설정 가져오기"""
    config = get_config()
    return {
        "indexer_retry_count": config.get("indexer_retry_count", 3),
        "indexer_retry_interval": config.get("indexer_retry_interval", 10),
        "auto_restart_indexing": config.get("auto_restart_indexing", False)
    }

@router.post("/api/settings/retry")
async def save_retry_settings(settings: Dict[str, Any]):
    """인덱서 재시도 설정 저장"""
    config = get_config()
    
    # 설정 업데이트
    config["indexer_retry_count"] = settings.get("retry_count", 3)
    config["indexer_retry_interval"] = settings.get("retry_interval", 10)
    config["auto_restart_indexing"] = settings.get("auto_restart", False)
    
    # 설정 저장
    save_config(config)
    
    return {"success": True, "message": "재시도 설정이 저장되었습니다."}

# 메뉴 설정 관련 API 추가
@router.get("/api/settings/menu")
async def get_menu_settings():
    """메뉴 설정 가져오기"""
    config = get_config()
    menu_settings = config.get("menu_settings", DEFAULT_MENU_SETTINGS)
    return {"success": True, "settings": menu_settings}

@router.post("/api/settings/menu")
async def save_menu_settings(settings: Dict[str, Any]):
    """메뉴 설정 저장"""
    try:
        logger.info("메뉴 설정 저장 요청 받음")
        
        # 기존 설정 불러오기
        config = get_config()
        
        # 새 메뉴 설정 저장
        config["menu_settings"] = settings
        save_config(config)
        
        logger.info("메뉴 설정 저장 완료")
        return {
            "success": True, 
            "message": "메뉴 설정이 저장되었습니다.",
            "reload": False  # 페이지 새로고침 필요 없음
        }
    except Exception as e:
        logger.error(f"메뉴 설정 저장 중 오류 발생: {str(e)}")
        return {"success": False, "message": f"메뉴 설정 저장 중 오류가 발생했습니다: {str(e)}"}

@router.post("/api/settings/menu/reset")
async def reset_menu_settings():
    """메뉴 설정 기본값으로 복원"""
    try:
        logger.info("메뉴 설정 초기화 요청 받음")
        
        # 기존 설정 불러오기
        config = get_config()
        
        # 메뉴 설정 기본값으로 복원
        config["menu_settings"] = DEFAULT_MENU_SETTINGS
        save_config(config)
        
        logger.info("메뉴 설정 초기화 완료")
        return {
            "success": True, 
            "message": "메뉴 설정이 기본값으로 복원되었습니다.",
            "reload": True  # 페이지 새로고침 필요
        }
    except Exception as e:
        logger.error(f"메뉴 설정 초기화 중 오류 발생: {str(e)}")
        return {"success": False, "message": f"메뉴 설정 초기화 중 오류가 발생했습니다: {str(e)}"}

# 라우터 내보내기
__all__ = ["router", "api_router"]