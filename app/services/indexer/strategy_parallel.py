"""
병렬 인덱싱 전략 모듈

ThreadPoolExecutor를 사용하여 여러 파일을 동시에 처리하는 병렬 인덱싱 전략을 구현합니다.
"""

import time
import traceback
from concurrent.futures import ThreadPoolExecutor

from app.config import config
from app.services.indexer.base import IndexingStrategy
from app.utils import DEFAULT_MAX_THREADS


class ParallelIndexingStrategy(IndexingStrategy):
    """병렬 인덱싱 전략 - ThreadPoolExecutor를 사용하여 여러 파일을 동시에 처리"""
    
    def process(self, indexer, media_files):
        """
        병렬 처리 방식으로 인덱싱 수행
        
        Args:
            indexer: 인덱서 서비스 인스턴스
            media_files: 처리할 미디어 파일 목록
        """
        try:
            max_workers = min(config.get("max_threads", DEFAULT_MAX_THREADS), 8)  # 최대값 제한
            indexer.log("INFO", f"병렬 처리 시작 (최대 {max_workers}개 스레드)")
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = []
                
                for file_info in media_files:
                    if not indexer.current_status["is_indexing"]:
                        break
                        
                    media_path = file_info["media_path"]
                    subtitle_path = file_info["subtitle_path"]
                    
                    # 미디어 파일 정보 저장 - 메인 스레드에서 처리
                    from app.database.media import upsert_media
                    media_id = upsert_media(media_path)
                    
                    if not media_id:
                        indexer.log("ERROR", f"미디어 ID를 가져올 수 없습니다: {media_path}")
                        continue
                    
                    # 병렬 작업 제출 - 스레드 안전한 버전 사용
                    future = executor.submit(indexer.thread_safe_process_subtitle, subtitle_path, media_id)
                    futures.append((future, media_path))
                
                # 완료된 작업 처리
                for i, (future, media_path) in enumerate(futures):
                    if not indexer.current_status["is_indexing"]:
                        break
                        
                    try:
                        # 일시 중지 확인
                        while indexer.is_paused and indexer.current_status["is_indexing"]:
                            time.sleep(1)
                            
                        # 현재 파일 표시
                        indexer.current_status["current_file"] = media_path
                        indexer.log("INFO", f"처리 중 ({i+1}/{len(futures)}): {media_path}")
                        
                        # 처리 결과 대기
                        subtitles_count = future.result()
                        
                        # 상태 업데이트
                        indexer.current_status["processed_files"] += 1
                        indexer.current_status["subtitle_count"] += subtitles_count
                        indexer._save_status()
                        
                        indexer.log("INFO", f"완료: {media_path} - {subtitles_count}개 자막 인덱싱됨")
                        
                    except Exception as e:
                        indexer.log("ERROR", f"파일 처리 중 오류: {str(e)} - {media_path}")
                        indexer.log("ERROR", traceback.format_exc())
                        
                        # 오류가 발생해도 처리된 파일 수 증가
                        indexer.current_status["processed_files"] += 1
                        indexer._save_status()
                    
        except Exception as e:
            indexer.log("ERROR", f"병렬 처리 중 오류 발생: {str(e)}")
            indexer.log("ERROR", traceback.format_exc()) 