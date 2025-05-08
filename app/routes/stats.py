"""
통계 라우트 모듈

시스템 통계 정보 관련 API 엔드포인트를 정의합니다.
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from typing import Dict, Any, Optional, List

from app.services.stats import stats_service

# 라우터 생성
router = APIRouter(prefix="/api", tags=["stats"])


@router.get("/stats", response_class=HTMLResponse)
async def get_stats_html():
    """
    시스템 통계 정보를 HTML 형식으로 반환합니다.
    
    Returns:
        HTMLResponse: HTML 형식의 통계 정보
    """
    try:
        # 통계 정보 가져오기
        stats = stats_service.get_all_stats()
        
        # HTML 형식으로 포맷팅
        html_content = stats_service.format_stats_html(stats)
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        error_html = f"""
        <div class="bg-red-100 border-l-4 border-red-500 text-red-700 p-4 mt-4" role="alert">
            <p class="font-bold">통계 정보 조회 중 오류가 발생했습니다</p>
            <p>{str(e)}</p>
        </div>
        """
        return HTMLResponse(content=error_html, status_code=500)


@router.get("/stats/json", response_model=Dict[str, Any])
async def get_stats_json():
    """
    시스템 통계 정보를 JSON 형식으로 반환합니다.
    
    Returns:
        Dict[str, Any]: 통계 정보 딕셔너리
    """
    try:
        # 통계 정보 가져오기
        stats = stats_service.get_all_stats()
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"통계 정보 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/stats/daily", response_model=Dict[str, List])
async def get_daily_stats(days: int = Query(7, ge=1, le=30)):
    """
    일일 인덱싱 통계를 반환합니다.
    
    Args:
        days: 조회할 일수 (기본값: 7, 최대: 30)
        
    Returns:
        Dict[str, List]: 날짜별 인덱싱된 파일 수
    """
    try:
        # 일일 통계 가져오기
        daily_stats = stats_service.get_daily_indexing_stats(days)
        
        # 결과 포맷팅
        return {
            "dates": [date for date, _ in daily_stats],
            "counts": [count for _, count in daily_stats]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"일일 통계 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/stats/length-distribution", response_model=Dict[str, List])
async def get_length_distribution():
    """
    자막 길이 분포 통계를 반환합니다.
    
    Returns:
        Dict[str, List]: 자막 길이 분포 (범위별 개수)
    """
    try:
        # 통계 정보 가져오기
        stats = stats_service.get_all_stats()
        length_distribution = stats.get("subtitle_stats", {}).get("length_distribution", {})
        
        # 키와 값을 정렬된 목록으로 변환
        sorted_ranges = sorted(
            length_distribution.keys(),
            key=lambda x: {
                "~20": 1,
                "21~50": 2,
                "51~100": 3,
                "101~200": 4,
                "201~": 5
            }.get(x, 999)
        )
        
        return {
            "labels": sorted_ranges,
            "data": [length_distribution.get(range_key, 0) for range_key in sorted_ranges]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"자막 길이 분포 조회 중 오류가 발생했습니다: {str(e)}")