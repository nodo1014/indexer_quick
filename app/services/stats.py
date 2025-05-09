"""
통계 서비스 모듈

시스템 통계 정보를 제공하는 서비스 클래스입니다.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import traceback
from app.database import db
from app.config import config
from app.utils.logging import setup_module_logger

# 로거 초기화
logger = setup_module_logger("stats_service")

class StatsService:
    """통계 정보 서비스"""
    
    @staticmethod
    def get_all_stats() -> Dict[str, Any]:
        """
        모든 통계 정보를 수집하여 반환합니다.
        
        Returns:
            Dict[str, Any]: 수집된 모든 통계 정보
        """
        try:
            # 마지막 스캔 시간 가져오기
            last_scan_time = config.get("last_scan_time")
            
            # 기본 통계값 초기화 (오류 시 사용)
            default_stats = {
                "media_stats": {"total_count": 0, "with_subtitles": 0, "without_subtitles": 0, "subtitle_coverage_percentage": 0},
                "subtitle_stats": {"total_entries": 0, "language_distribution": {}, "length_distribution": {}},
                "file_stats": {"extensions": {}},
                "system_info": {"last_scan_time": last_scan_time, "formatted_last_scan_time": StatsService._format_datetime(last_scan_time) or "없음"}
            }
            
            # 각 부분별로 별도로 try-except 처리하여 오류에도 부분적 데이터 제공
            try:
                # 기본 통계 정보 가져오기
                base_stats = db.get_all_stats()
            except Exception as e:
                logger.error(f"기본 통계 정보 가져오기 실패: {e}")
                logger.debug(traceback.format_exc())
                base_stats = {"media_count": 0, "subtitle_count": 0, "subtitles_ratio": {"percentage": 0, "has_subtitles": 0, "total": 0}}
            
            try:
                # 자막 통계 가져오기
                subtitle_stats = db.get_subtitle_stats()
            except Exception as e:
                logger.error(f"자막 통계 가져오기 실패: {e}")
                logger.debug(traceback.format_exc())
                subtitle_stats = {"total": 0, "languages": {}}
                
            try:
                # 미디어 통계 가져오기
                media_stats = db.get_media_stats()
            except Exception as e:
                logger.error(f"미디어 통계 가져오기 실패: {e}")
                logger.debug(traceback.format_exc())
                media_stats = {"total": 0, "with_subtitles": 0, "without_subtitles": 0, "subtitle_coverage_percent": 0}
            
            # 자막 길이 분포 계산
            try:
                length_distribution = db.get_subtitle_length_distribution()
            except Exception as e:
                logger.error(f"자막 길이 분포 계산 실패: {e}")
                logger.debug(traceback.format_exc())
                # 기본값 또는 서비스 내에서 직접 계산 시도
                try:
                    length_distribution = StatsService._calculate_length_distribution()
                except Exception as ex:
                    logger.error(f"내부 자막 길이 분포 계산도 실패: {ex}")
                    length_distribution = []
            
            # 확장자별 파일 수 계산 (별도 오류 처리)
            try:
                extension_stats = StatsService._calculate_extension_stats()
            except Exception as e:
                logger.error(f"확장자별 통계 계산 실패: {e}")
                logger.debug(traceback.format_exc())
                extension_stats = {}
            
            # 최종 통계 정보 구성
            stats = {
                "media_stats": {
                    "total_count": media_stats.get("total", 0),
                    "with_subtitles": media_stats.get("with_subtitles", 0),
                    "without_subtitles": media_stats.get("without_subtitles", 0),
                    "subtitle_coverage_percentage": media_stats.get("subtitle_coverage_percent", 0)
                },
                "subtitle_stats": {
                    "total_entries": subtitle_stats.get("total", 0),
                    "language_distribution": subtitle_stats.get("languages", {}),
                    "length_distribution": {
                        category: count for category, count in length_distribution
                    } if isinstance(length_distribution, list) else length_distribution
                },
                "file_stats": {
                    "extensions": extension_stats
                },
                "system_info": {
                    "last_scan_time": last_scan_time,
                    "formatted_last_scan_time": StatsService._format_datetime(last_scan_time) or "없음"
                }
            }
            
            return stats
        except Exception as e:
            logger.error(f"통계 정보 수집 중 오류: {e}")
            logger.debug(traceback.format_exc())
            # 빈 통계 정보 반환
            return {
                "media_stats": {"total_count": 0, "with_subtitles": 0, "without_subtitles": 0, "subtitle_coverage_percentage": 0},
                "subtitle_stats": {"total_entries": 0, "language_distribution": {}, "length_distribution": {}},
                "file_stats": {"extensions": {}},
                "system_info": {"last_scan_time": "", "formatted_last_scan_time": "없음"}
            }
    
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
            logger.error(f"확장자별 통계 계산 중 오류 발생: {e}")
        
        return extensions_count
    
    @staticmethod
    def _calculate_length_distribution() -> Dict[str, int]:
        """
        자막 길이 분포를 계산합니다. (get_subtitle_length_distribution 대체 함수)
        
        Returns:
            Dict[str, int]: 자막 길이 분포
        """
        length_ranges = {
            "~20": 0,
            "21~50": 0,
            "51~100": 0,
            "101~200": 0,
            "201~": 0
        }
        
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT content FROM subtitles")
            subtitles = cursor.fetchall()
            conn.close()
            
            for subtitle in subtitles:
                content = subtitle["content"]
                word_count = len(content.split())
                
                if word_count <= 20:
                    length_ranges["~20"] += 1
                elif word_count <= 50:
                    length_ranges["21~50"] += 1
                elif word_count <= 100:
                    length_ranges["51~100"] += 1
                elif word_count <= 200:
                    length_ranges["101~200"] += 1
                else:
                    length_ranges["201~"] += 1
        except Exception as e:
            logger.error(f"자막 길이 분포 계산 중 오류 발생: {e}")
        
        return length_ranges
    
    @staticmethod
    def get_daily_indexing_stats(days: int = 7) -> List[Tuple[str, int]]:
        """
        일일 인덱싱 통계를 반환합니다.
        
        Args:
            days: 조회할 일수
            
        Returns:
            List[Tuple[str, int]]: 날짜별 인덱싱된 파일 수
        """
        try:
            return db.get_daily_indexing_stats(days)
        except AttributeError:
            # 함수가 없는 경우 빈 목록 반환
            logger.error("get_daily_indexing_stats 함수가 존재하지 않습니다.")
            return []
    
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
            # 유효한 언어 코드인지 확인하고, 적절한 형식으로 표시
            for lang, count in language_distribution.items():
                # 언어 코드에 따라 적절한 이름으로 변환
                lang_name = StatsService._get_language_name(lang)
                html += f"<li><span class='font-semibold'>{lang_name}:</span> {count}개</li>\n"
        else:
            html += "<li>언어 통계 정보가 없습니다.</li>\n"
        
        html += """
                </ul>
            </div>
        </div>
        """
        
        return html

    @staticmethod
    def _get_language_name(lang_code: str) -> str:
        """
        언어 코드에 따라 적절한 언어 이름을 반환합니다.
        
        Args:
            lang_code: 언어 코드 또는 문자열
            
        Returns:
            str: 언어 이름
        """
        # 언어 코드가 실제 시간 형식인지 확인 (00:00:00 패턴)
        import re
        if re.match(r'^\d{2}:\d{2}:\d{2}', lang_code):
            return "기타"
            
        # 주요 언어 코드에 대한 이름 매핑
        language_map = {
            "en": "영어",
            "ko": "한국어",
            "ja": "일본어",
            "zh": "중국어",
            "es": "스페인어",
            "fr": "프랑스어",
            "de": "독일어",
            "ru": "러시아어",
            "it": "이탈리아어",
            "pt": "포르투갈어"
        }
        
        # 알려진 언어 코드인 경우 해당 이름 반환
        return language_map.get(lang_code.lower(), lang_code)

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