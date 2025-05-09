"""
인덱싱 라우트 모듈

미디어 파일 인덱싱 관련 API 엔드포인트를 정의합니다.
"""

from fastapi import APIRouter, HTTPException, Request, BackgroundTasks, Query, Body
from fastapi.responses import HTMLResponse, JSONResponse
from typing import Dict, Any, Optional
from fastapi.templating import Jinja2Templates
from pathlib import Path
from datetime import datetime
import logging

from app.services.indexer import indexer_service
from app.database import db
from app.config import config
from app.utils.logging import get_indexer_logger

# 로거 설정
logger = get_indexer_logger()

# 라우터 생성
router = APIRouter(prefix="/api", tags=["indexing"])

# 템플릿 설정
templates = Jinja2Templates(directory="templates")


@router.get("/db/info")
async def get_db_info():
    """
    데이터베이스 정보를 반환합니다.
    
    Returns:
        Dict[str, Any]: 데이터베이스 정보
    """
    try:
        from app.database.connection import get_db_path, fetch_one
        
        # 데이터베이스 버전 정보
        version_result = fetch_one("SELECT sqlite_version()")
        version = version_result["sqlite_version()"] if version_result else "Unknown"
        
        # 테이블 개수
        table_result = fetch_one("SELECT count(*) as count FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        table_count = table_result["count"] if table_result else 0
        
        # 인덱스 개수
        index_result = fetch_one("SELECT count(*) as count FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'")
        index_count = index_result["count"] if index_result else 0
        
        # 데이터베이스 파일 경로
        db_path = str(get_db_path())
        
        # 데이터베이스 파일 크기
        try:
            import os
            file_size = os.path.getsize(db_path)
            # 크기 포맷팅 (MB)
            if file_size > 1024 * 1024:
                formatted_size = f"{file_size / (1024 * 1024):.2f} MB"
            elif file_size > 1024:
                formatted_size = f"{file_size / 1024:.2f} KB"
            else:
                formatted_size = f"{file_size} bytes"
        except Exception:
            formatted_size = "Unknown"
        
        # 데이터베이스 통계
        stats = {
            "version": version,
            "table_count": table_count,
            "index_count": index_count,
            "path": db_path,
            "size": formatted_size,
            "last_modified": None
        }
        
        # 마지막 수정 시간 추가
        try:
            import os
            import datetime
            mtime = os.path.getmtime(db_path)
            last_modified = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
            stats["last_modified"] = last_modified
        except Exception:
            pass
        
        return stats
    except Exception as e:
        return {"error": str(e)}


@router.get("/db/stats")
async def get_db_stats():
    """
    데이터베이스 테이블의 통계 정보를 반환합니다.
    
    Returns:
        Dict[str, Any]: 테이블별 통계 정보
    """
    try:
        from app.database.connection import fetch_one, fetch_all
        from app.database import subtitles, media
        
        # 자막 테이블 통계
        subtitle_count = subtitles.get_subtitle_count()
        
        # 미디어 파일 통계
        media_count = media.get_total_media_count()
        
        # 자막이 있는 미디어 파일 수
        media_with_subtitles = subtitles.get_media_with_subtitles_count()
        
        # 자막 없는 미디어 파일 수
        media_without_subtitles = media_count - media_with_subtitles
        
        # 테이블별 행 수 통계
        tables = fetch_all("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
        """)
        
        table_stats = []
        for table in tables:
            table_name = table["name"]
            row_count_result = fetch_one(f"SELECT COUNT(*) as count FROM {table_name}")
            row_count = row_count_result["count"] if row_count_result else 0
            
            # 테이블 크기 추정 (총 행 수 * 100 바이트 추정)
            estimated_size = row_count * 100
            if estimated_size > 1024 * 1024:
                size_str = f"{estimated_size / (1024 * 1024):.2f} MB"
            elif estimated_size > 1024:
                size_str = f"{estimated_size / 1024:.2f} KB"
            else:
                size_str = f"{estimated_size} bytes"
                
            table_stats.append({
                "name": table_name,
                "row_count": row_count,
                "estimated_size": size_str
            })
        
        # 자막 문장 길이 통계
        length_stats = fetch_all("""
            SELECT 
                CASE 
                    WHEN length(content) <= 50 THEN '0-50' 
                    WHEN length(content) <= 100 THEN '51-100' 
                    WHEN length(content) <= 150 THEN '101-150' 
                    WHEN length(content) <= 200 THEN '151-200' 
                    ELSE '200+' 
                END as length_range, 
                COUNT(*) as count 
            FROM subtitles 
            GROUP BY length_range 
            ORDER BY 
                CASE length_range 
                    WHEN '0-50' THEN 1 
                    WHEN '51-100' THEN 2 
                    WHEN '101-150' THEN 3 
                    WHEN '151-200' THEN 4 
                    ELSE 5 
                END
        """)
        
        # FTS 인덱스 상태 확인
        fts_count_result = fetch_one("SELECT COUNT(*) as count FROM subtitles_fts")
        fts_count = fts_count_result["count"] if fts_count_result else 0
        
        fts_status = {
            "indexed_count": fts_count,
            "total_count": subtitle_count,
            "is_synced": fts_count == subtitle_count,
            "sync_percentage": round((fts_count / subtitle_count) * 100, 2) if subtitle_count > 0 else 100
        }
        
        return {
            "subtitle_count": subtitle_count,
            "media_count": media_count,
            "media_with_subtitles": media_with_subtitles,
            "media_without_subtitles": media_without_subtitles,
            "table_stats": table_stats,
            "length_stats": length_stats,
            "fts_status": fts_status
        }
    except Exception as e:
        return {"error": str(e)}

@router.get("/db/tables")
async def get_db_tables():
    """
    데이터베이스의 테이블 목록을 반환합니다.
    
    Returns:
        List[Dict[str, Any]]: 테이블 목록 (이름, 타입, 행 수 등 포함)
    """
    from app.database.schema import get_table_list
    return get_table_list()


@router.get("/db/table/{table_name}")
async def get_db_table_data(table_name: str, limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0)):
    """
    지정된 테이블의 데이터를 조회합니다.
    
    Args:
        table_name: 조회할 테이블 이름
        limit: 조회할 최대 행 수 (기본값: 100, 최대: 1000)
        offset: 조회 시작 위치 (기본값: 0)
        
    Returns:
        Dict[str, Any]: 테이블 구조와 데이터
    """
    from app.database.schema import get_table_data
    return get_table_data(table_name, limit, offset)


@router.get("/indexing/status", response_model=Dict[str, Any])
async def get_indexing_status():
    """
    현재 인덱싱 상태를 반환합니다.
    
    Returns:
        Dict[str, Any]: 인덱싱 상태 정보
    """
    return indexer_service.get_status()


# 이전 API 경로 호환성 유지를 위한 엔드포인트 추가
@router.get("/indexing_status", response_model=Dict[str, Any])
async def get_indexing_status_legacy():
    """
    이전 버전 호환성을 위한 인덱싱 상태 API
    
    Returns:
        Dict[str, Any]: 인덱싱 상태 정보
    """
    return indexer_service.get_status()


@router.post("/indexing/start")
async def start_indexing(
    incremental: bool = False
):
    """
    인덱싱 작업을 시작합니다.
    
    Args:
        incremental: 증분 인덱싱 모드 (기본값: False)
        
    Returns:
        Dict[str, Any]: 인덱싱 시작 상태 정보
    """
    # 인덱싱 시작
    result = indexer_service.start_indexing(incremental)
    
    return {
        "success": True,
        "message": "인덱싱이 시작되었습니다.",
        "status": indexer_service.get_status()
    }


@router.post("/indexing/stop")
async def stop_indexing():
    """
    인덱싱 작업을 중지합니다.
    
    Returns:
        Dict[str, Any]: 인덱싱 중지 상태 정보
    """
    return indexer_service.stop_indexing()


@router.post("/indexing/pause")
async def pause_indexing():
    """
    인덱싱 작업을 일시정지합니다.
    
    Returns:
        Dict[str, Any]: 인덱싱 일시정지 상태 정보
    """
    return indexer_service.pause_indexing()


@router.post("/indexing/resume")
async def resume_indexing():
    """
    일시정지된 인덱싱 작업을 재개합니다.
    
    Returns:
        Dict[str, Any]: 인덱싱 재개 상태 정보
    """
    return {
        "success": True,
        "message": "인덱싱이 재개되었습니다.",
        "status": indexer_service.resume_indexing()
    }


@router.get("/indexing/progress", response_class=HTMLResponse)
async def get_indexing_progress():
    """
    인덱싱 진행률을 HTML 형식으로 반환합니다.
    
    Returns:
        HTMLResponse: HTML 형식의 인덱싱 진행률
    """
    status = indexer_service.get_status()
    
    # 인덱싱 상태 분류
    is_indexing = status.get("is_indexing", False)
    is_paused = status.get("is_paused", False)
    
    # 진행률 계산
    processed = status.get("processed_files", 0)
    total = status.get("total_files", 0)
    progress = 0
    if total > 0:
        progress = int((processed / total) * 100)
    
    # 현재 파일 정보
    current_file = status.get("current_file", "")
    subtitle_count = status.get("subtitle_count", 0)
    last_updated = status.get("last_updated", None)
    
    # 자막이 있는 미디어 수 및 비율 계산
    try:
        # 새로운 모듈화된 데이터베이스 접근 방식 사용
        from app.database import db
        from app.database.media import get_total_media_count
        from app.database.subtitles import get_media_with_subtitles_count
        
        # 자막이 있는 미디어 파일 수
        media_with_subtitles = get_media_with_subtitles_count()
        # 전체 미디어 파일 수
        total_media = get_total_media_count()
        
        # 자막이 있는 미디어 비율 계산
        media_with_subtitles_ratio = 0
        if total_media > 0:
            media_with_subtitles_ratio = round((media_with_subtitles / total_media) * 100)
    except:
        media_with_subtitles = 0
        total_media = 0
        media_with_subtitles_ratio = 0
    
    # 상태 클래스 결정
    status_class = "status-idle"
    status_text = "대기 중"
    status_icon = "<svg xmlns=\"http://www.w3.org/2000/svg\" class=\"h-5 w-5 mr-1\" viewBox=\"0 0 20 20\" fill=\"currentColor\"><path fill-rule=\"evenodd\" d=\"M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z\" clip-rule=\"evenodd\" /></svg>"
    
    # 인덱싱 상태에 따른 표시 정보 설정
    if is_indexing:
        if is_paused:
            status_class = "status-paused"
            status_text = "일시정지됨"
            status_icon = "<svg xmlns=\"http://www.w3.org/2000/svg\" class=\"h-5 w-5 mr-1\" viewBox=\"0 0 20 20\" fill=\"currentColor\"><path fill-rule=\"evenodd\" d=\"M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z\" clip-rule=\"evenodd\" /></svg>"
        else:
            status_class = "status-running"
            status_text = "진행 중"
            status_icon = "<svg xmlns=\"http://www.w3.org/2000/svg\" class=\"h-5 w-5 mr-1\" viewBox=\"0 0 20 20\" fill=\"currentColor\"><path fill-rule=\"evenodd\" d=\"M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z\" clip-rule=\"evenodd\" /></svg>"
    elif processed > 0 and processed >= total and total > 0:
        status_class = "status-completed"
        status_text = "완료됨"
        status_icon = "<svg xmlns=\"http://www.w3.org/2000/svg\" class=\"h-5 w-5 mr-1\" viewBox=\"0 0 20 20\" fill=\"currentColor\"><path fill-rule=\"evenodd\" d=\"M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z\" clip-rule=\"evenodd\" /></svg>"
    
    # 인덱싱이 중단되었는지 확인 (진행률이 100%가 아니고 인덱싱이 중지된 경우)
    if not is_indexing and processed > 0 and processed < total:
        status_class = "status-idle"
        status_text = "중단됨"
        status_icon = "<svg xmlns=\"http://www.w3.org/2000/svg\" class=\"h-5 w-5 mr-1\" viewBox=\"0 0 20 20\" fill=\"currentColor\"><path fill-rule=\"evenodd\" d=\"M10 18a8 8 0 100-16 8 8 0 000 16zM8 7a1 1 0 00-1 1v4a1 1 0 001 1h4a1 1 0 001-1V8a1 1 0 00-1-1H8z\" clip-rule=\"evenodd\" /></svg>"
    
    # ETA(예상 완료 시간) 정보
    eta = status.get("eta", "")
    eta_text = f"(완료 예상: {eta})" if eta and is_indexing and not is_paused else ""
    
    # 마지막 업데이트 시간 표시
    last_updated_text = ""
    if last_updated:
        from datetime import datetime
        try:
            # 마지막 업데이트 시간을 표시형식으로 변환
            if isinstance(last_updated, str):
                last_updated = datetime.fromisoformat(last_updated)
            last_updated_str = last_updated.strftime("%Y-%m-%d %H:%M:%S")
            last_updated_text = f"<div class=\"text-xs text-gray-500 mt-1\">마지막 업데이트: {last_updated_str}</div>"
        except Exception:
            pass
    
    # 완료 상태일 때 추가 안내 메시지
    completion_message = ""
    if status_class == "status-completed":
        completion_message = f"""
        <div class="mt-3 p-3 bg-green-50 border border-green-200 rounded-md">
            <div class="flex items-center text-green-800">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                </svg>
                <span class="font-medium">인덱싱이 성공적으로 완료되었습니다!</span>
            </div>
            <p class="text-sm text-green-700 mt-1">이제 검색 페이지에서 자막을 검색할 수 있습니다.</p>
        </div>
        """
    elif status_class == "status-idle" and status_text == "중단됨":
        completion_message = f"""
        <div class="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
            <div class="flex items-center text-yellow-800">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
                </svg>
                <span class="font-medium">인덱싱이 중단되었습니다.</span>
            </div>
            <p class="text-sm text-yellow-700 mt-1">인덱싱을 다시 시작하려면 아래 '인덱싱 시작' 버튼을 클릭하세요.</p>
        </div>
        """
    
    # 숫자 의미 설명이 포함된 인덱싱 상태 섹션 - 사용자 요청에 맞게 명확하게 설명 추가
    indexing_stats_explanation = f"""
    <div class="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-md">
        <h4 class="font-medium text-blue-800 mb-2">인덱싱 상태 설명</h4>
        <ul class="text-sm text-blue-700 space-y-1">
            <li><span class="font-semibold">전체 발견된 파일 수</span>: {total}개 (미디어 파일 전체 수)</li>
            <li><span class="font-semibold">처리 완료된 파일 수</span>: {processed}개 (인덱싱이 완료된 미디어 파일 수)</li>
            <li><span class="font-semibold">처리율</span>: {progress}% (전체 대비 처리 완료 비율)</li>
            <li><span class="font-semibold">자막이 있는 미디어의 처리율</span>: {media_with_subtitles_ratio}% ({media_with_subtitles}/{total_media})</li>
            <li><span class="font-semibold">처리된 자막 항목 수</span>: {subtitle_count}개 (데이터베이스에 저장된 개별 자막 항목 수)</li>
        </ul>
    </div>
    """
    
    # HTML 생성
    html = f"""
    <div class="indexing-status-card {status_class} mb-4">
        <div class="flex justify-between items-center mb-2">
            <h3 class="font-semibold text-lg flex items-center">
                {status_icon}
                인덱싱 상태: {status_text}
            </h3>
            <span class="text-sm">{processed}/{total} 파일 처리됨 {eta_text}</span>
        </div>
        
        <div class="progress-bar">
            <div class="progress-value" style="width: {progress}%"></div>
        </div>
        
        <div class="mt-3 text-sm">
            <div class="flex justify-between text-gray-600">
                <span>처리된 자막: {subtitle_count}개</span>
                <span>진행률: {progress}%</span>
            </div>
            
            {f'<div class="mt-1 overflow-hidden text-ellipsis whitespace-nowrap">현재 파일: <span class="font-mono">{current_file}</span></div>' if current_file and is_indexing else ''}
            {last_updated_text}
        </div>
        
        {indexing_stats_explanation}
        {completion_message}
    </div>
    """
    
    return HTMLResponse(html)

@router.get("/indexing/logs", response_class=HTMLResponse)
async def get_indexing_logs():
    """
    인덱싱 로그를 HTML 형식으로 반환합니다.
    
    Returns:
        HTMLResponse: HTML 형식의 인덱싱 로그
    """
    status = indexer_service.get_status()
    logs = status.get("log_messages", [])
    
    # 로그가 없는 경우
    if not logs:
        return HTMLResponse(
            """<div class="text-center p-4">
                <p class="text-gray-400">로그가 없습니다.</p>
            </div>"""
        )
    
    # 로그를 HTML로 포맷팅
    html = "<div class='space-y-1'>\n"
    
    for i, log in enumerate(logs):
        # 로그 레벨에 따른 스타일 적용 (어두운 배경에 맞게 조정)
        log_class = "text-gray-300"  # 기본 스타일
        
        if "ERROR" in log:
            log_class = "text-red-400 font-semibold"
            prompt_color = "text-red-400"
        elif "WARNING" in log:
            log_class = "text-yellow-300"
            prompt_color = "text-yellow-300"
        elif "INFO" in log:
            log_class = "text-cyan-300"
            prompt_color = "text-cyan-300"
        elif "DEBUG" in log:
            log_class = "text-green-300"
            prompt_color = "text-green-300"
        else:
            prompt_color = "text-gray-500"
        
        # 줄 번호와 터미널 프롬프트 추가
        line_number = f"{i+1:02d}"
        
        # 로그 항목 HTML 생성
        html += f'''<div class="log-line {log_class} text-sm font-mono flex">
                      <span class="text-gray-500 mr-2">[{line_number}]</span>
                      <span class="{prompt_color} mr-2">$</span>
                      <span class="flex-1">{log}</span>
                   </div>\n'''
    
    html += "</div>"
    
    return HTMLResponse(html)

@router.post("/settings/retry", response_model=Dict[str, Any])
async def update_retry_settings(
    retry_count: int = Body(..., description="최대 재시도 횟수", ge=0, le=10),
    retry_interval: int = Body(..., description="재시도 간격(초)", ge=5, le=60),
    auto_restart: bool = Body(..., description="자동 재시작 활성화 여부")
):
    """
    인덱서 재시도 관련 설정을 업데이트합니다.
    
    Args:
        retry_count: 최대 재시도 횟수 (0~10)
        retry_interval: 재시도 간격(초) (5~60)
        auto_restart: 자동 재시작 활성화 여부
        
    Returns:
        Dict[str, Any]: 업데이트된 설정 정보
    """
    # 설정 업데이트
    config.set("indexer_retry_count", retry_count)
    config.set("indexer_retry_interval", retry_interval)
    config.set("auto_restart_indexing", auto_restart)
    
    # 현재 설정 반환
    return {
        "indexer_retry_count": config.get("indexer_retry_count"),
        "indexer_retry_interval": config.get("indexer_retry_interval"),
        "auto_restart_indexing": config.get("auto_restart_indexing"),
        "success": True,
        "message": "인덱서 재시도 설정이 업데이트되었습니다."
    }

@router.get("/settings/retry", response_model=Dict[str, Any])
async def get_retry_settings():
    """
    인덱서 재시도 관련 설정을 조회합니다.
    
    Returns:
        Dict[str, Any]: 현재 설정 정보
    """
    return {
        "indexer_retry_count": config.get("indexer_retry_count", 3),
        "indexer_retry_interval": config.get("indexer_retry_interval", 10),
        "auto_restart_indexing": config.get("auto_restart_indexing", False)  # 기본값을 False로 변경
    }

# 인덱싱 필터 페이지 라우트 추가
@router.get("/filter", response_class=HTMLResponse, tags=["pages"])
async def indexing_filter(request: Request):
    """
    인덱싱 필터 페이지를 표시합니다.
    
    Args:
        request: FastAPI Request 객체
        
    Returns:
        HTMLResponse: 인덱싱 필터 HTML 페이지
    """
    # 인덱싱 상태 정보 가져오기
    status = indexer_service.get_status()
    
    # DB에서 언어별 자막 개수 가져오기
    language_stats = db.get_language_stats() if db else {"en": 271288}
    
    # 처리된 파일 목록 가져오기 (최대 100개 가져오기)
    processed_files = db.get_processed_files(limit=100) if db else []
    
    return templates.TemplateResponse("indexing_filter.html", {
        "request": request,
        "status": status,
        "language_stats": language_stats,
        "processed_files": processed_files
    })

@router.post("/db/reset")
async def reset_database():
    """
    데이터베이스를 완전히 초기화합니다 (모든 데이터 삭제).
    이 작업은 되돌릴 수 없습니다.
    
    Returns:
        Dict[str, Any]: 초기화 결과
    """
    try:
        # 인덱싱 중지
        indexer_service.stop_indexing()
        
        # 데이터베이스 초기화 - 리팩토링된 모듈화 구조 사용
        from app.database.schema import reset_database
        success = reset_database()
        
        if success:
            return {
                "status": "success",
                "message": "데이터베이스가 성공적으로 초기화되었습니다.",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        else:
            return {
                "status": "error",
                "message": "데이터베이스 초기화 중 오류가 발생했습니다.",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
    except Exception as e:
        logger.error(f"데이터베이스 초기화 중 오류: {e}")
        return {
            "status": "error",
            "message": f"데이터베이스 초기화 중 오류: {str(e)}",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }


@router.post("/db/rebuild-fts")
async def rebuild_fts_index(force: bool = Body(False, description="FTS 인덱스를 강제로 재구축할지 여부")):
    """
    FTS(Full-Text Search) 인덱스를 재구축합니다.
    
    Args:
        force: 기존 인덱스를 모두 제거하고 새로 구축할지 여부
        
    Returns:
        Dict[str, Any]: 재구축 결과
    """
    try:
        # FTS 인덱스 재구축 실행 - 리팩토링된 모듈화 구조 사용
        from app.database.subtitles import rebuild_fts_index as db_rebuild_fts_index
        
        success = db_rebuild_fts_index(force=force)
        
        if success:
            # 성공 시 최신 상태 확인 - 리팩토링된 모듈화 구조 사용
            from app.database.subtitles import get_subtitle_count
            from app.database.connection import get_connection, fetch_one
            
            # 자막 테이블 레코드 수 가져오기
            subtitle_count = get_subtitle_count()
            
            # FTS 테이블 레코드 수 가져오기
            fts_count_result = fetch_one("SELECT COUNT(*) as count FROM subtitles_fts")
            fts_count = fts_count_result["count"] if fts_count_result else 0
            
            return {
                "success": True,
                "message": "FTS 인덱스 재구축 완료",
                "fts_count": fts_count,
                "subtitle_count": subtitle_count,
                "is_synced": fts_count == subtitle_count,
                "sync_percentage": round((fts_count / subtitle_count) * 100, 2) if subtitle_count > 0 else 100
            }
        else:
            return {
                "success": False,
                "message": "FTS 인덱스 재구축 실패"
            }
    except Exception as e:
        return {
            "success": False,
            "message": f"FTS 인덱스 재구축 중 오류 발생: {str(e)}"
        }