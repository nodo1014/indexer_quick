"""
검색 서비스 모듈

자막 검색 기능을 제공하는 서비스 클래스입니다.
"""

import math
from typing import Dict, List, Any, Optional, Tuple
from app.database import db
from app.models.subtitle import Subtitle, SearchResult


class SearchService:
    """자막 검색 서비스"""
    
    @staticmethod
    def search_subtitles(
        query: str, 
        lang: Optional[str] = None, 
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        page: int = 1,
        per_page: int = 50
    ) -> SearchResult:
        """
        자막 내용 검색
        
        Args:
            query: 검색어
            lang: 언어 필터
            start_time: 시작 시간 필터
            end_time: 종료 시간 필터
            page: 페이지 번호
            per_page: 페이지당 결과 수
            
        Returns:
            SearchResult: 검색 결과 및 메타데이터
        """
        # 결과 수 제한을 위한 추가 쿼리 (결과가 많을 수 있으므로 total_count만 가져오는 쿼리 분리)
        # 참고: 실제 구현에서는 FTS 테이블의 rowid를 활용해 더 효율적으로 구현 가능
        # 계산된 total_count는 근사치일 수 있음
        total_count = SearchService._estimate_total_count(query, lang, start_time, end_time)
        
        # 실제 검색 수행
        results = db.search_subtitles(
            query=query,
            lang=lang,
            start_time=start_time,
            end_time=end_time,
            page=page,
            per_page=per_page
        )
        
        # 모델로 변환
        subtitle_items = [Subtitle.from_db(item) for item in results]
        
        # 총 페이지 수 계산
        total_pages = math.ceil(total_count / per_page) if per_page > 0 else 0
        
        # 적용된 필터 정보
        filters_applied = {
            "lang": lang,
            "start_time": start_time,
            "end_time": end_time
        }
        
        # 필터에서 None 값 제거
        filters_applied = {k: v for k, v in filters_applied.items() if v is not None}
        
        return SearchResult(
            items=subtitle_items,
            query=query,
            total_results=total_count,
            page=page,
            per_page=per_page,
            total_pages=total_pages,
            filters_applied=filters_applied
        )
    
    @staticmethod
    def _estimate_total_count(
        query: str, 
        lang: Optional[str] = None, 
        start_time: Optional[str] = None,
        end_time: Optional[str] = None
    ) -> int:
        """검색 조건에 맞는 총 결과 수 추정 (데이터베이스 계층에 위임)"""
        return db.estimate_total_count(query, lang, start_time, end_time)
    
    @staticmethod
    def format_search_results_html(results: SearchResult) -> str:
        """
        검색 결과를 HTML 형식으로 포맷팅
        
        Args:
            results: 검색 결과 객체
            
        Returns:
            str: HTML 형식의 검색 결과
        """
        import os
        import json
        
        # 디버깅 정보 로그
        print(f"검색 결과 개수: {len(results.items)}")
        print(f"검색어: {results.query}")
        print(f"전체 결과수: {results.total_results}")
        
        if not results.items:
            return """
            <div class="text-center py-4">
                <p class="text-gray-500">검색 결과가 없습니다.</p>
            </div>
            """
        
        # 필터 정보 추가
        filter_text = ""
        if results.filters_applied.get('lang'):
            filter_text += f" (언어: {results.filters_applied['lang']})"
        
        if results.filters_applied.get('start_time') and results.filters_applied.get('end_time'):
            filter_text += f" (시간대: {results.filters_applied['start_time']}-{results.filters_applied['end_time']})"
        
        html = f"""
        <div class="mb-2 text-sm text-gray-600">
            "{results.query}" 검색 결과: {results.total_results}건{filter_text}
            {f'(페이지: {results.page}/{results.total_pages})' if results.page > 1 else ''}
        </div>
        <div class="space-y-2">
        """
        
        for item in results.items:
            filepath = item.media_path or ""
            content = item.highlight or item.content
            
            # 디버깅을 위한 ID 추가
            html += f"""
            <div class="result-item p-3 border rounded cursor-pointer hover:bg-gray-50"
                 data-filepath="{filepath}"
                 data-starttime="{item.start_time_text}"
                 data-endtime="{item.end_time_text}"
                 id="result-item-{item.id}">
                <div class="flex justify-between items-start">
                    <span class="font-medium text-gray-800">{os.path.basename(filepath)}</span>
                    <span class="text-xs text-gray-500">{item.start_time_text} - {item.end_time_text}</span>
                </div>
                <p class="content mt-1 text-gray-700">{content}</p>
            </div>
            """
        
        # 페이지네이션 추가
        if results.page < results.total_pages:
            next_page = results.page + 1
            
            # 쿼리스트링 생성
            query_params = f"query={results.query}"
            if results.filters_applied.get('lang'):
                query_params += f"&lang={results.filters_applied['lang']}"
            if results.filters_applied.get('start_time') and results.filters_applied.get('end_time'):
                query_params += f"&start_time={results.filters_applied['start_time']}&end_time={results.filters_applied['end_time']}"
            query_params += f"&page={next_page}&per_page={results.per_page}"
            
            html += f"""
            <div class="flex justify-center mt-4">
                <button 
                    class="bg-blue-500 hover:bg-blue-600 text-white py-1 px-4 rounded text-sm"
                    hx-get="/api/search?{query_params}"
                    hx-target="#search-results"
                    hx-swap="innerHTML"
                >
                    더 보기
                </button>
            </div>
            """
        
        html += "</div>"
        return html


# 서비스 인스턴스 생성
search_service = SearchService()