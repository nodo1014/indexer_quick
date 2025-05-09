"""
인덱싱 서비스 모듈

인덱싱 서비스를 관리하는 기능을 제공합니다.
"""

import os
import time
import threading
from typing import Dict, Any, Optional, List

from app.config import config
from app.utils.logging import get_indexer_logger

# 인덱싱 관련 클래스 임포트
from app.services.indexer.indexing_worker import IndexingWorker
from app.services.indexer.indexing_status_handler import IndexingStatusHandler
from app.services.indexer.strategy_standard import StandardIndexingStrategy
from app.services.indexer.strategy_parallel import ParallelIndexingStrategy

logger = get_indexer_logger()

class IndexingService:
    """인덱싱 서비스 클래스"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        """싱글톤 패턴 구현"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(IndexingService, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """인덱싱 서비스 초기화"""
        # 이미 초기화된 경우 건너뜀
        if self._initialized:
            return
            
        # 상태 핸들러 초기화
        self.status_handler = IndexingStatusHandler()
        
        # 워커 초기화
        self.worker = IndexingWorker(self.status_handler)
        
        # 인덱싱 전략 초기화
        self.standard_strategy = StandardIndexingStrategy()
        self.parallel_strategy = ParallelIndexingStrategy()
        
        # 초기화 완료 표시
        self._initialized = True
        
        logger.info("인덱싱 서비스 초기화 완료")
    
    def start_indexing(self, incremental: bool = True) -> Dict[str, Any]:
        """
        인덱싱 시작
        
        Args:
            incremental: 증분 인덱싱 여부
            
        Returns:
            Dict[str, Any]: 인덱싱 시작 결과
        """
        # 이미 인덱싱 중인 경우
        if self.status_handler.current_status["is_indexing"]:
            return {"error": "이미 인덱싱이 진행 중입니다."}
        
        # 일시 중지 상태인 경우 재개
        if self.status_handler.current_status["is_paused"]:
            return self.resume_indexing()
        
        # 상태 업데이트
        self.status_handler.update_status(
            is_indexing=True,
            is_paused=False,
            status_message="인덱싱 시작 중..."
        )
        
        # 워커 시작
        self.worker.start_worker(incremental)
        
        return {
            "success": True,
            "message": "인덱싱이 시작되었습니다.",
            "incremental": incremental
        }
    
    def stop_indexing(self) -> Dict[str, Any]:
        """
        인덱싱 중지
        
        Returns:
            Dict[str, Any]: 인덱싱 중지 결과
        """
        # 인덱싱 중이 아닌 경우
        if not self.status_handler.current_status["is_indexing"]:
            return {"error": "인덱싱이 진행 중이 아닙니다."}
        
        # 워커 중지
        self.worker.stop_worker()
        
        # 상태 업데이트
        self.status_handler.update_status(
            is_indexing=False,
            is_paused=False,
            status_message="인덱싱이 중지되었습니다."
        )
        
        return {
            "success": True,
            "message": "인덱싱이 중지되었습니다."
        }
    
    def pause_indexing(self) -> Dict[str, Any]:
        """
        인덱싱 일시 중지
        
        Returns:
            Dict[str, Any]: 인덱싱 일시 중지 결과
        """
        # 인덱싱 중이 아닌 경우
        if not self.status_handler.current_status["is_indexing"]:
            return {"error": "인덱싱이 진행 중이 아닙니다."}
        
        # 이미 일시 중지된 경우
        if self.status_handler.current_status["is_paused"]:
            return {"error": "이미 인덱싱이 일시 중지되었습니다."}
        
        # 상태 업데이트
        self.status_handler.update_status(
            is_paused=True,
            status_message="인덱싱이 일시 중지되었습니다."
        )
        
        return {
            "success": True,
            "message": "인덱싱이 일시 중지되었습니다."
        }
    
    def resume_indexing(self) -> Dict[str, Any]:
        """
        인덱싱 재개
        
        Returns:
            Dict[str, Any]: 인덱싱 재개 결과
        """
        # 일시 중지 상태가 아닌 경우
        if not self.status_handler.current_status["is_paused"]:
            return {"error": "인덱싱이 일시 중지 상태가 아닙니다."}
        
        # 상태 업데이트
        self.status_handler.update_status(
            is_paused=False,
            status_message="인덱싱이 재개되었습니다."
        )
        
        return {
            "success": True,
            "message": "인덱싱이 재개되었습니다."
        }
    
    def get_status(self) -> Dict[str, Any]:
        """
        인덱싱 상태 가져오기
        
        Returns:
            Dict[str, Any]: 인덱싱 상태
        """
        return self.status_handler.get_status()
    
    def get_logs(self, count: int = 100) -> List[Dict[str, Any]]:
        """
        인덱싱 로그 가져오기
        
        Args:
            count: 가져올 로그 수
            
        Returns:
            List[Dict[str, Any]]: 로그 목록
        """
        return self.status_handler.get_logs(count)
    
    def reset_status(self) -> Dict[str, Any]:
        """
        인덱싱 상태 초기화
        
        Returns:
            Dict[str, Any]: 초기화 결과
        """
        # 인덱싱 중인 경우 중지
        if self.status_handler.current_status["is_indexing"]:
            self.stop_indexing()
        
        # 상태 초기화
        self.status_handler.reset_status()
        
        return {
            "success": True,
            "message": "인덱싱 상태가 초기화되었습니다."
        }
    
    def update_fts_index(self) -> Dict[str, Any]:
        """
        FTS 인덱스 수동 업데이트
        
        Returns:
            Dict[str, Any]: 업데이트 결과
        """
        from app.services.indexer.indexing_strategy import update_fts_index
        
        # 인덱싱 중인 경우
        if self.status_handler.current_status["is_indexing"]:
            return {"error": "인덱싱이 진행 중입니다. 인덱싱이 완료된 후 다시 시도하세요."}
        
        # 로그 기록
        self.status_handler.log("INFO", "FTS 인덱스 수동 업데이트 시작")
        
        # FTS 인덱스 업데이트
        result = update_fts_index()
        
        if result:
            self.status_handler.log("INFO", "FTS 인덱스 수동 업데이트 완료")
            return {
                "success": True,
                "message": "FTS 인덱스가 업데이트되었습니다."
            }
        else:
            self.status_handler.log("ERROR", "FTS 인덱스 수동 업데이트 실패")
            return {
                "error": "FTS 인덱스 업데이트 중 오류가 발생했습니다."
            }
    
    def get_config(self) -> Dict[str, Any]:
        """
        인덱싱 설정 가져오기
        
        Returns:
            Dict[str, Any]: 인덱싱 설정
        """
        indexer_config = {
            "root_dir": config.get("root_dir", ""),
            "media_extensions": config.get("media_extensions", []),
            "subtitle_extensions": config.get("subtitle_extensions", []),
            "max_threads": config.get("indexer_max_threads", 1)
        }
        
        return indexer_config
    
    def update_config(self, new_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        인덱싱 설정 업데이트
        
        Args:
            new_config: 새 설정
            
        Returns:
            Dict[str, Any]: 업데이트 결과
        """
        # 인덱싱 중인 경우
        if self.status_handler.current_status["is_indexing"]:
            return {"error": "인덱싱이 진행 중입니다. 인덱싱이 완료된 후 다시 시도하세요."}
        
        try:
            # 설정 업데이트
            for key, value in new_config.items():
                if key in ["root_dir", "media_extensions", "subtitle_extensions", "indexer_max_threads"]:
                    config.set(key, value)
            
            # 설정 저장
            config.save()
            
            # 워커 설정 업데이트
            self.worker.max_threads = config.get("indexer_max_threads", 1)
            
            return {
                "success": True,
                "message": "인덱싱 설정이 업데이트되었습니다.",
                "config": self.get_config()
            }
            
        except Exception as e:
            logger.error(f"설정 업데이트 중 오류 발생: {str(e)}")
            return {
                "error": f"설정 업데이트 중 오류가 발생했습니다: {str(e)}"
            }
