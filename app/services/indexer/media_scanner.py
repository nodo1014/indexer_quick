"""
미디어 스캐너 모듈

파일 시스템을 스캔하여 미디어 파일과 자막 파일을 찾는 기능을 제공합니다.
"""

import os
import time
import glob
from typing import List, Dict, Any, Optional, Tuple, Callable

from app.config import config
from app.utils.helpers import get_file_extension
from app.utils.logging import get_indexer_logger

logger = get_indexer_logger()

class MediaScanner:
    """미디어 파일 스캐너 클래스"""
    
    def __init__(self, status_handler=None):
        """
        스캐너 초기화
        
        Args:
            status_handler: 상태 관리자 인스턴스 (로깅용)
        """
        self.status_handler = status_handler
        self.root_dir = config.get("root_dir", "")
        self.media_extensions = config.get("media_extensions", [".mp4", ".mkv", ".avi"])
        self.subtitle_extension = config.get("subtitle_extension", ".srt")
    
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
    
    def scan_directory(self, incremental: bool = True, is_indexing_func: Optional[Callable[[], bool]] = None) -> List[Dict[str, Any]]:
        """
        지정된 디렉토리를 스캔하여 미디어 파일 목록 생성
        
        Args:
            incremental: 증분 인덱싱 여부
            is_indexing_func: 인덱싱 중단 여부를 확인하는 함수
            
        Returns:
            list: 처리할 미디어 파일 목록
        """
        if not self.root_dir or not os.path.exists(self.root_dir):
            self.log("ERROR", f"루트 디렉토리가 존재하지 않습니다: {self.root_dir}")
            print(f"오류: 루트 디렉토리가 존재하지 않습니다: {self.root_dir}")
            return []
        
        # 이미 인덱싱된 파일 목록 (증분 인덱싱에 사용)
        indexed_files = set()
        if incremental:
            from app.database.media import get_indexed_media_paths
            indexed_files = set(get_indexed_media_paths())
            self.log("INFO", f"이미 인덱싱된 파일: {len(indexed_files)}개")
            print(f"\n===== 인덱싱 모드: {'증분(새 파일만)' if incremental else '전체'} =====")
            print(f"이미 인덱싱된 파일: {len(indexed_files)}개")
        else:
            print(f"\n===== 인덱싱 모드: 전체 =====")
        
        media_files = []
        total_scanned = 0
        skipped_count = 0
        
        self.log("INFO", f"디렉토리 스캔 시작: {self.root_dir}")
        print(f"디렉토리 스캔 시작: {self.root_dir}")
        
        # 스캔 시작 시간
        scan_start_time = time.time()
        last_progress_update = time.time()
        progress_update_interval = 2.0  # 2초마다 진행 상황 업데이트
        
        # 모든 파일 스캔
        for dirpath, dirnames, filenames in os.walk(self.root_dir):
            for filename in filenames:
                # CPU 과점유 방지
                time.sleep(0.01)
                
                # 인덱싱 중단 확인
                if is_indexing_func and not is_indexing_func():
                    self.log("INFO", "스캔 중지됨")
                    print("\n스캔이 중지되었습니다.")
                    return media_files
                
                filepath = os.path.join(dirpath, filename)
                file_ext = get_file_extension(filepath)
                
                # 미디어 파일 확인
                if file_ext in self.media_extensions:
                    total_scanned += 1
                    
                    # 주기적으로 진행 상황 업데이트
                    current_time = time.time()
                    if current_time - last_progress_update > progress_update_interval:
                        print(f"\r스캔 중: {total_scanned}개 미디어 파일 발견, {len(media_files)}개 처리 대상 식별됨...", end="")
                        last_progress_update = current_time
                    
                    # 증분 인덱싱이고 이미 인덱싱된 파일이면 건너뜀
                    if incremental and filepath in indexed_files:
                        skipped_count += 1
                        continue
                    
                    # 자막 파일 확인
                    subtitle_files = self.find_subtitle_files(filepath)
                    
                    # 자막 파일이 존재하면 목록에 추가
                    if subtitle_files:
                        # 데이터베이스에 미디어 파일 정보 저장
                        from app.database.media import upsert_media
                        media_id = upsert_media(filepath)
                        
                        if media_id:
                            media_files.append({
                                "id": media_id,
                                "path": filepath,
                                "subtitle_files": subtitle_files
                            })
        
        # 스캔 완료 시간 및 통계
        scan_time = time.time() - scan_start_time
        self.log("INFO", f"스캔 완료: {total_scanned}개 미디어 파일 스캔, {len(media_files)}개 처리 대상 식별됨")
        
        print(f"\n===== 스캔 완료 =====")
        print(f"스캔된 미디어 파일: {total_scanned}개")
        print(f"처리 대상 파일: {len(media_files)}개")
        if incremental:
            print(f"건너뛴 파일 (이미 인덱싱됨): {skipped_count}개")
        print(f"스캔 소요 시간: {scan_time:.2f}초")
        print("=====================")
        
        # 인덱싱할 파일이 없는 경우
        if not media_files:
            if incremental:
                self.log("INFO", "인덱싱할 새 파일이 없습니다.")
                print("\n인덱싱할 새 파일이 없습니다. 모든 파일이 이미 처리되었습니다.")
            else:
                self.log("INFO", "인덱싱할 파일이 없습니다.")
                print("\n인덱싱할 파일이 없습니다. 자막 파일이 없는 것 같습니다.")
        
        return media_files
    
    def find_subtitle_files(self, media_path: str) -> List[str]:
        """
        미디어 파일과 관련된 자막 파일을 찾습니다.
        
        Args:
            media_path: 미디어 파일 경로
            
        Returns:
            list: 자막 파일 경로 목록
        """
        media_dir = os.path.dirname(media_path)
        media_filename = os.path.basename(media_path)
        media_basename = os.path.splitext(media_filename)[0]
        
        # 자막 파일 패턴 목록
        patterns = [
            # 기본 패턴 (동일한 이름)
            f"{media_basename}{self.subtitle_extension}",
            
            # 언어 코드가 포함된 패턴
            f"{media_basename}.en{self.subtitle_extension}",
            f"{media_basename}.eng{self.subtitle_extension}",
            f"{media_basename}_eng{self.subtitle_extension}",
            f"{media_basename}_en{self.subtitle_extension}",
            f"{media_basename}.english{self.subtitle_extension}",
            
            # 기타 일반적인 패턴
            f"{media_basename}.*{self.subtitle_extension}"
        ]
        
        subtitle_files = []
        
        for pattern in patterns:
            # 전체 경로 패턴
            full_pattern = os.path.join(media_dir, pattern)
            
            # glob을 사용하여 패턴과 일치하는 파일 찾기
            matching_files = glob.glob(full_pattern)
            
            # 결과 목록에 추가
            for file_path in matching_files:
                if os.path.exists(file_path) and file_path not in subtitle_files:
                    subtitle_files.append(file_path)
        
        return subtitle_files
