"""
표준 인덱싱 전략 모듈

파일을 하나씩 순차적으로 처리하는 표준 인덱싱 전략을 구현합니다.
"""

import time
import traceback
from typing import Dict, Any, List

from app.services.indexer.indexing_strategy import IndexingStrategy
from app.database.media import upsert_media
from app.utils.logging import get_indexer_logger

logger = get_indexer_logger()

class StandardStrategy(IndexingStrategy):
    """표준 인덱싱 전략 - 파일을 하나씩 순차적으로 처리"""
    
    def __init__(self, worker=None):
        """
        표준 인덱싱 전략 초기화
        
        Args:
            worker: 인덱싱 워커 인스턴스
        """
        self.worker = worker
    
    def execute(self, media_files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        파일을 하나씩 순차적으로 처리하는 표준 인덱싱 수행
        
        Args:
            media_files: 처리할 미디어 파일 목록
            
        Returns:
            Dict[str, Any]: 인덱싱 결과
        """
        if not self.worker:
            return {"error": "인덱싱 워커가 설정되지 않았습니다."}
        
        status_handler = self.worker.status_handler
        processor = self.worker.processor
        
        self._log("INFO", f"표준 인덱싱 시작: {len(media_files)}개 파일 처리 예정")
        
        # 진행 상황 표시 변수
        total_files = len(media_files)
        processed_files = 0
        subtitle_count = 0
        process_start_time = time.time()
        last_progress_log = time.time()
        progress_interval = 60  # 진행 상황 로그 간격 (초)
        
        # 상태 업데이트
        if status_handler:
            status_handler.update_status(
                total_files=total_files,
                status_message=f"인덱싱 중... (0/{total_files})"
            )
        
        for i, media_file in enumerate(media_files):
            # 인덱싱 중단 확인
            if not self._is_indexing():
                self._log("INFO", "인덱싱 중지 요청으로 처리 중단")
                break
            
            # 일시 중지 확인
            if self._is_paused():
                while self._is_paused() and self._is_indexing():
                    time.sleep(1)
            
            media_id = media_file["id"]
            media_path = media_file["path"]
            subtitle_files = media_file.get("subtitle_files", [])
            
            # 상태 업데이트
            if status_handler:
                status_handler.update_status(
                    current_file=media_path,
                    status_message=f"인덱싱 중... ({processed_files}/{total_files})"
                )
            
            # 미디어 파일 처리 시작 로깅
            self._log("INFO", f"미디어 파일 처리 중 ({i+1}/{total_files}): {media_path}")
            
            # 자막 파일 처리
            for subtitle_path in subtitle_files:
                # 인덱싱 중단 확인
                if not self._is_indexing():
                    break
                
                try:
                    # 자막 처리
                    subtitles_count = processor.process_subtitle(subtitle_path, media_id)
                    subtitle_count += subtitles_count
                    
                    self._log("INFO", f"자막 처리 완료: {subtitle_path} - {subtitles_count}개 자막 인덱싱됨")
                    
                except Exception as e:
                    self._log("ERROR", f"자막 처리 중 오류: {str(e)} - {subtitle_path}")
                    self._log("ERROR", traceback.format_exc())
                    
                    # 오류 발생 후 잠시 대기 (0.5초)
                    time.sleep(0.5)
            
            # 처리 완료된 파일 수 증가
            processed_files += 1
            
            # 상태 업데이트
            if status_handler:
                status_handler.update_status(
                    processed_files=processed_files,
                    subtitle_count=subtitle_count,
                    status_message=f"인덱싱 중... ({processed_files}/{total_files})"
                )
            
            # 진행 상황 로그 추가 - 간격을 늘려 로깅 빈도 감소
            if time.time() - last_progress_log >= progress_interval:
                elapsed_time = time.time() - process_start_time
                if i > 0 and elapsed_time > 0:
                    files_per_second = i / elapsed_time
                    estimated_total_time = total_files / files_per_second if files_per_second > 0 else 0
                    estimated_remaining = max(0, estimated_total_time - elapsed_time)
                    
                    # 시간 형식 변환
                    elapsed_str = self._format_time(elapsed_time)
                    remaining_str = self._format_time(estimated_remaining)
                    
                    progress = int((i / total_files) * 100)
                    
                    self._log("INFO", f"인덱싱 진행 상황: {i}/{total_files} ({progress}%), "
                                     f"경과: {elapsed_str}, 예상 남은 시간: {remaining_str}")
                last_progress_log = time.time()
        
        # 처리 완료 후 최종 로그
        elapsed_time = time.time() - process_start_time
        elapsed_str = self._format_time(elapsed_time)
        
        self._log("INFO", f"인덱싱 완료: {total_files}개 파일, {subtitle_count}개 자막, 소요 시간: {elapsed_str}")
        
        # 인덱싱 결과
        return {
            "success": True,
            "message": "표준 인덱싱 완료",
            "files_processed": processed_files,
            "subtitles_processed": subtitle_count,
            "elapsed_time": elapsed_str
        }
    
    def _log(self, level: str, message: str) -> None:
        """
        로그 메시지 기록
        
        Args:
            level: 로그 레벨
            message: 로그 메시지
        """
        if self.worker and self.worker.status_handler:
            self.worker.status_handler.log(level, message)
        else:
            level_upper = level.upper()
            if level_upper == "INFO":
                logger.info(message)
            elif level_upper == "WARNING":
                logger.warning(message)
            elif level_upper == "ERROR":
                logger.error(message)
            elif level_upper == "DEBUG":
                logger.debug(message)
            elif level_upper == "CRITICAL":
                logger.critical(message)
    
    def _is_indexing(self) -> bool:
        """
        현재 인덱싱 중인지 확인
        
        Returns:
            bool: 인덱싱 중 여부
        """
        if self.worker:
            return self.worker.is_indexing()
        return False
    
    def _is_paused(self) -> bool:
        """
        현재 인덱싱이 일시 중지 상태인지 확인
        
        Returns:
            bool: 일시 중지 상태 여부
        """
        if self.worker:
            return self.worker.is_paused()
        return False
    
    def _format_time(self, seconds: float) -> str:
        """
        초 단위 시간을 읽기 쉬운 형식으로 변환
        
        Args:
            seconds: 초 단위 시간
            
        Returns:
            str: 형식화된 시간 문자열 (예: "1시간 30분 45초")
        """
        hours, remainder = divmod(int(seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours > 0:
            return f"{hours}시간 {minutes}분 {seconds}초"
        elif minutes > 0:
            return f"{minutes}분 {seconds}초"
        else:
            return f"{seconds}초"
