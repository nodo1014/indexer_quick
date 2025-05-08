"""
인덱싱 라우트 모듈

미디어 파일 인덱싱 관련 API 엔드포인트를 정의합니다.
"""

from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from typing import Dict, Any, Optional

from app.services.indexer import indexer_service

# 라우터 생성
router = APIRouter(prefix="/api", tags=["indexing"])


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
async def start_indexing(incremental: bool = False, background_tasks: BackgroundTasks = None):
    """
    인덱싱 작업을 시작합니다.
    
    Args:
        incremental: 증분 인덱싱 모드 (기본값: False)
        
    Returns:
        Dict[str, Any]: 인덱싱 시작 상태 정보
    """
    return indexer_service.start_indexing(incremental)


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
    return indexer_service.resume_indexing()


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
                <p class="text-gray-500">로그가 없습니다.</p>
            </div>"""
        )
    
    # 로그를 HTML로 포맷팅
    log_html = """<div class="space-y-1 font-mono text-xs">"""
    
    for log in logs:
        # 로그 레벨에 따른 색상 지정
        if "ERROR" in log:
            log_class = "text-red-600"
        elif "WARNING" in log:
            log_class = "text-yellow-600"
        else:
            log_class = "text-gray-700"
        
        log_html += f"""<div class="{log_class}">{log}</div>"""
    
    log_html += """</div>"""
    return HTMLResponse(log_html)


@router.get("/indexing/progress", response_class=HTMLResponse)
async def get_indexing_progress():
    """
    인덱싱 진행 상황을 HTML 형식으로 반환합니다.
    
    Returns:
        HTMLResponse: HTML 형식의 인덱싱 진행 상황
    """
    status = indexer_service.get_status()
    
    # 인덱싱 중이 아닌 경우
    is_indexing = status.get("is_indexing", False)
    is_paused = status.get("is_paused", False)
    
    if not is_indexing and not is_paused:
        return HTMLResponse(
            """<div class="text-center p-4">
                <p class="text-gray-500">현재 진행 중인 인덱싱이 없습니다.</p>
            </div>"""
        )
    
    # 인덱싱 진행 상태 계산
    processed = status.get("processed_files", 0)
    total = status.get("total_files", 1)  # 0으로 나누기 방지
    subtitle_count = status.get("subtitle_count", 0)
    current_file = status.get("current_file", "")
    
    # 진행률 계산
    progress = min(100, int((processed / total) * 100)) if total > 0 else 0
    
    # 현재 파일 경로에서 파일명만 추출
    import os
    current_file_name = os.path.basename(current_file) if current_file else "준비 중..."
    
    # ETA 표시
    eta = status.get("eta", "계산 중...")
    
    # 상태에 따른 버튼 HTML
    if is_indexing:
        buttons_html = """
        <div class="flex space-x-2 mt-2">
            <button class="px-3 py-1 bg-yellow-500 hover:bg-yellow-600 text-white rounded text-sm"
                hx-post="/api/indexing/pause" hx-swap="none" hx-trigger="click"
                onclick="showToast('인덱싱이 일시정지되었습니다.')">
                일시정지
            </button>
            <button class="px-3 py-1 bg-red-500 hover:bg-red-600 text-white rounded text-sm"
                hx-post="/api/indexing/stop" hx-swap="none" hx-trigger="click"
                onclick="showToast('인덱싱이 중지되었습니다.')">
                중지
            </button>
        </div>
        """
    elif is_paused:
        buttons_html = """
        <div class="flex space-x-2 mt-2">
            <button class="px-3 py-1 bg-green-500 hover:bg-green-600 text-white rounded text-sm"
                hx-post="/api/indexing/resume" hx-swap="none" hx-trigger="click"
                onclick="showToast('인덱싱이 재개되었습니다.')">
                재개
            </button>
            <button class="px-3 py-1 bg-red-500 hover:bg-red-600 text-white rounded text-sm"
                hx-post="/api/indexing/stop" hx-swap="none" hx-trigger="click"
                onclick="showToast('인덱싱이 중지되었습니다.')">
                중지
            </button>
        </div>
        """
    else:
        buttons_html = ""
    
    # 진행 상황 HTML 생성
    status_text = "일시정지됨" if is_paused else "진행 중..."
    
    progress_html = f"""
    <div class="space-y-2">
        <div class="flex items-center justify-between">
            <span class="text-sm font-medium">진행 상황: {status_text}</span>
            <span class="text-sm text-gray-600">{progress}% ({processed}/{total})</span>
        </div>
        <div class="w-full bg-gray-200 rounded-full h-2.5">
            <div class="bg-blue-600 h-2.5 rounded-full" style="width: {progress}%"></div>
        </div>
        <div class="flex justify-between">
            <span class="text-xs text-gray-600">처리된 자막: {subtitle_count}개</span>
            <span class="text-xs text-gray-600">남은 시간: {eta}</span>
        </div>
        <div class="text-xs mt-1 text-gray-700 truncate" title="{current_file}">
            현재 파일: {current_file_name}
        </div>
        {buttons_html}
    </div>
    """
    
    return HTMLResponse(progress_html)