"""
인덱싱 서비스 모듈

미디어 파일과 자막을 인덱싱하는 서비스 클래스입니다.
"""

import os
import re
import json
import time
from pathlib import Path
from datetime import datetime
from threading import Thread
from concurrent.futures import ThreadPoolExecutor, as_completed
import pysrt
from langdetect import detect, LangDetectException

from app.config import config
from app.database import db
from app.utils import (
    time_to_ms, remove_html_tags, detect_encoding, is_english_subtitle,
    get_file_extension, get_media_paths, get_estimated_completion_time,
    INDEXING_STATUS_FILE, DEFAULT_MAX_THREADS, MAX_LOG_ENTRIES
)
from app.utils.logging import get_indexer_logger

# 로거 설정
logger = get_indexer_logger()


class IndexerService:
    """인덱싱 서비스 클래스"""
    
    def __init__(self):
        """인덱서 초기화"""
        self.status_file = INDEXING_STATUS_FILE
        self.current_status = self._load_status() or {
            "is_indexing": False,
            "processed_files": 0,
            "total_files": 0,
            "current_file": "",
            "subtitle_count": 0,
            "log_messages": [],
            "pid": None,
            "last_updated": None
        }
        self.is_paused = False
        self.indexing_thread = None
        
        # 서버 시작 시 이전 인덱싱 상태 확인
        self._check_running_indexing()
    
    def _load_status(self):
        """저장된 인덱싱 상태 로드"""
        try:
            if os.path.exists(self.status_file):
                with open(self.status_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"상태 파일 로딩 오류: {str(e)}")
        return None
    
    def _save_status(self):
        """현재 인덱싱 상태를 파일에 저장"""
        try:
            # 현재 시간 추가
            self.current_status["last_updated"] = datetime.now().isoformat()
            self.current_status["is_paused"] = self.is_paused
            
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(self.current_status, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"상태 저장 오류: {str(e)}")
    
    def _check_running_indexing(self):
        """서버 시작 시 이전 인덱싱 프로세스 확인"""
        if self.current_status.get("is_indexing") and self.current_status.get("pid"):
            pid = self.current_status.get("pid")
            # PID가 여전히 실행 중인지 확인
            try:
                if os.name == 'nt':  # Windows
                    import ctypes
                    kernel32 = ctypes.windll.kernel32
                    handle = kernel32.OpenProcess(1, False, pid)
                    if handle == 0:
                        self._reset_indexing_status("이전 인덱싱 프로세스가 종료됨")
                    else:
                        kernel32.CloseHandle(handle)
                else:  # Unix/Linux/MacOS
                    os.kill(pid, 0)
            except (OSError, ProcessLookupError):
                # 프로세스가 존재하지 않음
                self._reset_indexing_status("이전 인덱싱 프로세스가 종료됨")
            else:
                # 마지막 업데이트 시간 확인
                if self.current_status.get("last_updated"):
                    try:
                        last_updated = datetime.fromisoformat(self.current_status["last_updated"])
                        now = datetime.now()
                        if (now - last_updated).total_seconds() > 300:  # 5분 이상 업데이트 없음
                            self._reset_indexing_status("인덱싱 프로세스가 응답하지 않음 (5분 이상 업데이트 없음)")
                    except (ValueError, TypeError):
                        pass
    
    def _reset_indexing_status(self, reason):
        """인덱싱 상태 초기화"""
        self.log("WARNING", f"인덱싱 상태 초기화: {reason}")
        self.current_status["is_indexing"] = False
        self.current_status["pid"] = None
        self._save_status()
    
    def log(self, level, message):
        """로그 메시지 추가 및 파일에 기록"""
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
            
        # 로그 추가할 때마다 상태 저장
        self._save_status()
    
    def log_indexing_event(self, event_type, details=None):
        """인덱싱 이벤트 로깅"""
        if event_type == "start":
            self.log("INFO", "인덱싱 시작")
        elif event_type == "complete":
            self.log("INFO", f"인덱싱 완료: {details.get('processed_files', 0)}개 파일 처리, {details.get('subtitle_count', 0)}개 자막 인덱싱됨")
        elif event_type == "file_start":
            self.log("INFO", f"파일 처리 중: {details.get('file_path', '')}")
        elif event_type == "file_complete":
            self.log("INFO", f"파일 처리 완료: {details.get('file_path', '')}")
        elif event_type == "subtitle_found":
            self.log("INFO", f"자막 발견: {details.get('subtitle_path', '')}")
        elif event_type == "subtitle_processed":
            self.log("INFO", f"자막 처리 완료: {details.get('subtitle_path', '')}, {details.get('lines_count', 0)}개 라인")
        elif event_type == "error":
            self.log("ERROR", f"오류 발생: {details.get('message', '')}")
        elif event_type == "skipped":
            self.log("INFO", f"건너뜀: {details.get('file_path', '')}, 사유: {details.get('reason', '')}")
    
    def get_status(self):
        """현재 인덱싱 상태 반환"""
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
                        eta = get_estimated_completion_time(processed, total, start_time)
                        if eta:
                            self.current_status["eta"] = eta
                        else:
                            self.current_status["eta"] = "계산 중..."
                except Exception:
                    self.current_status["eta"] = "계산 중..."
        
        return self.current_status
    
    def start_indexing(self, incremental=True):
        """인덱싱 작업 시작, incremental이 True이면 증분 인덱싱 수행"""
        if self.current_status["is_indexing"]:
            return {"error": "이미 인덱싱이 진행 중입니다."}

        # 일시정지 상태에서 재개하는 경우
        if self.is_paused:
            return self.resume_indexing()

        # 새로운 인덱싱 시작
        self.current_status = {
            "is_indexing": True,
            "is_paused": False,
            "processed_files": 0,
            "total_files": 0,
            "current_file": "",
            "subtitle_count": 0,
            "log_messages": [],
            "pid": os.getpid(),
            "start_time": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "incremental": incremental
        }
        
        self.log("INFO", f"인덱싱 시작 (증분 모드: {incremental})")
        self._save_status()
        
        # 인덱싱 스레드 시작
        self.indexing_thread = Thread(target=self._indexing_worker, args=(incremental,))
        self.indexing_thread.daemon = True
        self.indexing_thread.start()
        
        return {"status": "started", "message": "인덱싱이 시작되었습니다."}
    
    def stop_indexing(self):
        """인덱싱 작업 중지"""
        if not self.current_status["is_indexing"]:
            return {"error": "현재 인덱싱이 진행 중이 아닙니다."}
        
        self.log("INFO", "인덱싱 중지 요청")
        self.current_status["is_indexing"] = False
        self._save_status()
        
        return {"status": "stopped", "message": "인덱싱이 중지되었습니다."}
    
    def pause_indexing(self):
        """인덱싱 작업 일시 중지"""
        if not self.current_status["is_indexing"]:
            return {"error": "현재 인덱싱이 진행 중이 아닙니다."}
        
        if self.is_paused:
            return {"error": "이미 일시 중지된 상태입니다."}
        
        self.is_paused = True
        self.log("INFO", "인덱싱 일시 중지")
        self._save_status()
        
        return {"status": "paused", "message": "인덱싱이 일시 중지되었습니다."}
    
    def resume_indexing(self):
        """일시 중지된 인덱싱 작업 재개"""
        if not self.is_paused:
            return {"error": "일시 중지된 인덱싱이 없습니다."}
        
        self.is_paused = False
        self.current_status["is_indexing"] = True
        self.log("INFO", "인덱싱 재개")
        self._save_status()
        
        # 스레드가 종료된 경우 재시작
        if not self.indexing_thread or not self.indexing_thread.is_alive():
            incremental = self.current_status.get("incremental", True)
            self.indexing_thread = Thread(target=self._indexing_worker, args=(incremental,))
            self.indexing_thread.daemon = True
            self.indexing_thread.start()
        
        return {"status": "resumed", "message": "인덱싱이 재개되었습니다."}
    
    def scan_directory(self, incremental=True):
        """
        지정된 디렉토리를 스캔하여 미디어 파일 목록 생성
        
        Args:
            incremental (bool): 증분 인덱싱 여부
            
        Returns:
            list: 처리할 미디어 파일 목록
        """
        root_dir = config.get("root_dir", "")
        if not root_dir or not os.path.exists(root_dir):
            self.log("ERROR", f"루트 디렉토리가 존재하지 않습니다: {root_dir}")
            return []
        
        media_extensions = config.get("media_extensions", [".mp4", ".mkv", ".avi"])
        subtitle_extension = config.get("subtitle_extension", ".srt")
        
        # 이미 인덱싱된 파일 목록 (증분 인덱싱에 사용)
        indexed_files = set()
        if incremental:
            indexed_files = set(db.get_indexed_media_paths())
            self.log("INFO", f"이미 인덱싱된 파일: {len(indexed_files)}개")
        
        media_files = []
        total_scanned = 0
        
        self.log("INFO", f"디렉토리 스캔 시작: {root_dir}")
        
        # 모든 파일 스캔
        for dirpath, dirnames, filenames in os.walk(root_dir):
            for filename in filenames:
                if self.is_paused:
                    while self.is_paused and self.current_status["is_indexing"]:
                        time.sleep(1)
                
                if not self.current_status["is_indexing"]:
                    self.log("INFO", "스캔 중지됨")
                    return media_files
                
                filepath = os.path.join(dirpath, filename)
                file_ext = get_file_extension(filepath)
                
                # 미디어 파일 확인
                if file_ext in media_extensions:
                    total_scanned += 1
                    
                    # 증분 인덱싱이고 이미 인덱싱된 파일이면 건너뜀
                    if incremental and filepath in indexed_files:
                        continue
                    
                    # 매칭되는 자막 파일 확인
                    media_path, subtitle_path = get_media_paths(filepath, subtitle_extension)
                    
                    # 자막 파일이 존재하면 목록에 추가
                    if subtitle_path and os.path.exists(subtitle_path):
                        media_files.append({
                            "media_path": media_path,
                            "subtitle_path": subtitle_path
                        })
        
        self.log("INFO", f"디렉토리 스캔 완료: 총 {total_scanned}개 미디어 파일 발견, {len(media_files)}개 새 파일 처리 예정")
        
        return media_files
    
    def process_subtitle(self, subtitle_path, media_id):
        """
        자막 파일 처리 및 데이터베이스에 저장
        
        Args:
            subtitle_path (str): 자막 파일 경로
            media_id (int): 미디어 파일 ID
            
        Returns:
            int: 처리된 자막 라인 수
        """
        try:
            # 파일 인코딩 탐지
            encoding = detect_encoding(subtitle_path)
            
            # 자막 파일 로드
            subtitles = pysrt.open(subtitle_path, encoding=encoding)
            
            # 자막 중복 제거를 위한 해시 세트
            processed_lines = set()
            subtitles_count = 0
            
            # 영어 자막 비율 확인을 위한 샘플링
            min_english_ratio = config.get("min_english_ratio", 0.2)
            
            # 자막 라인 처리
            for subtitle in subtitles:
                if not self.current_status["is_indexing"]:
                    break
                    
                # HTML 태그 제거
                text = remove_html_tags(subtitle.text)
                
                # 이미 처리한 텍스트는 건너뜀 (중복 제거)
                if text in processed_lines:
                    continue
                
                processed_lines.add(text)
                
                # 자막 시간 정보 (밀리초 단위)
                start_time = time_to_ms(subtitle.start)
                end_time = time_to_ms(subtitle.end)
                
                # 자막을 데이터베이스에 저장
                db.add_subtitle(media_id, text, start_time, end_time)
                subtitles_count += 1
            
            return subtitles_count
                
        except Exception as e:
            self.log("ERROR", f"자막 처리 중 오류: {str(e)} - {subtitle_path}")
            return 0
    
    def _indexing_worker(self, incremental=True):
        """
        인덱싱 작업 수행 (스레드에서 실행)
        
        Args:
            incremental (bool): 증분 인덱싱 여부
        """
        try:
            # 미디어 파일 스캔
            media_files = self.scan_directory(incremental)
            self.current_status["total_files"] = len(media_files)
            self._save_status()
            
            if not media_files:
                self.log("INFO", "처리할 미디어 파일이 없습니다.")
                self.current_status["is_indexing"] = False
                self._save_status()
                return
            
            # 인덱싱 전략 선택
            indexing_strategy = config.get("indexing_strategy", "standard")
            self.log("INFO", f"인덱싱 전략: {indexing_strategy}")
            
            if indexing_strategy == "batch":
                self._process_batch(media_files)
            elif indexing_strategy == "parallel":
                self._process_parallel(media_files)
            elif indexing_strategy == "delayed_language":
                self._process_delayed_language(media_files)
            else:  # 기본: standard
                self._process_standard(media_files)
            
            # 인덱싱 완료 후 정리
            self.log("INFO", f"인덱싱 완료: {self.current_status['processed_files']}개 파일, {self.current_status['subtitle_count']}개 자막 처리됨")
            self.current_status["is_indexing"] = False
            self._save_status()
            
        except Exception as e:
            self.log("ERROR", f"인덱싱 작업 중 오류 발생: {str(e)}")
            self.current_status["is_indexing"] = False
            self._save_status()
    
    def _process_standard(self, media_files):
        """표준 인덱싱 처리 - 파일을 하나씩 순차적으로 처리"""
        for i, file_info in enumerate(media_files):
            if not self.current_status["is_indexing"]:
                break
                
            # 일시 중지 확인
            while self.is_paused and self.current_status["is_indexing"]:
                time.sleep(1)
                
            media_path = file_info["media_path"]
            subtitle_path = file_info["subtitle_path"]
            
            self.current_status["current_file"] = media_path
            self.log("INFO", f"처리 중 ({i+1}/{len(media_files)}): {media_path}")
            
            try:
                # 미디어 파일 정보 저장
                media_id = db.add_media_file(media_path)
                
                # 자막 처리
                subtitles_count = self.process_subtitle(subtitle_path, media_id)
                
                # 상태 업데이트
                self.current_status["processed_files"] += 1
                self.current_status["subtitle_count"] += subtitles_count
                self._save_status()
                
                self.log("INFO", f"완료: {media_path} - {subtitles_count}개 자막 인덱싱됨")
                
            except Exception as e:
                self.log("ERROR", f"파일 처리 중 오류: {str(e)} - {media_path}")
    
    def _process_batch(self, media_files):
        """배치 처리 - 미디어 파일을 먼저 모두 등록한 후 자막 처리"""
        try:
            # 1단계: 모든 미디어 파일을 데이터베이스에 등록
            self.log("INFO", "1단계: 미디어 파일 등록 중...")
            media_ids = {}
            
            for i, file_info in enumerate(media_files):
                if not self.current_status["is_indexing"]:
                    return
                    
                media_path = file_info["media_path"]
                media_id = db.add_media_file(media_path)
                media_ids[media_path] = media_id
                
                if i % 10 == 0:  # 진행 상황 주기적 업데이트
                    self.log("INFO", f"미디어 파일 등록 진행 중: {i+1}/{len(media_files)}")
            
            # 2단계: 자막 처리
            self.log("INFO", "2단계: 자막 처리 중...")
            for i, file_info in enumerate(media_files):
                if not self.current_status["is_indexing"]:
                    return
                    
                media_path = file_info["media_path"]
                subtitle_path = file_info["subtitle_path"]
                
                self.current_status["current_file"] = media_path
                self.log("INFO", f"처리 중 ({i+1}/{len(media_files)}): {media_path}")
                
                try:
                    # 자막 처리
                    subtitles_count = self.process_subtitle(subtitle_path, media_ids[media_path])
                    
                    # 상태 업데이트
                    self.current_status["processed_files"] += 1
                    self.current_status["subtitle_count"] += subtitles_count
                    self._save_status()
                    
                    self.log("INFO", f"완료: {media_path} - {subtitles_count}개 자막 인덱싱됨")
                    
                except Exception as e:
                    self.log("ERROR", f"파일 처리 중 오류: {str(e)} - {media_path}")
        except Exception as e:
            self.log("ERROR", f"배치 처리 중 오류 발생: {str(e)}")
    
    def _process_parallel(self, media_files):
        """병렬 처리 - 여러 파일을 동시에 처리"""
        try:
            max_workers = config.get("max_threads", DEFAULT_MAX_THREADS)
            self.log("INFO", f"병렬 처리 시작 (최대 {max_workers}개 스레드)")
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = []
                
                for file_info in media_files:
                    if not self.current_status["is_indexing"]:
                        break
                        
                    media_path = file_info["media_path"]
                    subtitle_path = file_info["subtitle_path"]
                    
                    # 미디어 파일 정보 저장
                    media_id = db.add_media_file(media_path)
                    
                    # 병렬 작업 제출
                    future = executor.submit(self.process_subtitle, subtitle_path, media_id)
                    futures.append((future, media_path))
                
                # 완료된 작업 처리
                for future, media_path in futures:
                    if not self.current_status["is_indexing"]:
                        break
                        
                    try:
                        subtitles_count = future.result()
                        
                        # 상태 업데이트
                        self.current_status["processed_files"] += 1
                        self.current_status["subtitle_count"] += subtitles_count
                        self._save_status()
                        
                        self.log("INFO", f"완료: {media_path} - {subtitles_count}개 자막 인덱싱됨")
                        
                    except Exception as e:
                        self.log("ERROR", f"파일 처리 중 오류: {str(e)} - {media_path}")
                    
        except Exception as e:
            self.log("ERROR", f"병렬 처리 중 오류 발생: {str(e)}")
    
    def _process_delayed_language(self, media_files):
        """지연 언어 감지 처리 - 언어 감지를 최소화"""
        try:
            # 자막 파일 먼저 필터링
            self.log("INFO", "자막 파일 필터링 중...")
            filtered_files = []
            
            for file_info in media_files:
                if not self.current_status["is_indexing"]:
                    break
                    
                media_path = file_info["media_path"]
                subtitle_path = file_info["subtitle_path"]
                
                try:
                    # 자막 파일이 영어인지 확인
                    if is_english_subtitle(subtitle_path):
                        filtered_files.append(file_info)
                    else:
                        self.log("INFO", f"영어 자막이 아님, 건너뜀: {subtitle_path}")
                except Exception as e:
                    self.log("ERROR", f"자막 언어 확인 중 오류: {str(e)} - {subtitle_path}")
            
            # 필터링된 파일 처리
            self.log("INFO", f"영어 자막 파일 {len(filtered_files)}개 처리 중...")
            
            for i, file_info in enumerate(filtered_files):
                if not self.current_status["is_indexing"]:
                    break
                    
                media_path = file_info["media_path"]
                subtitle_path = file_info["subtitle_path"]
                
                self.current_status["current_file"] = media_path
                self.log("INFO", f"처리 중 ({i+1}/{len(filtered_files)}): {media_path}")
                
                try:
                    # 미디어 파일 정보 저장
                    media_id = db.add_media_file(media_path)
                    
                    # 자막 처리
                    subtitles_count = self.process_subtitle(subtitle_path, media_id)
                    
                    # 상태 업데이트
                    self.current_status["processed_files"] += 1
                    self.current_status["subtitle_count"] += subtitles_count
                    self._save_status()
                    
                    self.log("INFO", f"완료: {media_path} - {subtitles_count}개 자막 인덱싱됨")
                    
                except Exception as e:
                    self.log("ERROR", f"파일 처리 중 오류: {str(e)} - {media_path}")
        except Exception as e:
            self.log("ERROR", f"지연 언어 감지 처리 중 오류 발생: {str(e)}")


# IndexerService의 인스턴스 생성
indexer_service = IndexerService()