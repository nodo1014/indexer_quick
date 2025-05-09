"""
전체 구조는 `project_structure.txt` 참조. 구조가 바뀐 경우 project_structure.txt를 수정해주세요.
구조화 원칙 (AI 및 협업자용):
- routes/: 직접 DB 접근 금지 → 반드시 services 또는 db 모듈 경유
- subtitle/: SRT, VTT 등 포맷 파싱 및 변환만 담당
- database/: 모든 DB 함수는 이곳에 집중
- main.py는 FastAPI 앱 진입점으로 라우터와 초기화 코드만 포함
"""

from fastapi import FastAPI, Request, Depends, Form, Body
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import os
import logging
from typing import Dict, Any, Optional
from starlette.middleware.sessions import SessionMiddleware

# 내부 모듈 임포트
from app.config import config, get_config, load_config
from app.database import db
from app.database.schema import init_db
from app.database.connection import get_connection, close_connection  # 풀링 제거, 단일 연결 함수로 변경
from app.routes import search, stats, indexing, settings, database  # database 라우트 추가
from app.routes import docs  # 문서 라우터 추가
from app.services.indexer import indexer_service


# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("app")

# 자동 작업 비활성화 설정 (개발 모드에서 사용)
DISABLE_AUTO_TASKS = True  # 자동 워치독, 인덱싱 등 무거운 작업 실행 여부

# FastAPI 애플리케이션 생성
app = FastAPI(
    title="Media Indexer API",
    description="미디어 파일과 자막을 관리하는 API",
    version="1.0.0",
    docs_url=None,  # API 문서 페이지 비활성화
    redoc_url=None,  # ReDoc 페이지 비활성화
    openapi_url=None  # OpenAPI 스키마 비활성화
)

# 세션 미들웨어 추가 (설정 저장 등에 필요)
app.add_middleware(SessionMiddleware, secret_key="some-random-string-for-sessions")

# 기본 경로 설정
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

# 정적 파일 및 템플릿 설정
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# 메뉴 설정을 모든 템플릿에 제공하는 컨텍스트 프로세서
@app.middleware("http")
async def add_template_context(request: Request, call_next):
    """모든 템플릿에 공통 컨텍스트를 추가하는 미들웨어"""
    # 설정 데이터 가져오기
    config_data = get_config()
    
    # 메뉴 설정 추가
    menu_settings = config_data.get("menu_settings", {})
    request.state.menu_settings = menu_settings
    
    # 추가 컨텍스트 데이터 설정
    request.state.app_version = app.version
    request.state.config = config_data
    
    # 원본 핸들러 호출
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        logger.error(f"요청 처리 중 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise

# 라우터 등록
app.include_router(search.router)
app.include_router(stats.router)
app.include_router(indexing.router)
app.include_router(settings.router)  # 설정 페이지 라우터 등록
app.include_router(settings.api_router)  # 설정 API 라우터 등록

# 데이터베이스 관리 라우터 등록
app.include_router(database.router)

# 문서 라우터 등록
app.include_router(docs.router)


@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 실행할 작업들"""
    try:
        # 데이터베이스 커넥션 초기화 (필수 기능이므로 항상 실행)
        conn = get_connection()
        logger.info("데이터베이스 연결이 초기화되었습니다.")
        
        # 데이터베이스 초기화 (필수 기능이므로 항상 실행)
        init_db()
        logger.info("데이터베이스가 성공적으로 초기화되었습니다.")
        

        
        # 무거운 자동 작업은 설정에 따라 선택적으로 실행
        if not DISABLE_AUTO_TASKS:
            # FTS 인덱스 상태 확인 및 필요시 복구
            logger.info("FTS 인덱스 상태 확인 중...")
            try:
                from app.services.indexer import update_fts_index
                update_result = update_fts_index(force=False)  # 필요한 경우에만 재구축
                if update_result:
                    logger.info("FTS 인덱스가 정상 상태입니다.")
                else:
                    logger.warning("FTS 인덱스 상태가 불안정합니다. 백그라운드에서 재구축이 필요할 수 있습니다.")
            except Exception as e:
                logger.error(f"FTS 인덱스 상태 확인 중 오류 발생: {e}")
            
            # 인덱서 초기화 상태 확인
            indexer_status = indexer_service.get_status()
            if indexer_status.get("is_indexing", False):
                logger.info("인덱싱 상태 확인 - 진행 중인 인덱싱이 있습니다.")
            else:
                logger.info("인덱싱 상태 확인 - 진행 중인 인덱싱이 없습니다.")
            

        else:
            logger.info("자동 워치독 및 무거운 작업이 비활성화되어 있습니다. 필요할 때 수동으로 활성화 가능합니다.")
        
    except Exception as e:
        logger.error(f"애플리케이션 시작 중 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())


@app.on_event("shutdown")
async def shutdown_event():
    """애플리케이션 종료 시 실행할 작업들"""
    try:
        # 데이터베이스 연결 종료
        close_connection()
        logger.info("데이터베이스 연결을 정상적으로 종료했습니다.")
        

        
    except Exception as e:
        logger.error(f"애플리케이션 종료 중 오류 발생: {e}")


@app.get("/", response_class=RedirectResponse)
async def read_root():
    """루트 페이지를 인덱싱 관리 페이지로 리다이렉트"""
    return "/indexing-process"


@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request):
    """검색 페이지 반환"""
    return templates.TemplateResponse(
        "search.html",
        {"request": request}
    )


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """대시보드 페이지 반환"""
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "config": config.data}
    )


# 설정 페이지는 이제 settings.py 모듈에서 처리합니다.


@app.post("/settings")
async def save_settings(
    request: Request,
    media_dir: str = Form(...),
    db_path: str = Form("media_index.db"),
    use_absolute_path: bool = Form(False),
    max_threads: Optional[int] = Form(None),
    media_extensions_hidden: str = Form(""),
    reset_db: str = Form("false"),
    indexing_strategy: str = Form("standard"),
    skip_db_reset_check: Optional[str] = Form(None)
):
    """
    설정 저장 엔드포인트
    
    폼에서 제출된 설정을 저장합니다.
    """
    try:
        # 폼 데이터 처리
        logger.info(f"설정 저장 요청 받음: media_dir={media_dir}, db_path={db_path}, media_extensions_hidden={media_extensions_hidden}")
        
        if media_extensions_hidden:
            media_extensions = media_extensions_hidden.split(",")
            logger.info(f"처리된 미디어 확장자: {media_extensions}")
        else:
            media_extensions = config.get("media_extensions", [])
            logger.info(f"미디어 확장자 값이 없어 기존 설정 사용: {media_extensions}")
        
        # 설정 업데이트
        config.update({
            "media_dir": media_dir,
            "db_path": db_path,
            "use_absolute_path": use_absolute_path,
            "max_threads": max_threads or config.get("max_threads", 4),
            "media_extensions": media_extensions,
            "indexing_strategy": indexing_strategy
        })
        
        # 설정 저장
        config.save()
        
        logger.info(f"설정이 성공적으로 저장되었습니다: {config.data}")
        return RedirectResponse(url="/settings", status_code=303)
        
    except Exception as e:
        logger.error(f"설정 저장 중 오류 발생: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@app.post("/api/index")
async def start_indexing(request: Request):
    """
    인덱싱 시작 API 엔드포인트
    
    인덱싱 프로세스를 시작합니다.
    """
    try:
        # JSON 데이터 직접 파싱
        data = await request.json()
        incremental = data.get("incremental", True)
        reset_db = data.get("reset_db", False)
        
        logger.info(f"인덱싱 요청 받음: incremental={incremental}, reset_db={reset_db}")
        
        # 인덱싱 시작
        if reset_db:
            logger.info("DB 초기화 요청으로 데이터베이스를 초기화합니다.")
            db.reset_database()
        
        result = indexer_service.start_indexing(incremental=incremental)
        
        return {
            "success": True,
            "message": "인덱싱이 시작되었습니다.",
            "status": indexer_service.get_status()
        }
        
    except Exception as e:
        logger.error(f"인덱싱 시작 중 오류 발생: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@app.get("/indexing-process", response_class=HTMLResponse)
async def indexing_process_page(request: Request):
    """인덱싱 프로세스 페이지 반환"""
    return templates.TemplateResponse(
        "indexing_process.html",
        {
            "request": request, 
            "config": config.data,
            "status": indexer_service.get_status()
        }
    )


@app.get("/indexing-filter", response_class=HTMLResponse) 
async def indexing_filter_page(request: Request):
    """인덱싱 필터 페이지 반환"""
    # 인덱싱 상태 정보 가져오기
    status = indexer_service.get_status()
    
    # DB에서 언어별 자막 개수 가져오기
    language_stats = db.get_language_stats()
    
    # 처리된 파일 목록 가져오기 (최대 100개)
    processed_files = db.get_processed_files(limit=100)
    
    return templates.TemplateResponse(
        "indexing_filter.html",
        {
            "request": request,
            "config": config.data,
            "status": status,
            "language_stats": language_stats,
            "processed_files": processed_files
        }
    )


# 데이터베이스 관리 페이지 기능 제거


# AI 인터페이스 페이지 라우트 추가
@app.get("/ai-prompt", response_class=HTMLResponse)
async def ai_prompt_page(request: Request):
    """AI 인터페이스 페이지 반환"""
    return templates.TemplateResponse(
        "ai_interface.html",
        {"request": request, "config": config.data}
    )


# AI 인터페이스 API 엔드포인트 추가
@app.get("/api/ai-prompt", response_class=JSONResponse)
async def ai_prompt_api():
    """AI 프롬프트 데이터를 JSON 형식으로 반환"""
    try:
        # ai_prompt.md 파일에서 내용 읽기
        ai_prompt_path = BASE_DIR / "ai_prompt.md" 
        with open(ai_prompt_path, "r", encoding="utf-8") as f:
            prompt_content = f.read()
            
        return {
            "success": True,
            "content": prompt_content,
            "timestamp": str(config.data.get("last_scan_time", ""))
        }
    except Exception as e:
        logger.error(f"AI 프롬프트 로딩 오류: {e}")
        return {
            "success": False,
            "error": f"AI 프롬프트를 로드할 수 없습니다: {str(e)}"
        }


# AI 시스템 정보 API 엔드포인트 추가
@app.get("/api/ai/system_info", response_class=JSONResponse)
async def ai_system_info():
    """AI 분석을 위한 시스템 정보를 JSON 형식으로 반환"""
    try:
        # 데이터베이스 통계 가져오기
        from app.services.stats import stats_service
        system_stats = stats_service.get_system_stats()
        media_stats = stats_service.get_media_stats()
        subtitle_stats = stats_service.get_subtitle_stats()
        
        # 인덱싱 상태 가져오기
        indexing_status = indexer_service.get_status()
        
        # 데이터베이스 스키마 정보
        db_schema = {
            "tables": [
                {
                    "name": "media_files",
                    "columns": ["id", "path", "filename", "extension", "size", "created_at", "modified_at", "duration", "has_subtitle"],
                    "primary_key": "id"
                },
                {
                    "name": "subtitles",
                    "columns": ["id", "media_id", "text", "start_time", "end_time", "language", "created_at"],
                    "primary_key": "id",
                    "foreign_keys": [
                        {"column": "media_id", "references": "media_files.id"}
                    ]
                }
            ]
        }
        
        # 파일 확장자별 통계
        extension_stats = {}
        if media_stats.get("extensions"):
            extension_stats = media_stats["extensions"]
        
        # 응답 데이터 구성
        response_data = {
            "config": {
                "root_directory": config.get("root_dir", ""),
                "database_path": config.get("db_path", "media_index.db"),
                "media_extensions": config.get("media_extensions", [".mp4", ".mkv", ".avi"]),
                "indexing_strategy": config.get("indexing_strategy", "standard"),
                "max_threads": config.get("max_threads", 4)
            },
            "indexing": {
                "is_active": indexing_status.get("is_indexing", False),
                "is_paused": indexing_status.get("is_paused", False),
                "current_operation": indexing_status.get("current_file", ""),
                "progress": indexing_status.get("processed_files", 0) / max(indexing_status.get("total_files", 1), 1),
                "started_at": indexing_status.get("start_time", ""),
                "estimated_completion": indexing_status.get("eta", "")
            },
            "database_schema": db_schema,
            "statistics": {
                "media_files": {
                    "total_count": media_stats.get("total", 0),
                    "with_subtitles": media_stats.get("with_subtitles", 0),
                    "without_subtitles": media_stats.get("without_subtitles", 0),
                    "subtitle_coverage_percentage": media_stats.get("subtitle_coverage_percent", 0)
                },
                "subtitles": {
                    "total_entries": subtitle_stats.get("total", 0),
                    "language_distribution": subtitle_stats.get("languages", {})
                },
                "file_extensions": extension_stats,
                "subtitle_length_distribution": {
                    "Short (1-10 words)": subtitle_stats.get("length_short", 0),
                    "Medium (11-50 words)": subtitle_stats.get("length_medium", 0),
                    "Long (50+ words)": subtitle_stats.get("length_long", 0)
                }
            }
        }
        
        return response_data
        
    except Exception as e:
        logger.error(f"AI 시스템 정보 로딩 오류: {e}")
        return {
            "error": f"시스템 정보를 로드할 수 없습니다: {str(e)}",
            "config": {
                "media_directory": config.get("root_dir", ""),
                "database_path": config.get("db_path", "media_index.db"),
                "media_extensions": config.get("media_extensions", [".mp4", ".mkv", ".avi"]),
                "indexing_strategy": config.get("indexing_strategy", "standard"),
                "max_threads": config.get("max_threads", 4)
            },
            "indexing": {
                "is_active": False,
                "current_operation": "",
                "progress": 0,
                "started_at": "",
                "estimated_completion": ""
            }
        }


@app.get("/health")
async def health_check():
    """애플리케이션 상태 확인 API"""
    return {
        "status": "ok",
        "version": app.version,
        "database_connected": True,
        "indexing_active": indexer_service.get_status().get("is_indexing", False)
    }


@app.get("/api/browse", response_class=HTMLResponse)
async def browse_directory(request: Request, path: Optional[str] = None):
    """
    디렉토리 브라우징 API 엔드포인트
    
    지정된 경로의 디렉토리 내용을 HTML 형식으로 반환합니다.
    path가 없으면 루트 디렉토리 목록을 반환합니다.
    """
    try:
        import os
        from pathlib import Path
        
        # 경로가 지정되지 않은 경우 루트 디렉토리 목록 제공
        if not path:
            if os.name == "posix":  # macOS/Linux
                directory_list = [
                    {"name": "/", "path": "/", "is_dir": True},
                    {"name": "홈", "path": str(Path.home()), "is_dir": True}
                ]
                
                # 볼륨 목록 추가 (macOS)
                volumes_path = "/Volumes"
                if os.path.exists(volumes_path):
                    for volume in os.listdir(volumes_path):
                        volume_path = os.path.join(volumes_path, volume)
                        if os.path.isdir(volume_path):
                            directory_list.append({
                                "name": volume, 
                                "path": volume_path, 
                                "is_dir": True
                            })
            else:  # Windows
                import string
                drives = [f"{d}:\\" for d in string.ascii_uppercase if os.path.exists(f"{d}:")]
                directory_list = [{"name": d, "path": d, "is_dir": True} for d in drives]
            
            # HTML 렌더링
            directory_html = """
            <div class="directory-list">
                <h3 class="text-lg font-semibold mb-2">루트 디렉토리 선택</h3>
                <div class="space-y-2">
            """
            
            for item in directory_list:
                directory_html += f"""
                <div class="directory-item hover:bg-blue-50 p-2 rounded cursor-pointer flex items-center"
                     data-path="{item['path']}">
                    <svg class="w-5 h-5 mr-2 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                              d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"></path>
                    </svg>
                    <span>{item['name']}</span>
                </div>
                """
            
            directory_html += """
                </div>
            </div>
            """
            
            return HTMLResponse(directory_html)
            
        # 실제 경로 확인
        target_path = Path(path)
        if not target_path.exists() or not target_path.is_dir():
            return HTMLResponse(
                """<div class="text-red-500 p-4">디렉토리가 존재하지 않거나 접근할 수 없습니다.</div>"""
            )
        
        # 상위 디렉토리 경로 계산
        parent_dir = str(target_path.parent)
        if target_path == target_path.parent:  # 루트 디렉토리인 경우
            parent_dir = None
        
        # 디렉토리 내용 가져오기
        directory_items = []
        for item in target_path.iterdir():
            if item.is_dir():  # 디렉토리만 포함
                directory_items.append({
                    "name": item.name,
                    "path": str(item),
                    "is_dir": True
                })
        
        # 알파벳순 정렬
        directory_items.sort(key=lambda x: x["name"].lower())
        
        # HTML 렌더링
        directory_html = f"""
        <div class="directory-browser">
            <div class="current-path-display mb-4">
                <div class="current-path bg-gray-100 p-2 rounded text-sm font-mono mb-2" data-path="{path}">
                    현재 경로: {path}
                </div>
        """
        
        # 상위 디렉토리 버튼
        if parent_dir:
            directory_html += f"""
            <button class="parent-dir-btn bg-gray-200 hover:bg-gray-300 rounded px-3 py-1 text-sm flex items-center"
                    data-parent="{parent_dir}">
                <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path>
                </svg>
                상위 디렉토리
            </button>
            """
        
        # 디렉토리 선택 라디오 버튼
        directory_html += f"""
            <div class="mt-4 mb-2">
                <label class="flex items-center">
                    <input type="radio" name="selected_directory" value="{path}" class="mr-2">
                    <span class="font-medium">현재 디렉토리 선택하기</span>
                </label>
            </div>
        </div>
        """
        
        # 디렉토리 목록
        if directory_items:
            directory_html += """
            <div class="directory-list mt-4 space-y-1 max-h-60 overflow-y-auto border p-2 rounded">
            """
            
            for item in directory_items:
                directory_html += f"""
                <div class="directory-item hover:bg-blue-50 p-1.5 rounded cursor-pointer flex items-center"
                     data-path="{item['path']}">
                    <svg class="w-5 h-5 mr-2 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                              d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"></path>
                    </svg>
                    <span>{item['name']}</span>
                </div>
                """
            
            directory_html += """
            </div>
            """
        else:
            directory_html += """
            <div class="text-gray-500 p-4 text-center border rounded mt-2">
                이 디렉토리는 비어있거나 접근 가능한 하위 디렉토리가 없습니다.
            </div>
            """
        
        directory_html += """
        </div>
        """
        
        return HTMLResponse(directory_html)
        
    except Exception as e:
        logger.error(f"디렉토리 브라우징 오류: {e}")
        return HTMLResponse(
            f"""<div class="text-red-500 p-4">디렉토리 탐색 중 오류가 발생했습니다: {str(e)}</div>"""
        )


# favicon.ico 추가
@app.get('/favicon.ico', include_in_schema=False)
async def favicon():
    return FileResponse('static/favicon.ico')