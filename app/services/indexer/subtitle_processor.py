"""
자막 처리 모듈

자막 파일을 처리하고 데이터베이스에 저장하는 기능을 제공합니다.
"""

import os
import time
import shutil
import sqlite3
import tempfile
from typing import Dict, Any, Optional, List

from app.utils.logging import get_indexer_logger
from app.utils import remove_html_tags, detect_encoding, is_english_subtitle
from app.utils.helpers import time_to_ms

logger = get_indexer_logger()

class SubtitleProcessor:
    """자막 처리 클래스"""
    
    def __init__(self, status_handler=None):
        """
        자막 처리기 초기화
        
        Args:
            status_handler: 상태 관리자 인스턴스 (로깅용)
        """
        self.status_handler = status_handler
    
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
    
    def process_subtitle(self, subtitle_path: str, media_id: int) -> int:
        """
        자막 파일 처리 및 데이터베이스에 저장
        
        Args:
            subtitle_path: 자막 파일 경로
            media_id: 미디어 파일 ID
            
        Returns:
            int: 처리된 자막 라인 수
        """
        import pysrt
        
        try:
            # 파일 존재 확인
            if not os.path.exists(subtitle_path):
                self.log("ERROR", f"자막 파일이 존재하지 않습니다: {subtitle_path}")
                return 0
                
            # 파일 크기 확인 - 0바이트 파일은 건너뜀
            if os.path.getsize(subtitle_path) == 0:
                self.log("WARNING", f"빈 자막 파일입니다: {subtitle_path}")
                return 0
            
            # 파일 인코딩 탐지
            encoding = detect_encoding(subtitle_path)
            
            # 변환된 임시 파일 경로
            temp_subtitle_path = None
            
            # 다양한 인코딩 시도
            encodings_to_try = [
                encoding,  # 감지된 인코딩 먼저 시도
                'utf-8', 'utf-8-sig',  # UTF-8 버전들
                'euc-kr', 'cp949',     # 한국어 인코딩
                'latin-1', 'iso-8859-1', # 서양어 인코딩
                'ascii'                 # 기본 ASCII
            ]
            
            # 중복 제거
            encodings_to_try = list(dict.fromkeys(encodings_to_try))
            
            # 인코딩 순회적으로 시도
            subtitles = None
            success_encoding = None
            
            for enc in encodings_to_try:
                try:
                    # 자막 파일 로드 시도
                    subtitles = pysrt.open(subtitle_path, encoding=enc)
                    success_encoding = enc
                    break
                except UnicodeDecodeError:
                    continue
                except Exception:
                    continue
            
            # 성공한 경우에만 한 번 로깅
            if success_encoding:
                self.log("INFO", f"자막 파일 로드 성공 (인코딩: {success_encoding}) - {subtitle_path}")
            
            # 모든 인코딩 시도 실패 시 자막 변환 모듈 사용
            if subtitles is None:
                self.log("WARNING", f"모든 인코딩 시도 실패 - {subtitle_path}")
                
                # 자막 변환 모듈 임포트
                from app.subtitle.encodings.converter import convert_subtitle_encoding
                
                # 임시 디렉토리 생성
                temp_dir = tempfile.mkdtemp(prefix="subtitle_convert_")
                
                # 기본 변환 설정
                conversion_config = {
                    'media_dir': os.path.dirname(subtitle_path),
                    'output_dir': temp_dir,
                    'delete_original': False,  # 원본 파일 유지
                    'convert_broken': True,    # 깨진 인코딩 변환
                    'extract_english': False,  # 영어 자막 추출 안 함
                    'process_multi': False     # 다중 언어 처리 안 함
                }
                
                # 자막 변환 실행
                result = convert_subtitle_encoding(subtitle_path, conversion_config)
                
                if result and 'output_path' in result and result['output_path'] and os.path.exists(result['output_path']):
                    temp_subtitle_path = result['output_path']
                    # 상세 경로 정보 제거하고 간결하게 로깅
                    self.log("INFO", f"자막 변환 성공: {result.get('encoding', '알 수 없음')} -> utf-8 - {subtitle_path}")
                    
                    # 변환된 파일로 다시 시도
                    try:
                        subtitles = pysrt.open(temp_subtitle_path, encoding='utf-8')
                    except Exception as conv_err:
                        self.log("ERROR", f"변환된 자막 파일 로드 실패: {str(conv_err)} - {temp_subtitle_path}")
                        # 임시 파일 정리
                        if os.path.exists(temp_dir):
                            try:
                                shutil.rmtree(temp_dir)
                            except Exception:
                                pass
                        return 0
                else:
                    self.log("ERROR", f"자막 변환 실패 - {subtitle_path}")
                    # 임시 파일 정리
                    if 'temp_dir' in locals() and os.path.exists(temp_dir):
                        try:
                            shutil.rmtree(temp_dir)
                        except Exception:
                            pass
                    return 0
            
            # 자막이 로드되지 않았으면 0 반환
            if not subtitles:
                self.log("ERROR", f"자막을 로드할 수 없습니다: {subtitle_path}")
                return 0
                
            # 자막 라인이 없거나 비어있는 경우
            if len(subtitles) == 0:
                self.log("WARNING", f"자막 라인이 없습니다: {subtitle_path}")
                return 0
            
            # 자막 중복 제거를 위한 해시 세트
            processed_lines = set()
            subtitles_count = 0
            
            # 자막 라인 처리
            from app.database.subtitles import insert_subtitle
            
            # 처리 시간 제한 - 매우 큰 파일의 경우
            max_processing_time = 600  # 최대 10분
            start_time = time.time()
            
            # 인덱싱 상태 확인 함수
            is_indexing = lambda: True
            if self.status_handler:
                is_indexing = lambda: self.status_handler.current_status.get("is_indexing", True)
            
            for subtitle in subtitles:
                # 최대 처리 시간 초과 확인
                if time.time() - start_time > max_processing_time:
                    self.log("WARNING", f"최대 처리 시간 초과, 처리 중단: {subtitle_path}")
                    break
                    
                if not is_indexing():
                    break
                    
                # HTML 태그 제거
                text = remove_html_tags(subtitle.text)
                
                # 비어있는 텍스트는 건너뜀
                if not text or text.isspace():
                    continue
                
                # 이미 처리한 텍스트는 건너뛰 (중복 제거)
                if text in processed_lines:
                    continue
                
                processed_lines.add(text)
                
                # 자막 시간 정보 (밀리초 단위)
                start_time_ms = time_to_ms(subtitle.start)
                end_time_ms = time_to_ms(subtitle.end)
                
                # 시간 텍스트 형식 (HH:MM:SS,mmm)
                start_text = str(subtitle.start)
                end_text = str(subtitle.end)
                
                # 자막 라인 저장 - database.subtitles 모듈의 insert_subtitle 함수 사용
                max_db_retries = 3
                db_retry_count = 0
                insert_success = False
                
                while db_retry_count < max_db_retries and not insert_success:
                    try:
                        # 데이터베이스 삽입 시도
                        insert_subtitle(media_id, start_time_ms, end_time_ms, text, 'en', start_text, end_text)
                        subtitles_count += 1
                        insert_success = True
                    except sqlite3.OperationalError as db_err:
                        db_retry_count += 1
                        error_msg = str(db_err).lower()
                        
                        # 데이터베이스 잠금 또는 손상 오류인 경우 재시도
                        if "locked" in error_msg or "malformed" in error_msg or "busy" in error_msg:
                            retry_delay = db_retry_count * 0.5  # 재시도마다 대기 시간 증가
                            # 마지막 시도에서만 로깅하도록 변경
                            if db_retry_count == max_db_retries:
                                self.log("WARNING", f"자막 삽입 재시도 실패 ({max_db_retries}/{max_db_retries}): {error_msg}")
                            time.sleep(retry_delay)
                        else:
                            # 다른 유형의 오류는 재시도하지 않음
                            self.log("ERROR", f"자막 삽입 오류: {error_msg}")
                            break
                    except Exception as e:
                        # 기타 예외 처리
                        self.log("ERROR", f"자막 삽입 중 예외 발생: {str(e)}")
                        break
            
            # 임시 파일 정리
            if temp_subtitle_path and os.path.exists(os.path.dirname(temp_subtitle_path)):
                try:
                    shutil.rmtree(os.path.dirname(temp_subtitle_path))
                except Exception:
                    pass
            
            # 처리 결과 로깅 - 최종 결과만 로깅하고 처리 시간 추가
            processing_time = time.time() - start_time
            self.log("INFO", f"자막 처리 완료: {subtitle_path} - {subtitles_count}개 라인 처리 ({processing_time:.2f}초)")
            
            return subtitles_count
                
        except Exception as e:
            self.log("ERROR", f"자막 처리 중 오류 발생: {str(e)} - {subtitle_path}")
            return 0
    
    def detect_subtitle_language(self, subtitle_path: str) -> str:
        """
        자막 파일의 언어 감지
        
        Args:
            subtitle_path: 자막 파일 경로
            
        Returns:
            str: 감지된 언어 코드 (기본값: 'en')
        """
        try:
            # 영어 자막 여부 확인
            is_english = is_english_subtitle(subtitle_path)
            return 'en' if is_english else 'ko'
        except Exception as e:
            self.log("WARNING", f"자막 언어 감지 중 오류: {str(e)} - {subtitle_path}")
            return 'en'  # 기본값은 영어
