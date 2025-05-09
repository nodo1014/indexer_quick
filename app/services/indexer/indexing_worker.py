"""
인덱싱 워커 모듈

인덱싱 작업을 실행하는 기능을 제공합니다.
"""

import os
import time
import threading
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable

from app.config import config
from app.utils.logging import get_indexer_logger
from app.database.media import upsert_media
from app.database.subtitles import get_subtitle_stats

# 인덱싱 관련 클래스 임포트
from app.services.indexer.media_scanner import MediaScanner
from app.services.indexer.subtitle_processor import SubtitleProcessor

logger = get_indexer_logger()

class IndexingWorker:
    """인덱싱 작업 실행 클래스"""
    
    def __init__(self, status_handler=None):
        """
        인덱싱 워커 초기화
        
        Args:
            status_handler: 상태 관리자 인스턴스
        """
        self.status_handler = status_handler
        self.scanner = MediaScanner(status_handler)
        self.processor = SubtitleProcessor(status_handler)
        self.indexing_thread = None
        self.max_threads = config.get("indexer_max_threads", 1)
    
    def log(self, level: str, message: str) -> None:
        """
        로그 메시지 기록
        
        Args:
            level: 로그 레벨
            message: 로그 메시지
        """
        if self.status_handler:
            self.status_handler.log(level, message)
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
    
    def is_indexing(self) -> bool:
        """
        현재 인덱싱 중인지 확인
        
        Returns:
            bool: 인덱싱 중 여부
        """
        if self.status_handler:
            return self.status_handler.current_status.get("is_indexing", False)
        return False
    
    def is_paused(self) -> bool:
        """
        현재 인덱싱이 일시 중지 상태인지 확인
        
        Returns:
            bool: 일시 중지 상태 여부
        """
        if self.status_handler:
            return self.status_handler.current_status.get("is_paused", False)
        return False
    
    def start_worker(self, incremental: bool = True) -> None:
        """
        인덱싱 워커 스레드 시작
        
        Args:
            incremental: 증분 인덱싱 여부
        """
        if self.indexing_thread and self.indexing_thread.is_alive():
            self.log("WARNING", "이미 인덱싱 워커가 실행 중입니다.")
            return
        
        self.indexing_thread = threading.Thread(target=self.run_indexing, args=(incremental,))
        self.indexing_thread.daemon = True
        self.indexing_thread.start()
        
        self.log("INFO", f"인덱싱 워커 시작 (증분 모드: {incremental})")
    
    def run_indexing(self, incremental: bool = True) -> None:
        """
        인덱싱 작업 실행 함수
        
        Args:
            incremental: 증분 인덱싱 여부
        """
        try:
            self.log("INFO", f"인덱싱 작업 시작 (증분 모드: {incremental})")
            
            # 상태 업데이트
            if self.status_handler:
                self.status_handler.update_status(
                    status_message="미디어 파일 스캔 중...",
                    processed_files=0,
                    total_files=0,
                    current_file="",
                    subtitle_count=0
                )
            
            # 미디어 파일 스캔
            media_files = self.scanner.scan_directory(incremental, self.is_indexing)
            
            if not media_files:
                self.log("INFO", "인덱싱할 파일이 없습니다.")
                if self.status_handler:
                    self.status_handler.reset_status("완료")
                return
            
            # 상태 업데이트
            total_files = len(media_files)
            if self.status_handler:
                self.status_handler.update_status(
                    total_files=total_files,
                    status_message=f"인덱싱 중... (0/{total_files})"
                )
            
            # 인덱싱 시작 시간
            start_time = time.time()
            
            # 단일 스레드 인덱싱
            if self.max_threads <= 1:
                self._run_standard_indexing(media_files)
            else:
                # 병렬 인덱싱
                self._run_parallel_indexing(media_files)
            
            # 인덱싱 완료 후 통계 업데이트
            if self.is_indexing():
                # 인덱싱 시간 계산
                indexing_time = time.time() - start_time
                
                # 자막 통계 가져오기
                stats = get_subtitle_stats()
                
                # 완료 메시지
                self.log("INFO", f"인덱싱 완료: {total_files}개 파일, {stats.get('total_count', 0)}개 자막 ({indexing_time:.2f}초)")
                
                # FTS 인덱스 업데이트
                from app.services.indexer.indexing_strategy import update_fts_index
                update_fts_index()
                
                # 상태 초기화
                if self.status_handler:
                    self.status_handler.reset_status("완료")
            else:
                self.log("INFO", "인덱싱이 중단되었습니다.")
                
                # 상태 초기화
                if self.status_handler:
                    self.status_handler.reset_status("중단됨")
                
        except Exception as e:
            self.log("ERROR", f"인덱싱 작업 중 오류 발생: {str(e)}")
            
            # 오류 상태 업데이트
            if self.status_handler:
                self.status_handler.update_status(
                    is_indexing=False,
                    last_error=str(e),
                    status_message=f"인덱싱 오류: {str(e)}"
                )
    
    def _run_standard_indexing(self, media_files: List[Dict[str, Any]]) -> None:
        """
        단일 스레드 인덱싱 실행
        
        Args:
            media_files: 처리할 미디어 파일 목록
        """
        total_files = len(media_files)
        processed_files = 0
        subtitle_count = 0
        
        for media_file in media_files:
            # 일시 중지 상태 확인
            if self.is_paused():
                while self.is_paused() and self.is_indexing():
                    time.sleep(1)
            
            # 인덱싱 중단 확인
            if not self.is_indexing():
                break
            
            media_id = media_file["id"]
            media_path = media_file["path"]
            subtitle_files = media_file.get("subtitle_files", [])
            
            # 상태 업데이트
            if self.status_handler:
                self.status_handler.update_status(
                    current_file=media_path,
                    status_message=f"인덱싱 중... ({processed_files}/{total_files})"
                )
            
            # 자막 파일 처리
            for subtitle_path in subtitle_files:
                # 인덱싱 중단 확인
                if not self.is_indexing():
                    break
                
                # 자막 처리
                subtitles_count = self.processor.process_subtitle(subtitle_path, media_id)
                subtitle_count += subtitles_count
            
            # 처리 완료된 파일 수 증가
            processed_files += 1
            
            # 상태 업데이트
            if self.status_handler:
                self.status_handler.update_status(
                    processed_files=processed_files,
                    subtitle_count=subtitle_count,
                    status_message=f"인덱싱 중... ({processed_files}/{total_files})"
                )
    
    def _run_parallel_indexing(self, media_files: List[Dict[str, Any]]) -> None:
        """
        병렬 스레드 인덱싱 실행
        
        Args:
            media_files: 처리할 미디어 파일 목록
        """
        from concurrent.futures import ThreadPoolExecutor
        
        total_files = len(media_files)
        processed_files = 0
        subtitle_count = 0
        
        # 스레드 풀 생성
        with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            futures = []
            
            for media_file in media_files:
                # 인덱싱 중단 확인
                if not self.is_indexing():
                    break
                
                media_id = media_file["id"]
                media_path = media_file["path"]
                subtitle_files = media_file.get("subtitle_files", [])
                
                # 상태 업데이트
                if self.status_handler:
                    self.status_handler.update_status(
                        current_file=media_path,
                        status_message=f"인덱싱 중... ({processed_files}/{total_files})"
                    )
                
                # 자막 파일 병렬 처리
                for subtitle_path in subtitle_files:
                    # 인덱싱 중단 확인
                    if not self.is_indexing():
                        break
                    
                    # 스레드 풀에 작업 제출
                    future = executor.submit(self.processor.process_subtitle, subtitle_path, media_id)
                    futures.append((future, media_path))
                
                # 처리 완료된 파일 수 증가
                processed_files += 1
                
                # 상태 업데이트
                if self.status_handler:
                    self.status_handler.update_status(
                        processed_files=processed_files,
                        status_message=f"인덱싱 중... ({processed_files}/{total_files})"
                    )
            
            # 모든 작업 완료 대기
            for future, media_path in futures:
                # 인덱싱 중단 확인
                if not self.is_indexing():
                    break
                
                try:
                    # 작업 결과 가져오기
                    result = future.result()
                    subtitle_count += result
                    
                    # 상태 업데이트
                    if self.status_handler:
                        self.status_handler.update_status(
                            subtitle_count=subtitle_count
                        )
                except Exception as e:
                    self.log("ERROR", f"자막 처리 중 오류 발생: {str(e)} - {media_path}")
    
    def stop_worker(self) -> None:
        """인덱싱 워커 중지"""
        # 인덱싱 중단 플래그 설정
        if self.status_handler:
            self.status_handler.update_status(is_indexing=False)
        
        # 스레드 종료 대기
        if self.indexing_thread and self.indexing_thread.is_alive():
            self.indexing_thread.join(timeout=5.0)
            
        self.log("INFO", "인덱싱 워커 중지됨")
