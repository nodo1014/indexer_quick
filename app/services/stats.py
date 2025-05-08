"""
통계 서비스 모듈

시스템 통계 정보를 제공하는 서비스 클래스입니다.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from app.database import db
from app.config import config


class StatsService:
    """통계 정보 서비스"""
    
    @staticmethod
    def get_all_stats() -> Dict[str, Any]:
        """
        모든 통계 정보를 수집하여 반환합니다.
        
        Returns:
            Dict[str, Any]: 수집된 모든 통계 정보
        """
        # 기본 통계 정보 가져오기
        base_stats = db.get_all_stats()
        
        # 마지막 스캔 시간 가져오기
        last_scan_time = config.get("last_scan_time")
        
        # 자막 길이 분포 가져오기
        length_distribution = db.get_subtitle_length_distribution()
        
        # 확장자별 파일 수 계산
        extension_stats = StatsService._calculate_extension_stats()
        
        # 최종 통계 정보 구성
        stats = {
            "media_stats": {
                "total_count": base_stats.get("media_count", 0),
                "with_subtitles": base_stats.get("subtitles_ratio", {}).get("has_subtitles", 0),
                "without_subtitles": base_stats.get("media_count", 0) - base_stats.get("subtitles_ratio", {}).get("has_subtitles", 0),
                "subtitle_coverage_percentage": base_stats.get("subtitles_ratio", {}).get("percentage", 0)
            },
            "subtitle_stats": {
                "total_entries": base_stats.get("subtitle_count", 0),
                "language_distribution": {
                    lang: count for lang, count in base_stats.get("language_stats", [])
                },
                "length_distribution": {
                    category: count for category, count in length_distribution
                }
            },
            "file_stats": {
                "extensions": extension_stats
            },
            "system_info": {
                "last_scan_time": last_scan_time,
                "formatted_last_scan_time": StatsService._format_datetime(last_scan_time)
            }
        }
        
        return stats
    
    @staticmethod
    def _calculate_extension_stats() -> Dict[str, int]:
        """
        미디어 파일의 확장자별 통계를 계산합니다.
        
        Returns:
            Dict[str, int]: 확장자별 파일 수
        """
        extensions_count = {}
        
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT path FROM media_files")
            paths = cursor.fetchall()
            conn.close()
            
            import os
            for path in paths:
                ext = os.path.splitext(path["path"])[1].lower()
                extensions_count[ext] = extensions_count.get(ext, 0) + 1
                
        except Exception as e:
            print(f"확장자별 통계 계산 중 오류 발생: {e}")
        
        return extensions_count
    
    @staticmethod
    def get_daily_indexing_stats(days: int = 7) -> List[Tuple[str, int]]:
        """
        일일 인덱싱 통계를 반환합니다.
        
        Args:
            days: 조회할 일수
            
        Returns:
            List[Tuple[str, int]]: 날짜별 인덱싱된 파일 수
        """
        return db.get_daily_indexing_stats(days)
    
    @staticmethod
    def format_stats_html(stats: Dict[str, Any]) -> str:
        """
        통계 정보를 HTML 형식으로 포맷팅합니다.
        
        Args:
            stats: 통계 정보
            
        Returns:
            str: HTML 형식의 통계 정보
        """
        media_stats = stats.get("media_stats", {})
        subtitle_stats = stats.get("subtitle_stats", {})
        system_info = stats.get("system_info", {})
        
        html = f"""
        <div class="space-y-3 text-sm">
            <div>
                <p class="font-semibold text-lg text-blue-600">기본 통계</p>
                <p><span class="font-semibold">미디어 파일:</span> {media_stats.get("total_count", 0)}개</p>
                <p><span class="font-semibold">인덱싱된 자막:</span> {subtitle_stats.get("total_entries", 0)}개</p>
                <p><span class="font-semibold">마지막 스캔:</span> {system_info.get("formatted_last_scan_time", "없음")}</p>
                <p><span class="font-semibold">자막 있는 미디어 비율:</span> {media_stats.get("subtitle_coverage_percentage", 0)}% 
                   ({media_stats.get("with_subtitles", 0)}/{media_stats.get("total_count", 0)})</p>
            </div>
            
            <div>
                <p class="font-semibold text-lg text-blue-600 mt-3">언어 통계</p>
                <ul class="list-disc pl-5">
        """
        
        # 언어별 통계
        language_distribution = subtitle_stats.get("language_distribution", {})
        if language_distribution:
            for lang, count in language_distribution.items():
                html += f"<li><span class='font-semibold'>{lang}:</span> {count}개</li>\n"
        else:
            html += "<li>언어 통계 정보가 없습니다.</li>\n"
        
        html += """
                </ul>
            </div>
        </div>
        """
        
        return html

    @staticmethod
    def _format_datetime(datetime_str: Optional[str], 
                         format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
        """ISO 형식의 날짜/시간 문자열을 지정된 형식으로 변환합니다."""
        if not datetime_str:
            return "없음"
            
        try:
            dt = datetime.fromisoformat(datetime_str)
            return dt.strftime(format_str)
        except ValueError:
            # ISO 형식이 아닌 경우 원본 반환
            return datetime_str


# 서비스 인스턴스 생성
stats_service = StatsService()