"""
작업 관리 모듈

백그라운드 작업의 상태를 관리하고 추적하는 기능을 제공합니다.
주로 자막 인코딩 변환, 다중 자막 처리 등의 장시간 작업을 추적합니다.
"""

import threading
import time
import logging
import uuid
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime

# 로거 설정
logger = logging.getLogger("job_manager")

class JobStatus:
    """작업 상태 열거형"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"
    IDLE = "idle"


class Job:
    """작업 정보를 저장하는 클래스"""
    
    def __init__(self, job_id: str, job_type: str, params: Dict[str, Any] = None):
        """작업 객체 초기화
        
        Args:
            job_id: 작업 고유 ID
            job_type: 작업 유형 (예: "encoding_conversion", "subtitle_extract")
            params: 작업 파라미터
        """
        self.job_id = job_id
        self.job_type = job_type
        self.params = params or {}
        self.status = JobStatus.PENDING
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None
        self.progress = 0
        self.total = 0
        self.current_item = None
        self.result = {}
        self.error = None
        self.success_count = 0
        self.failed_count = 0
        self.callback = None
    
    def start(self) -> None:
        """작업 시작 시간을 기록하고 상태를 RUNNING으로 변경"""
        self.started_at = datetime.now()
        self.status = JobStatus.RUNNING
    
    def complete(self, result: Dict[str, Any] = None) -> None:
        """작업 완료 처리
        
        Args:
            result: 작업 결과 데이터
        """
        self.completed_at = datetime.now()
        self.status = JobStatus.COMPLETED
        self.progress = self.total if self.total > 0 else 1
        self.result = result or {}
        
        # 콜백 함수가 있으면 실행
        if self.callback:
            try:
                self.callback(self)
            except Exception as e:
                logger.error(f"작업 완료 콜백 실행 중 오류 발생: {e}")
    
    def fail(self, error: str) -> None:
        """작업 실패 처리
        
        Args:
            error: 오류 메시지
        """
        self.completed_at = datetime.now()
        self.status = JobStatus.FAILED
        self.error = error
        
        # 콜백 함수가 있으면 실행
        if self.callback:
            try:
                self.callback(self)
            except Exception as e:
                logger.error(f"작업 실패 콜백 실행 중 오류 발생: {e}")
    
    def cancel(self) -> None:
        """작업 취소 처리"""
        self.completed_at = datetime.now()
        self.status = JobStatus.CANCELED
        
        # 콜백 함수가 있으면 실행
        if self.callback:
            try:
                self.callback(self)
            except Exception as e:
                logger.error(f"작업 취소 콜백 실행 중 오류 발생: {e}")
    
    def update_progress(self, progress: int, total: int, current_item: str = None) -> None:
        """작업 진행 상태 업데이트
        
        Args:
            progress: 현재 진행 항목 수
            total: 전체 항목 수
            current_item: 현재 처리 중인 항목 (예: 파일 경로)
        """
        self.progress = progress
        self.total = total
        if current_item:
            self.current_item = current_item
    
    def get_status_dict(self) -> Dict[str, Any]:
        """작업 상태를 사전 형태로 반환
        
        Returns:
            Dict[str, Any]: 작업 상태 정보
        """
        duration = None
        if self.started_at:
            if self.completed_at:
                duration = (self.completed_at - self.started_at).total_seconds()
            else:
                duration = (datetime.now() - self.started_at).total_seconds()
        
        progress_percent = 0
        if self.total > 0:
            progress_percent = round(self.progress / self.total * 100, 1)
        
        return {
            "job_id": self.job_id,
            "job_type": self.job_type,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration": duration,
            "progress": self.progress,
            "total": self.total,
            "progress_percent": progress_percent,
            "current_item": self.current_item,
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "error": self.error
        }


class JobManager:
    """작업 관리자 클래스"""
    
    def __init__(self):
        """작업 관리자 초기화"""
        self.jobs: Dict[str, Job] = {}
        self.active_jobs: Dict[str, Job] = {}
        self.completed_jobs: Dict[str, Job] = {}
        self.lock = threading.Lock()
        self.max_history = 100  # 유지할 최대 작업 이력 수
    
    def create_job(self, job_type: str, params: Dict[str, Any] = None, callback: Callable = None) -> str:
        """새 작업 생성
        
        Args:
            job_type: 작업 유형
            params: 작업 파라미터
            callback: 작업 완료 시 호출할 콜백 함수
        
        Returns:
            str: 생성된 작업 ID
        """
        job_id = str(uuid.uuid4())
        job = Job(job_id, job_type, params)
        job.callback = callback
        
        with self.lock:
            self.jobs[job_id] = job
        
        logger.debug(f"작업 생성: {job_id}, 유형: {job_type}")
        return job_id
    
    def start_job(self, job_id: str) -> None:
        """작업 시작
        
        Args:
            job_id: 작업 ID
        
        Raises:
            KeyError: 존재하지 않는 작업 ID
        """
        with self.lock:
            if job_id not in self.jobs:
                raise KeyError(f"존재하지 않는 작업 ID: {job_id}")
            
            job = self.jobs[job_id]
            job.start()
            self.active_jobs[job_id] = job
        
        logger.debug(f"작업 시작: {job_id}")
    
    def complete_job(self, job_id: str, result: Dict[str, Any] = None) -> None:
        """작업 완료 처리
        
        Args:
            job_id: 작업 ID
            result: 작업 결과
        
        Raises:
            KeyError: 존재하지 않는 작업 ID
        """
        with self.lock:
            if job_id not in self.jobs:
                raise KeyError(f"존재하지 않는 작업 ID: {job_id}")
            
            job = self.jobs[job_id]
            job.complete(result)
            
            if job_id in self.active_jobs:
                del self.active_jobs[job_id]
            
            self.completed_jobs[job_id] = job
            self._clean_old_jobs()
        
        logger.debug(f"작업 완료: {job_id}")
    
    def fail_job(self, job_id: str, error: str) -> None:
        """작업 실패 처리
        
        Args:
            job_id: 작업 ID
            error: 오류 메시지
        
        Raises:
            KeyError: 존재하지 않는 작업 ID
        """
        with self.lock:
            if job_id not in self.jobs:
                raise KeyError(f"존재하지 않는 작업 ID: {job_id}")
            
            job = self.jobs[job_id]
            job.fail(error)
            
            if job_id in self.active_jobs:
                del self.active_jobs[job_id]
            
            self.completed_jobs[job_id] = job
            self._clean_old_jobs()
        
        logger.error(f"작업 실패: {job_id} - {error}")
    
    def cancel_job(self, job_id: str) -> None:
        """작업 취소 처리
        
        Args:
            job_id: 작업 ID
        
        Raises:
            KeyError: 존재하지 않는 작업 ID
        """
        with self.lock:
            if job_id not in self.jobs:
                raise KeyError(f"존재하지 않는 작업 ID: {job_id}")
            
            job = self.jobs[job_id]
            job.cancel()
            
            if job_id in self.active_jobs:
                del self.active_jobs[job_id]
            
            self.completed_jobs[job_id] = job
            self._clean_old_jobs()
        
        logger.debug(f"작업 취소: {job_id}")
    
    def update_job_progress(self, job_id: str, progress: int, total: int, current_item: str = None) -> None:
        """작업 진행 상태 업데이트
        
        Args:
            job_id: 작업 ID
            progress: 현재 진행 항목 수
            total: 전체 항목 수
            current_item: 현재 처리 중인 항목
        
        Raises:
            KeyError: 존재하지 않는 작업 ID
        """
        with self.lock:
            if job_id not in self.jobs:
                raise KeyError(f"존재하지 않는 작업 ID: {job_id}")
            
            job = self.jobs[job_id]
            job.update_progress(progress, total, current_item)
        
        logger.debug(f"작업 진행 업데이트: {job_id} - {progress}/{total}")
    
    def increment_job_progress(self, job_id: str, success: bool = True, current_item: str = None) -> None:
        """작업 진행 상태 증가
        
        Args:
            job_id: 작업 ID
            success: 성공 여부 (True: 성공 카운트 증가, False: 실패 카운트 증가)
            current_item: 현재 처리 중인 항목
        
        Raises:
            KeyError: 존재하지 않는 작업 ID
        """
        with self.lock:
            if job_id not in self.jobs:
                raise KeyError(f"존재하지 않는 작업 ID: {job_id}")
            
            job = self.jobs[job_id]
            job.progress += 1
            
            if success:
                job.success_count += 1
            else:
                job.failed_count += 1
            
            if current_item:
                job.current_item = current_item
        
        logger.debug(f"작업 진행 증가: {job_id} - {'성공' if success else '실패'} - {job.progress}/{job.total}")
    
    async def get_job(self, job_id: str) -> Optional[Job]:
        """작업 객체 가져오기
        
        Args:
            job_id: 작업 ID
        
        Returns:
            Optional[Job]: 작업 객체 또는 None (존재하지 않는 경우)
        """
        with self.lock:
            return self.jobs.get(job_id)
    
    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """작업 상태 가져오기
        
        Args:
            job_id: 작업 ID
        
        Returns:
            Optional[Dict[str, Any]]: 작업 상태 정보 또는 None (존재하지 않는 경우)
        """
        job = await self.get_job(job_id)
        return job.get_status_dict() if job else None
    
    async def get_active_jobs(self) -> List[Dict[str, Any]]:
        """활성 작업 목록 가져오기
        
        Returns:
            List[Dict[str, Any]]: 활성 작업 상태 목록
        """
        with self.lock:
            return [job.get_status_dict() for job in self.active_jobs.values()]
    
    def get_completed_jobs(self, limit: int = None) -> List[Dict[str, Any]]:
        """완료된 작업 목록 가져오기
        
        Args:
            limit: 최대 반환 개수
        
        Returns:
            List[Dict[str, Any]]: 완료된 작업 상태 목록
        """
        with self.lock:
            jobs = list(self.completed_jobs.values())
            jobs.sort(key=lambda j: j.completed_at if j.completed_at else datetime.now(), reverse=True)
            
            if limit:
                jobs = jobs[:limit]
            
            return [job.get_status_dict() for job in jobs]
    
    def get_all_jobs(self) -> List[Dict[str, Any]]:
        """모든 작업 목록 가져오기
        
        Returns:
            List[Dict[str, Any]]: 모든 작업 상태 목록
        """
        with self.lock:
            return [job.get_status_dict() for job in self.jobs.values()]
    
    def get_latest_job(self, job_type: str = None) -> Optional[Job]:
        """가장 최근 작업 가져오기
        
        Args:
            job_type: 작업 유형 필터 (None: 모든 유형)
        
        Returns:
            Optional[Job]: 가장 최근 작업 객체 또는 None (없는 경우)
        """
        with self.lock:
            jobs = []
            
            # 활성 작업 먼저 검색
            for job in self.active_jobs.values():
                if job_type is None or job.job_type == job_type:
                    jobs.append(job)
            
            # 활성 작업이 없으면 완료된 작업 검색
            if not jobs:
                for job in self.completed_jobs.values():
                    if job_type is None or job.job_type == job_type:
                        jobs.append(job)
            
            if not jobs:
                return None
            
            # 시작 시간 기준으로 정렬
            jobs.sort(key=lambda j: j.started_at if j.started_at else j.created_at, reverse=True)
            return jobs[0]
    
    def _clean_old_jobs(self) -> None:
        """오래된 작업 정리"""
        with self.lock:
            if len(self.completed_jobs) > self.max_history:
                # 완료 시간 기준으로 정렬
                jobs = list(self.completed_jobs.values())
                jobs.sort(key=lambda j: j.completed_at if j.completed_at else datetime.min)
                
                # 오래된 작업부터 삭제
                for job in jobs[:len(jobs) - self.max_history]:
                    if job.job_id in self.completed_jobs:
                        del self.completed_jobs[job.job_id]
                        
                        # 전체 작업에서도 삭제 (메모리 관리)
                        if job.job_id in self.jobs:
                            del self.jobs[job.job_id]
    
    def clear_completed_jobs(self) -> None:
        """완료된 작업 모두 삭제"""
        with self.lock:
            for job_id in list(self.completed_jobs.keys()):
                del self.completed_jobs[job_id]
                
                # 전체 작업에서도 삭제
                if job_id in self.jobs:
                    del self.jobs[job_id]
    
    def has_active_jobs(self, job_type: str = None) -> bool:
        """활성 작업이 있는지 확인
        
        Args:
            job_type: 작업 유형 필터 (None: 모든 유형)
        
        Returns:
            bool: 활성 작업 존재 여부
        """
        with self.lock:
            if job_type is None:
                return len(self.active_jobs) > 0
            
            for job in self.active_jobs.values():
                if job.job_type == job_type:
                    return True
            
            return False

# 글로벌 작업 관리자 인스턴스
job_manager = JobManager()