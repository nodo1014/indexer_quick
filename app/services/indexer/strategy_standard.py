"""
표준 인덱싱 전략 모듈

파일을 하나씩 순차적으로 처리하는 표준 인덱싱 전략을 구현합니다.
"""

import time
import traceback

from app.services.indexer.indexing_strategy import IndexingStrategy


class StandardIndexingStrategy(IndexingStrategy):
    """표준 인덱싱 전략 - 파일을 하나씩 순차적으로 처리"""
    
    def process(self, indexer, media_files):
        """
        파일을 하나씩 순차적으로 처리하는 표준 인덱싱 수행
        
        Args:
            indexer: 인덱서 서비스 인스턴스
            media_files: 처리할 미디어 파일 목록
        """
        indexer.log("INFO", f"표준 인덱싱 시작: {len(media_files)}개 파일 처리 예정")
        
        # 진행 상황 표시 변수
        total_files = len(media_files)
        process_start_time = time.time()
        last_progress_log = time.time()
        progress_interval = 60  # 진행 상황 로그 간격 (초) - 30초에서 60초로 증가
        
        for i, file_info in enumerate(media_files):
            if not indexer.current_status["is_indexing"]:
                indexer.log("INFO", "인덱싱 중지 요청으로 처리 중단")
                break
                
            # 일시 중지 확인
            while indexer.is_paused and indexer.current_status["is_indexing"]:
                time.sleep(1)
                
            media_path = file_info["media_path"]
            subtitle_path = file_info["subtitle_path"]
            
            indexer.current_status["current_file"] = media_path
            # 미디어 파일 처리 시작 로깅
            indexer.log("INFO", f"미디어 파일 처리 중 ({i+1}/{total_files}): {media_path}")
            
            try:
                # 미디어 파일 정보 저장
                from app.database.media import upsert_media
                media_id = upsert_media(media_path)
                
                if not media_id:
                    indexer.log("ERROR", f"미디어 파일 ID를 가져올 수 없습니다: {media_path}")
                    # 상태 업데이트
                    indexer.current_status["processed_files"] += 1
                    indexer._save_status()
                    continue
                
                # 자막 처리 - 표준 처리에서도 스레드 안전 버전 사용
                subtitles_count = indexer.thread_safe_process_subtitle(subtitle_path, media_id)
                
                # 상태 업데이트
                indexer.current_status["processed_files"] += 1
                indexer.current_status["subtitle_count"] += subtitles_count
                indexer._save_status()
                
                # 미디어 파일 처리 완료 로깅
                indexer.log("INFO", f"미디어 파일 처리 완료: {media_path} - {subtitles_count}개 자막 인덱싱됨")
                
            except Exception as e:
                indexer.log("ERROR", f"파일 처리 중 오류: {str(e)} - {media_path}")
                
                # 오류가 발생해도 처리된 파일 수 증가
                indexer.current_status["processed_files"] += 1
                indexer._save_status()
                
                # 오류 발생 후 잠시 대기 (0.5초)
                time.sleep(0.5)
            
            # 진행 상황 로그 추가 - 간격을 늘려 로깅 빈도 감소
            if time.time() - last_progress_log >= progress_interval:
                elapsed_time = time.time() - process_start_time
                if i > 0 and elapsed_time > 0:
                    files_per_second = i / elapsed_time
                    estimated_total_time = total_files / files_per_second if files_per_second > 0 else 0
                    estimated_remaining = max(0, estimated_total_time - elapsed_time)
                    
                    # 시간 형식 변환
                    elapsed_str = indexer._format_time(elapsed_time)
                    remaining_str = indexer._format_time(estimated_remaining)
                    
                    progress = int((i / total_files) * 100)
                    indexer.current_status["progress"] = progress
                    indexer.current_status["status_message"] = f"인덱싱 진행 중: {progress}%"
                    indexer._save_status()
                    
                    indexer.log("INFO", f"인덱싱 진행 상황: {i}/{total_files} ({progress}%), "
                                       f"경과: {elapsed_str}, 예상 남은 시간: {remaining_str}")
                last_progress_log = time.time()
        
        # 처리 완료 후 최종 로그
        elapsed_time = time.time() - process_start_time
        elapsed_str = indexer._format_time(elapsed_time)
        
        indexer.log("INFO", f"인덱싱 완료: {total_files}개 파일, {indexer.current_status['subtitle_count']}개 자막, 소요 시간: {elapsed_str}")


# IndexerService 인스턴스 생성 (서비스 싱글톤)
from app.services.indexer.indexing_service import IndexingService
indexer_service = IndexingService()