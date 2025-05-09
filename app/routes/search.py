"""
검색 라우트 모듈

자막 검색 관련 API 엔드포인트를 정의합니다.
"""

import logging
import subprocess
from fastapi import APIRouter, Query, HTTPException, Request, Body
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, StreamingResponse
from typing import Optional, List, Dict, Any
import os
import time  # time 모듈 추가 (export_search API에서 사용)
import urllib.parse  # URL 인코딩/디코딩에 사용

from app.services.search import search_service
from app.models.subtitle import SearchResult, SearchQuery
from app.database import db
from app.config import config  # config 모듈 임포트 추가

# 로거 설정
logger = logging.getLogger(__name__)

# 라우터 생성
router = APIRouter(prefix="/api", tags=["search"])


@router.get("/search")
async def search_subtitles(
    query: str,
    lang: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=1000),
    search_method: Optional[str] = None
):
    """
    자막을 검색하고 JSON 형식으로 결과를 반환합니다.
    
    Args:
        query: 검색할 텍스트
        lang: 언어 필터 (예: 'en', 'ko')
        start_time: 시작 시간 필터 (HH:MM:SS 형식)
        end_time: 종료 시간 필터 (HH:MM:SS 형식)
        page: 페이지 번호 (기본값: 1)
        per_page: 페이지당 결과 수 (기본값: 50)
        search_method: 검색 방식 ('like' 또는 'fts')
        
    Returns:
        JSONResponse: 검색 결과와 자막 정보
    """
    # 검색 방식이 지정되지 않은 경우 설정 파일의 기본값 사용
    if search_method not in ['like', 'fts']:
        search_method = config.get_default_search_method()
        
    logger.info(f"검색 요청 수신: query='{query}', lang={lang}, time={start_time}-{end_time}, search_method={search_method}")
    
    try:
        # 검색 서비스 호출 - database.subtitles 모듈 함수 사용
        from app.database.subtitles import search_subtitles as db_search_subtitles
        results = db_search_subtitles(
            query=query, 
            lang=lang, 
            start_time=start_time, 
            end_time=end_time, 
            page=page, 
            per_page=per_page
        )
        
        # 결과 로깅
        logger.info(f"검색 결과: {len(results)}개 찾음")
        
        # 자막 데이터를 그룹화하고 필요한 형식으로 변환
        media_files = {}
        filtered_results = []
        
        for sub in results:
            media_path = sub['media_path']
            
            # 실제 미디어 파일이 존재하는지 확인
            if not os.path.exists(media_path):
                logger.warning(f"미디어 파일이 존재하지 않음: {media_path}")
                continue
                
            filtered_results.append(sub)
            
            if media_path not in media_files:
                # 미디어 파일 경로를 스트리밍 API URL로 변환
                # URL 인코딩 처리 (슬래시는 보존)
                path_parts = []
                
                # 경로를 각 부분별로 인코딩하여 슬래시 구조 유지
                for part in media_path.split('/'):
                    if part:
                        path_parts.append(urllib.parse.quote(part))
                
                # 경로 재구성 (슬래시로 다시 연결)
                encoded_path = '/'.join(path_parts)
                if media_path.startswith('/'):
                    encoded_path = '/' + encoded_path
                
                # 스트리밍 URL 생성
                streaming_url = f"/api/media{encoded_path}"
                
                logger.info(f"스트리밍 URL 생성: {streaming_url} (원본 경로: {media_path})")
                
                media_files[media_path] = {
                    'mediaPath': media_path,  # 원본 경로 (클라이언트 참조용)
                    'streamingUrl': streaming_url,  # 스트리밍 URL (URL 인코딩 적용)
                    'fileName': os.path.basename(media_path),
                    'subtitles': []
                }
                
            # 자막 구조 변환 (프론트엔드에서 기대하는 형식으로)
            start_time_text = sub['start_time_text']
            if ',' in start_time_text:
                start_time_text = start_time_text.replace(',', '.')
            
            subtitle_item = {
                'en': sub['content'] if sub['lang'] == 'en' else '',
                'ko': sub['content'] if sub['lang'] == 'ko' else '',
                'time': start_time_text,
                'startTime': sub['start_time'] / 1000.0,  # 밀리초를 초로 변환
            }
            
            media_files[media_path]['subtitles'].append(subtitle_item)
        
        # 결과 포맷 정리
        formatted_results = list(media_files.values())
        
        # 필터링 결과 로그
        logger.info(f"필터링 후 결과: {len(filtered_results)}개 (실제 미디어 파일이 존재하는 자막)")
        
        return JSONResponse({
            "success": True,
            "results": formatted_results
        })
        
    except Exception as e:
        logger.error(f"검색 중 오류 발생: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"검색 중 오류가 발생했습니다: {str(e)}"}
        )


@router.get("/search/json", response_model=SearchResult)
async def search_subtitles_json(
    query: str,
    lang: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=1000)
):
    """
    자막을 검색하고 JSON 형식으로 결과를 반환합니다.
    
    Args:
        query: 검색할 텍스트
        lang: 언어 필터 (예: 'en', 'ko')
        start_time: 시작 시간 필터 (HH:MM:SS 형식)
        end_time: 종료 시간 필터 (HH:MM:SS 형식)
        page: 페이지 번호 (기본값: 1)
        per_page: 페이지당 결과 수 (기본값: 50)
        
    Returns:
        SearchResult: JSON 형식의 검색 결과
    """
    try:
        # 검색 서비스 호출
        search_results = search_service.search_subtitles(
            query=query,
            lang=lang,
            start_time=start_time,
            end_time=end_time,
            page=page,
            per_page=per_page
        )
        
        return search_results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"검색 중 오류가 발생했습니다: {str(e)}")


@router.post("/search/advanced", response_model=SearchResult)
async def advanced_search(search_query: SearchQuery):
    """
    고급 검색 옵션을 제공하는 API 엔드포인트
    
    Args:
        search_query: 검색 쿼리 객체
        
    Returns:
        SearchResult: 검색 결과
    """
    try:
        # 검색 서비스 호출
        search_results = search_service.search_subtitles(
            query=search_query.query,
            lang=search_query.lang,
            start_time=search_query.start_time,
            end_time=search_query.end_time,
            page=search_query.page,
            per_page=search_query.per_page
        )
        
        return search_results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"검색 중 오류가 발생했습니다: {str(e)}")


@router.post("/open-media")
async def open_media(media_path: str = Body(..., embed=True)):
    """
    미디어 파일을 OS 기본 프로그램으로 엽니다 (macOS: open 명령).
    Args:
        media_path: 미디어 파일 경로
    Returns:
        JSON: 성공 여부
    """
    try:
        subprocess.Popen(["open", media_path])
        return {"success": True, "message": f"미디어 파일을 엽니다: {media_path}"}
    except Exception as e:
        logger.error(f"미디어 열기 실패: {e}")
        raise HTTPException(status_code=500, detail=f"미디어 열기 실패: {str(e)}")


@router.post("/open-media-at-time")
async def open_media_at_time(media_path: str = Body(...), start_time: float = Body(...)):
    """
    미디어 파일을 지정 시간(초)부터 OS 플레이어(VLC/mpv)로 재생 (macOS)
    Args:
        media_path: 미디어 파일 경로
        start_time: 시작 시간(초)
    Returns:
        JSON: 성공 여부
    """
    try:
        # VLC가 설치되어 있다고 가정 (mpv도 유사)
        # VLC: --start-time=초
        # mpv: --start=초
        if os.system('which vlc > /dev/null 2>&1') == 0:
            subprocess.Popen(["vlc", "--play-and-exit", f"--start-time={start_time}", media_path])
        elif os.system('which mpv > /dev/null 2>&1') == 0:
            subprocess.Popen(["mpv", f"--start={start_time}", media_path])
        else:
            raise Exception("VLC 또는 mpv 플레이어가 설치되어 있어야 합니다.")
        return {"success": True, "message": f"{start_time}초부터 재생: {media_path}"}
    except Exception as e:
        logger.error(f"지정 시간 재생 실패: {e}")
        raise HTTPException(status_code=500, detail=f"지정 시간 재생 실패: {str(e)}")


@router.post("/delete-media")
async def delete_media(media_path: str = Body(...)):
    """
    미디어 파일 및 DB 레코드 삭제
    """
    try:
        # DB에서 삭제
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM media_files WHERE path = ?', (media_path,))
        conn.commit()
        conn.close()
        # 실제 파일 삭제
        if os.path.exists(media_path):
            os.remove(media_path)
        return {"success": True, "message": f"미디어 파일 삭제: {media_path}"}
    except Exception as e:
        logger.error(f"미디어 삭제 실패: {e}")
        raise HTTPException(status_code=500, detail=f"미디어 삭제 실패: {str(e)}")


@router.post("/delete-subtitles")
async def delete_subtitles(media_path: str = Body(...)):
    """
    자막 파일 및 DB 자막 삭제
    """
    try:
        # media_id 찾기
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM media_files WHERE path = ?', (media_path,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            raise HTTPException(status_code=404, detail="해당 미디어를 찾을 수 없습니다.")
        media_id = row['id']
        # DB 자막 삭제
        db.clear_subtitles_for_media(media_id)
        # 자막 파일 삭제 (확장자 .srt, .vtt 등 config에서)
        subtitle_exts = ['.srt', '.vtt']
        for ext in subtitle_exts:
            sub_path = os.path.splitext(media_path)[0] + ext
            if os.path.exists(sub_path):
                os.remove(sub_path)
        conn.close()
        return {"success": True, "message": f"자막 삭제: {media_path}"}
    except Exception as e:
        logger.error(f"자막 삭제 실패: {e}")
        raise HTTPException(status_code=500, detail=f"자막 삭제 실패: {str(e)}")


@router.get("/media-info")
async def media_info(media_path: str):
    """
    미디어 및 자막 정보 반환
    """
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM media_files WHERE path = ?', (media_path,))
        media = cursor.fetchone()
        conn.close()
        if not media:
            raise HTTPException(status_code=404, detail="해당 미디어를 찾을 수 없습니다.")
        # 자막 파일 존재 여부
        subtitle_exts = ['.srt', '.vtt']
        subtitles = []
        for ext in subtitle_exts:
            sub_path = os.path.splitext(media_path)[0] + ext
            if os.path.exists(sub_path):
                subtitles.append(sub_path)
        return {"media": media, "subtitles": subtitles}
    except Exception as e:
        logger.error(f"미디어 정보 조회 실패: {e}")
        raise


# === 미디어 파일 스트리밍 엔드포인트 ===
@router.get("/media/{path:path}")
async def stream_media(path: str, request: Request):
    """
    미디어 파일을 스트리밍 방식으로 제공
    
    Args:
        path: 스트리밍할 미디어 파일의 경로 (URL 인코딩 형태)
        
    Returns:
        StreamingResponse: 미디어 파일의 스트림
    """
    import os
    from fastapi.responses import StreamingResponse, JSONResponse
    
    try:
        logger.info(f"미디어 스트림 요청: {path}")
        
        # URL 디코딩: FastAPI가 자동으로 일부 디코딩하지만,
        # % 기호로 이중 인코딩된 문자가 있을 수 있으므로 추가 디코딩
        try:
            # % 문자 자체는 유지하면서 필요한 부분만 디코딩
            path = urllib.parse.unquote(path)
            logger.info(f"디코딩된 경로: {path}")
        except Exception as decode_error:
            logger.warning(f"경로 디코딩 중 오류 발생: {decode_error}")
        
        # 경로 조합 (절대 경로 조정 필요)
        # 파일 시스템에 맞게 경로 형식 조정 - macOS/Linux는 '/', Windows는 '\\'
        if os.name == 'nt':  # Windows
            full_path = path.replace('/', '\\')
        else:  # macOS/Linux
            full_path = path
            if not full_path.startswith('/'):
                full_path = '/' + full_path
        
        logger.info(f"스트리밍할 파일 전체 경로: {full_path}")
        
        # 파일 존재 확인
        if not os.path.exists(full_path):
            logger.error(f"파일 없음: {full_path}")
            
            # 경로 정책 적용 시도 (config 기반 경로 조정)
            try:
                adjusted_path = config.get_media_path(full_path)
                if os.path.exists(adjusted_path):
                    logger.info(f"조정된 경로로 파일 찾음: {adjusted_path}")
                    full_path = adjusted_path
                else:
                    return JSONResponse(
                        status_code=404,
                        content={"error": "요청한 미디어 파일을 찾을 수 없습니다."}
                    )
            except Exception as path_error:
                logger.error(f"경로 조정 실패: {path_error}")
                return JSONResponse(
                    status_code=404,
                    content={"error": "요청한 미디어 파일을 찾을 수 없습니다."}
                )
        
        # 미디어 파일 타입 확인 (정확한 MIME 타입 추론)
        content_type = "application/octet-stream"  # 기본값
        
        # 일반적인 비디오 포맷
        if full_path.lower().endswith((".mp4")):
            content_type = "video/mp4"
        elif full_path.lower().endswith((".webm")):
            content_type = "video/webm"
        elif full_path.lower().endswith((".ogg", ".ogv")):
            content_type = "video/ogg"
        elif full_path.lower().endswith((".mov", ".qt")):
            content_type = "video/quicktime"
        elif full_path.lower().endswith((".avi")):
            content_type = "video/x-msvideo"
        elif full_path.lower().endswith((".flv")):
            content_type = "video/x-flv"
        elif full_path.lower().endswith((".mkv")):
            content_type = "video/x-matroska"
        elif full_path.lower().endswith((".m4v")):
            content_type = "video/x-m4v"
        elif full_path.lower().endswith((".ts")):
            content_type = "video/mp2t"
            
        # 일반적인 오디오 포맷
        elif full_path.lower().endswith((".mp3")):
            content_type = "audio/mpeg"
        elif full_path.lower().endswith((".wav")):
            content_type = "audio/wav"
        elif full_path.lower().endswith((".aac")):
            content_type = "audio/aac"
        elif full_path.lower().endswith((".ogg", ".oga")):
            content_type = "audio/ogg"
        elif full_path.lower().endswith((".flac")):
            content_type = "audio/flac"
        elif full_path.lower().endswith((".m4a")):
            content_type = "audio/mp4"
        
        logger.info(f"미디어 콘텐츠 타입: {content_type}")
        
        # 파일 열기 및 스트리밍
        try:
            file_size = os.path.getsize(full_path)
        except Exception as size_error:
            logger.error(f"파일 크기 확인 중 오류: {size_error}")
            return JSONResponse(
                status_code=500,
                content={"error": "미디어 파일을 열 수 없습니다."}
            )
        
        # 파일 열기
        def iterfile():
            try:
                with open(full_path, mode="rb") as file_like:
                    # 청크 단위로 파일 전송
                    chunk_size = 1024 * 1024  # 1MB 청크
                    while chunk := file_like.read(chunk_size):
                        yield chunk
            except Exception as read_error:
                logger.error(f"파일 읽기 오류: {read_error}")
                raise
        
        # 안전한 파일명 생성
        safe_filename = os.path.basename(full_path)
        try:
            # ASCII가 아닌 문자가 있는 경우 인코딩
            safe_filename = urllib.parse.quote(safe_filename)
        except:
            pass
        
        headers = {
            'Content-Disposition': f'inline; filename="{safe_filename}"',
            'Accept-Ranges': 'bytes',
            'Content-Type': content_type,  # 명시적으로 콘텐츠 타입 헤더 추가
        }
        
        # Range 헤더 처리 (미디어 탐색 지원)
        range_header = request.headers.get('range')
        
        if range_header:
            try:
                parts = range_header.replace('bytes=', '').split('-')
                start = int(parts[0]) if parts[0] else 0
                end = int(parts[1]) if parts[1] else file_size - 1
                
                # 유효한 범위 체크
                if start >= file_size:
                    # 요청 범위가 파일 크기를 초과하는 경우
                    return JSONResponse(
                        status_code=416,  # Range Not Satisfiable
                        content={"error": "요청한 범위가 파일 크기를 초과합니다"}
                    )
                    
                # 끝점이 파일 크기보다 크면 조정
                if end >= file_size:
                    end = file_size - 1
                
                headers['Content-Range'] = f'bytes {start}-{end}/{file_size}'
                headers['Content-Length'] = str(end - start + 1)
                
                # 범위 요청 처리 함수
                def iterfile_range():
                    try:
                        with open(full_path, mode="rb") as file_like:
                            file_like.seek(start)
                            remaining = end - start + 1
                            while remaining > 0:
                                chunk_size = min(1024 * 1024, remaining)  # 1MB 또는 남은 크기
                                chunk = file_like.read(chunk_size)
                                if not chunk:
                                    break
                                remaining -= len(chunk)
                                yield chunk
                    except Exception as range_error:
                        logger.error(f"범위 파일 읽기 오류: {range_error}")
                        raise
                
                logger.debug(f"범위 스트리밍: {start}-{end}/{file_size}")
                return StreamingResponse(
                    iterfile_range(),
                    media_type=content_type,
                    headers=headers,
                    status_code=206  # Partial Content
                )
            except Exception as range_parse_error:
                logger.error(f"Range 헤더 파싱 오류: {range_parse_error}")
                # Range 헤더 파싱 실패 시 전체 파일 스트리밍으로 폴백
        
        # 전체 파일 스트리밍
        headers['Content-Length'] = str(file_size)
        logger.debug(f"전체 파일 스트리밍: {file_size} bytes")
        return StreamingResponse(
            iterfile(),
            media_type=content_type,
            headers=headers
        )
    
    except Exception as e:
        logger.error(f"미디어 스트리밍 오류: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": f"미디어 스트리밍 실패: {str(e)}"}
        )


@router.post("/add-tag")
async def add_tag(request: Request):
    """자막에 태그 추가"""
    try:
        data = await request.json()
        media_path = data.get("media_path", "")
        start_time = data.get("start_time", 0)
        tag = data.get("tag", "").strip()
        
        if not media_path or not tag:
            return JSONResponse({"success": False, "error": "필수 정보가 부족합니다."}, status_code=400)
        
        # 경로 정책에 따라 미디어 경로 통일 (북마크/태그 일관성 유지를 위해)
        media_path = config.get_media_path(media_path)
            
        success = db.add_tag(media_path, start_time, tag)
        
        if success:
            return JSONResponse({"success": True})
        else:
            return JSONResponse({"success": False, "error": "태그 추가 실패"}, status_code=500)
    except Exception as e:
        logger.error(f"태그 추가 중 오류: {str(e)}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

@router.post("/delete-tag")
async def delete_tag(request: Request):
    """자막에서 태그 삭제"""
    try:
        data = await request.json()
        media_path = data.get("media_path", "")
        start_time = data.get("start_time", 0)
        tag = data.get("tag", "").strip()
        
        if not media_path or not tag:
            return JSONResponse({"success": False, "error": "필수 정보가 부족합니다."}, status_code=400)
        
        # 경로 정책에 따라 미디어 경로 통일
        media_path = config.get_media_path(media_path)
            
        success = db.delete_tag(media_path, start_time, tag)
        
        if success:
            return JSONResponse({"success": True})
        else:
            return JSONResponse({"success": False, "error": "태그 삭제 실패 또는 존재하지 않음"}, status_code=404)
    except Exception as e:
        logger.error(f"태그 삭제 중 오류: {str(e)}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

@router.get("/get-tags")
async def get_tags(media_path: str, start_time: float):
    """특정 자막의 모든 태그 조회"""
    try:
        if not media_path:
            return JSONResponse({"success": False, "error": "미디어 경로가 필요합니다."}, status_code=400)
        
        # 경로 정책에 따라 미디어 경로 통일
        media_path = config.get_media_path(media_path)
            
        tags = db.get_tags(media_path, start_time)
        
        return JSONResponse({"success": True, "tags": tags})
    except Exception as e:
        logger.error(f"태그 조회 중 오류: {str(e)}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

@router.post("/bookmark")
async def toggle_bookmark(request: Request):
    """자막 북마크 추가 또는 삭제"""
    try:
        data = await request.json()
        media_path = data.get("media_path", "")
        start_time = data.get("start_time", 0)
        onoff = data.get("onoff", True)
        user_id = data.get("user_id", "default")
        
        if not media_path:
            return JSONResponse({"success": False, "error": "미디어 경로가 필요합니다."}, status_code=400)
        
        # 경로 정책에 따라 미디어 경로 통일
        media_path = config.get_media_path(media_path)
            
        success = db.toggle_bookmark(media_path, start_time, onoff, user_id)
        
        if success:
            return JSONResponse({"success": True, "onoff": onoff})
        else:
            return JSONResponse({"success": False, "error": "북마크 설정 실패"}, status_code=500)
    except Exception as e:
        logger.error(f"북마크 설정 중 오류: {str(e)}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

@router.get("/get-bookmarks")
async def get_bookmarks(user_id: str = "default"):
    """사용자의 모든 북마크 조회"""
    try:
        bookmarks = db.get_bookmarks(user_id)
        
        # 북마크의 미디어 경로를 현재 시스템에 맞게 조정
        adjusted_bookmarks = []
        for bookmark in bookmarks:
            parts = bookmark.split('|')
            if len(parts) == 2:
                rel_path, time = parts
                # 고정 경로 정책 적용 (필요시 경로 변환)
                abs_path = config.get_media_path(rel_path)
                adjusted_bookmarks.append(f"{abs_path}|{time}")
            else:
                adjusted_bookmarks.append(bookmark)
        
        return JSONResponse({"success": True, "bookmarks": adjusted_bookmarks})
    except Exception as e:
        logger.error(f"북마크 조회 중 오류: {str(e)}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)