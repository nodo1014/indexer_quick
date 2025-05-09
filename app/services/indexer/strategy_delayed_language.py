"""
지연 언어 감지 인덱싱 전략 모듈

자막 파일의 언어를 먼저 확인하여 필터링한 후 처리하는 전략을 구현합니다.
"""

import time
import traceback

from app.services.indexer.base import IndexingStrategy
from app.utils import is_english_subtitle


class DelayedLanguageIndexingStrategy(IndexingStrategy):
    """지연 언어 감지 인덱싱 전략 - 언어 감지를 최소화"""
    
    def process(self, indexer, media_files):
        """
        지연 언어 감지 방식으로 인덱싱 수행
        
        Args:
            indexer: 인덱서 서비스 인스턴스
            media_files: 처리할 미디어 파일 목록
        """
        try:
            # 자막 파일 먼저 필터링
            indexer.log("INFO", "자막 파일 필터링 중...")
            filtered_files = []
            
            for file_info in media_files:
                if not indexer.current_status["is_indexing"]:
                    break
                    
                media_path = file_info["media_path"]
                subtitle_path = file_info["subtitle_path"]
                
                try:
                    # 자막 파일이 영어인지 확인
                    if is_english_subtitle(subtitle_path):
                        filtered_files.append(file_info)
                    else:
                        indexer.log("INFO", f"영어 자막이 아님, 건너뜀: {subtitle_path}")
                except Exception as e:
                    indexer.log("ERROR", f"자막 언어 확인 중 오류: {str(e)} - {subtitle_path}")
            
            # 필터링된 파일 처리
            indexer.log("INFO", f"영어 자막 파일 {len(filtered_files)}개 처리 중...")
            
            for i, file_info in enumerate(filtered_files):
                if not indexer.current_status["is_indexing"]:
                    break
                
                # 일시 중지 확인
                while indexer.is_paused and indexer.current_status["is_indexing"]:
                    time.sleep(1)
                    
                media_path = file_info["media_path"]
                subtitle_path = file_info["subtitle_path"]
                
                indexer.current_status["current_file"] = media_path
                indexer.log("INFO", f"처리 중 ({i+1}/{len(filtered_files)}): {media_path}")
                
                try:
                    # 미디어 파일 정보 저장
                    from app.database.media import upsert_media
                    media_id = upsert_media(media_path)
                    
                    if not media_id:
                        indexer.log("ERROR", f"미디어 ID를 가져올 수 없습니다: {media_path}")
                        # 상태 업데이트
                        indexer.current_status["processed_files"] += 1
                        indexer._save_status()
                        continue
                    
                    # 자막 처리 - 스레드 안전 버전 사용
                    subtitles_count = indexer.thread_safe_process_subtitle(subtitle_path, media_id)
                    
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
                    
                    # 오류 발생 후 잠시 대기 (0.5초)
                    time.sleep(0.5)
                    
        except Exception as e:
            indexer.log("ERROR", f"지연 언어 감지 처리 중 오류 발생: {str(e)}")
            indexer.log("ERROR", traceback.format_exc()) 