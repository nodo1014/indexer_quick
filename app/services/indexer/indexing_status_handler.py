"""
인덱싱 상태 관리 모듈

인덱싱 작업의 상태를 관리하고 저장하는 기능을 제공합니다.
"""

import os
import json
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

from app.utils.constants import INDEXING_STATUS_FILE, MAX_LOG_ENTRIES
from app.utils.logging import get_indexer_logger

logger = get_indexer_logger()

class IndexingStatusHandler:
    """인덱싱 상태 관리 클래스"""
    
    def __init__(self):
        """상태 관리자 초기화"""
        self.status_file = INDEXING_STATUS_FILE
        self.last_save_time = 0
        self.save_interval = 1.0  # 1초 간격으로 저장 (디바운싱)
        self.current_status = self.load_status() or {
            "is_indexing": False,
            "processed_files": 0,
            "total_files": 0,
            "current_file": "",
            "subtitle_count": 0,
            "log_messages": [],
            "pid": None,
            "last_updated": None,
            "retry_count": 0,
            "last_error": None
        }
    
    def load_status(self) -> Optional[Dict[str, Any]]:
        """
        저장된 인덱싱 상태 로드
        
        Returns:
            Optional[Dict[str, Any]]: 로드된 상태 또는 None
        """
        try:
            if os.path.exists(self.status_file):
                with open(self.status_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"상태 파일 로딩 오류: {str(e)}")
        return None
    
    def save_status(self, force: bool = False) -> bool:
        """
        현재 인덱싱 상태를 파일에 저장 (디바운싱 적용)
        
        Args:
            force (bool): 디바운싱을 무시하고 강제 저장할지 여부
            
        Returns:
            bool: 저장 성공 여부
        """
        current_time = time.time()
        
        # 디바운싱 - 마지막 저장 후 일정 시간이 지나지 않았으면 저장하지 않음
        if not force and (current_time - self.last_save_time < self.save_interval):
            return False
            
        try:
            # 현재 시간 추가
            self.current_status["last_updated"] = datetime.now().isoformat()
            
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(self.current_status, f, ensure_ascii=False, indent=2)
                
            self.last_save_time = current_time
            return True
        except Exception as e:
            logger.error(f"상태 저장 오류: {str(e)}")
            return False
    
    def check_running_indexing(self) -> bool:
        """
        서버 시작 시 이전 인덱싱 프로세스 확인
        
        Returns:
            bool: 이전 인덱싱이 실행 중인지 여부
        """
        if self.current_status.get("is_indexing") and self.current_status.get("pid"):
            pid = self.current_status.get("pid")
            # PID가 여전히 실행 중인지 확인
            try:
                if os.name == 'nt':  # Windows
                    import ctypes
                    kernel32 = ctypes.windll.kernel32
                    handle = kernel32.OpenProcess(1, False, pid)
                    if handle == 0:
                        self.reset_status("이전 인덱싱 프로세스가 종료됨")
                        return False
                    else:
                        kernel32.CloseHandle(handle)
                else:  # Unix/Linux/MacOS
                    os.kill(pid, 0)
            except (OSError, ProcessLookupError):
                # 프로세스가 존재하지 않음
                self.reset_status("이전 인덱싱 프로세스가 종료됨")
                return False
            else:
                # 마지막 업데이트 시간 확인
                if self.current_status.get("last_updated"):
                    try:
                        last_updated = datetime.fromisoformat(self.current_status["last_updated"])
                        now = datetime.now()
                        if (now - last_updated).total_seconds() > 300:  # 5분 이상 업데이트 없음
                            self.reset_status("인덱싱 프로세스가 응답하지 않음 (5분 이상 업데이트 없음)")
                            return False
                    except (ValueError, TypeError):
                        pass
                return True
        return False
    
    def reset_status(self, reason: str = "완료") -> None:
        """
        인덱싱 상태 초기화
        
        Args:
            reason (str): 초기화 이유
        """
        self.log("WARNING", f"인덱싱 상태 초기화: {reason}")
        self.current_status["is_indexing"] = False
        self.current_status["pid"] = None
        self.current_status["status_message"] = f"인덱싱 {reason}"
        self.current_status["percentage"] = 100 if reason == "완료" else 0
        self.current_status["is_paused"] = False
        self.current_status["retry_count"] = 0
        self.current_status["last_error"] = None
        self.save_status(force=True)
    
    def log(self, level: str, message: str) -> None:
        """
        로그 메시지 추가 및 파일에 기록
        
        Args:
            level (str): 로그 레벨
            message (str): 로그 메시지
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"{timestamp} {level}: {message}"
        
        # 상태 메모리에 로그 추가
        self.current_status["log_messages"].insert(0, log_entry)
        
        # 최대 MAX_LOG_ENTRIES개의 로그만 유지
        if len(self.current_status["log_messages"]) > MAX_LOG_ENTRIES:
            self.current_status["log_messages"].pop()
            
        # 로깅 모듈을 사용하여 파일에 로그 기록
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
        else:
            # 기본값은 INFO
            logger.info(message)
            
        # 로그 추가할 때마다 상태 저장 (디바운싱 적용)
        self.save_status()
    
    def update_status(self, **kwargs) -> None:
        """
        상태 업데이트
        
        Args:
            **kwargs: 업데이트할 상태 키-값 쌍
        """
        for key, value in kwargs.items():
            self.current_status[key] = value
        self.save_status()
    
    def get_status(self) -> Dict[str, Any]:
        """
        현재 인덱싱 상태 반환
        
        Returns:
            Dict[str, Any]: 현재 인덱싱 상태
        """
        # ETA 계산 추가
        if self.current_status["is_indexing"]:
            processed = self.current_status["processed_files"]
            total = max(1, self.current_status["total_files"])  # 0으로 나누기 방지
            
            # 진행률 계산
            progress = min(100, int((processed / total) * 100))
            self.current_status["progress"] = progress
            
            # 예상 완료 시간 계산
            if processed > 0:
                try:
                    # 시작 시간이 저장되어 있으면 사용
                    if "start_time" in self.current_status:
                        start_time = datetime.fromisoformat(self.current_status["start_time"])
                        from app.utils.helpers import get_estimated_completion_time
                        eta = get_estimated_completion_time(processed, total, start_time)
                        if eta:
                            self.current_status["eta"] = eta
                        else:
                            self.current_status["eta"] = "계산 중..."
                except Exception:
                    self.current_status["eta"] = "계산 중..."
        
        return self.current_status
