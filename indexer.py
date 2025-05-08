import os
import re
import pysrt
import chardet
from pathlib import Path
from bs4 import BeautifulSoup
from datetime import datetime
from langdetect import detect, LangDetectException
import re
import json
import time
from threading import Thread
from concurrent.futures import ThreadPoolExecutor, as_completed
from database import Database, load_config, save_config
import logging
import logging.handlers

# 로깅 설정
logger = logging.getLogger('indexer')
logger.setLevel(logging.DEBUG)

# 파일 핸들러 설정 - 일반 로그 (INFO 이상)
file_handler = logging.handlers.RotatingFileHandler(
    'indexer.log', 
    maxBytes=10485760,  # 10MB
    backupCount=5,
    encoding='utf-8'
)
file_handler.setLevel(logging.INFO)
file_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_format)

# 상세 로그 핸들러 (모든 로그 레벨)
debug_handler = logging.handlers.RotatingFileHandler(
    'indexer_verbose.log',
    maxBytes=20971520,  # 20MB
    backupCount=3,
    encoding='utf-8'
)
debug_handler.setLevel(logging.DEBUG)
debug_handler.setFormatter(file_format)

# 콘솔 핸들러
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(file_format)

# 핸들러 등록
logger.addHandler(file_handler)
logger.addHandler(debug_handler)
logger.addHandler(console_handler)

# SRT 시간을 밀리초로 변환하는 함수
def time_to_ms(time_obj):
    """pysrt의 SubRipTime 객체를 밀리초로 변환"""
    return (time_obj.hours * 3600 + time_obj.minutes * 60 + time_obj.seconds) * 1000 + time_obj.milliseconds

# HTML 태그 제거 함수
def remove_html_tags(text):
    """HTML 태그 제거"""
    soup = BeautifulSoup(f"<div>{text}</div>", 'html.parser')
    return soup.div.get_text()

# 영어 비율 확인
def is_english_subtitle(text, min_ratio=0.7):
    """텍스트가 주로 영어인지 판별"""
    # 간단한 영어 단어 패턴 (공백으로 구분된 영문자)
    english_word_pattern = re.compile(r'[a-zA-Z]+')
    
    # 모든 단어 추출
    words = text.lower().split()
    if not words:
        return False
        
    # 영어 단어 개수
    english_words = [w for w in words if english_word_pattern.fullmatch(w)]
    english_ratio = len(english_words) / len(words)
    
    return english_ratio >= min_ratio

# 자막 파일 인코딩 탐지
def detect_encoding(file_path):
    """파일의 인코딩 탐지"""
    with open(file_path, 'rb') as file:
        raw_data = file.read(4096)  # 샘플 데이터만 읽음
        result = chardet.detect(raw_data)
        return result['encoding']

# 인덱서 클래스
class Indexer:
    def __init__(self):
        self.db = Database()
        self.config = load_config()
        self.status_file = "indexing_status.json"
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
        self.is_paused = False  # 일시정지 상태 추가
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
            print(f"상태 파일 로딩 오류: {str(e)}")
        return None
    
    def _save_status(self):
        """현재 인덱싱 상태를 파일에 저장"""
        try:
            # 현재 시간 추가
            self.current_status["last_updated"] = datetime.now().isoformat()
            self.current_status["is_paused"] = self.is_paused  # 일시정지 상태 추가
            
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(self.current_status, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"상태 저장 오류: {str(e)}")
    
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
                    os.kill(pid, 0)  # 시그널을 보내지 않고 프로세스 존재 확인
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
        """로그 메시지 추가 및 파일에 기록
        
        Args:
            level: 로그 레벨 (INFO, WARNING, ERROR, DEBUG 등)
            message: 로그 메시지
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"{timestamp} {level}: {message}"
        
        # 상태 메모리에 로그 추가
        self.current_status["log_messages"].insert(0, log_entry)
        # 최대 100개의 로그만 유지
        if len(self.current_status["log_messages"]) > 100:
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
        
        # 콘솔에 출력 (로깅 모듈로 대체되어 필요 없을 수 있음)
        print(log_entry)
        
        # 로그 추가할 때마다 상태 저장
        self._save_status()
        
    def log_indexing_event(self, event_type, details=None):
        """인덱싱 이벤트를 로깅하는 보조 함수
        
        Args:
            event_type: 이벤트 유형 ('start', 'file_processed', 'error', 'complete' 등)
            details: 이벤트에 대한 추가 정보 (딕셔너리 또는 문자열)
        """
        if event_type == "start":
            mode = "증분" if details and details.get("incremental") else "전체"
            self.log("INFO", f"인덱싱 시작 - 모드: {mode}")
        elif event_type == "file_processed":
            if details:
                file_path = details.get("file_path", "알 수 없는 파일")
                subtitles = details.get("subtitles", 0)
                duration = details.get("duration", 0)
                self.log("INFO", f"파일 처리 완료: {file_path} - 자막 {subtitles}개, 처리 시간: {duration:.2f}초")
        elif event_type == "error":
            error_msg = details if isinstance(details, str) else details.get("message", "알 수 없는 오류")
            self.log("ERROR", f"인덱싱 오류: {error_msg}")
        elif event_type == "warning":
            warning_msg = details if isinstance(details, str) else details.get("message", "알 수 없는 경고")
            self.log("WARNING", f"인덱싱 경고: {warning_msg}")
        elif event_type == "skipped":
            file_path = details if isinstance(details, str) else details.get("file_path", "알 수 없는 파일")
            reason = "" if isinstance(details, str) else details.get("reason", "")
            self.log("INFO", f"파일 건너뜀: {file_path}{' - ' + reason if reason else ''}")
        elif event_type == "complete":
            stats = ""
            if details:
                files = details.get("processed_files", 0)
                subtitles = details.get("subtitles", 0)
                duration = details.get("duration", 0)
                stats = f" - 처리 파일: {files}개, 자막: {subtitles}개, 총 시간: {duration:.2f}초"
            self.log("INFO", f"인덱싱 완료{stats}")
        elif event_type == "progress":
            if details:
                progress = details.get("progress", 0)
                self.log("INFO", f"인덱싱 진행 중: {progress:.1f}%")
        else:
            # 기타 이벤트 유형
            self.log("INFO", f"인덱싱 이벤트 '{event_type}': {details}")

    def get_status(self):
        """현재 인덱싱 상태 반환"""
        return self.current_status
    
    def start_indexing(self, incremental=False):
        """인덱싱 작업 시작, incremental이 True이면 증분 인덱싱 수행"""
        if self.current_status["is_indexing"]:
            return {"error": "이미 인덱싱이 진행 중입니다."}

        # 일시정지 상태에서 재개하는 경우
        if self.is_paused:
            self.is_paused = False
            self.current_status["is_indexing"] = True
            self._save_status()
            
            # 스레드 재시작
            self.indexing_thread = Thread(target=self._indexing_worker, args=(incremental,))
            self.indexing_thread.daemon = True
            self.indexing_thread.start()
            
            return {"status": "resumed", "message": "인덱싱이 재개되었습니다."}

        self.current_status = {
            "is_indexing": True,
            "processed_files": 0,
            "total_files": 0,
            "current_file": "",
            "subtitle_count": 0,
            "log_messages": [],
            "incremental": incremental,
            "pid": None,
            "last_updated": datetime.now().isoformat()
        }
        self.is_paused = False
        self._save_status()
        
        # 별도 스레드로 인덱싱 작업 실행
        self.indexing_thread = Thread(target=self._indexing_worker, args=(incremental,))
        self.indexing_thread.daemon = True  # 메인 스레드가 종료되면 같이 종료됨
        self.indexing_thread.start()
        
        return {
            "status": "started",
            "mode": "incremental" if incremental else "full"
        }
        
    def stop_indexing(self):
        """인덱싱 중지"""
        if self.current_status["is_indexing"] or self.is_paused:
            self.current_status["is_indexing"] = False
            self.is_paused = False  # 일시정지 상태도 해제
            self.log("WARNING", "인덱싱이 사용자에 의해 중지되었습니다.")
            self._save_status()
            return {"status": "stopped"}
        return {"status": "not_indexing"}

    def pause_indexing(self):
        """인덱싱 일시정지"""
        if not self.current_status["is_indexing"]:
            return {"status": "not_indexing", "message": "진행 중인 인덱싱이 없습니다."}
        
        if self.is_paused:
            return {"status": "already_paused", "message": "이미 일시정지 상태입니다."}
            
        self.is_paused = True
        self.current_status["is_indexing"] = False  # 실행 중 상태는 해제하지만 진행 상황은 유지
        self._save_status()
        return {"status": "paused", "message": "인덱싱이 일시정지되었습니다."}

    def resume_indexing(self):
        """인덱싱 재개"""
        if not self.is_paused:
            return {"status": "not_paused", "message": "일시정지된 인덱싱이 없습니다."}
            
        return self.start_indexing(self.current_status.get("incremental", False))
    
    def scan_directory(self, incremental=False):
        """설정된 디렉토리의 미디어 파일 탐색, incremental이 True이면 마지막 스캔 이후 변경된 파일만 스캔"""
        root_dir = self.config.get('root_dir')
        if not root_dir:
            self.log("ERROR", "루트 디렉토리가 설정되지 않았습니다.")
            return []
            
        media_extensions = [ext.lower() for ext in self.config.get('media_extensions', 
                                                                [".mp4", ".mkv", ".avi", ".mp3", ".wav"])]
        subtitle_extension = self.config.get('subtitle_extension', '.srt').lower()
        
        # 증분 인덱싱을 위한 마지막 스캔 시간 확인
        last_scan_time = None
        if incremental and self.config.get('last_scan_time'):
            try:
                last_scan_time = datetime.fromisoformat(self.config['last_scan_time'])
                self.log("INFO", f"증분 인덱싱 모드: {last_scan_time.strftime('%Y-%m-%d %H:%M:%S')} 이후 변경된 파일만 스캔합니다.")
            except ValueError:
                self.log("WARNING", "마지막 스캔 시간 형식이 올바르지 않아 전체 스캔을 진행합니다.")
        
        media_files = []
        
        self.log("INFO", f"'{root_dir}' 디렉토리 스캔 시작...")
        
        for root, _, files in os.walk(root_dir):
            for file in files:
                file_lower = file.lower()
                if any(file_lower.endswith(ext) for ext in media_extensions):
                    media_path = os.path.join(root, file)
                    subtitle_path = os.path.splitext(media_path)[0] + subtitle_extension
                    has_subtitle = os.path.exists(subtitle_path)
                    
                    # 파일 크기 및 수정 시간
                    try:
                        file_stat = os.stat(media_path)
                        file_size = file_stat.st_size
                        file_mtime = datetime.fromtimestamp(file_stat.st_mtime)
                        last_modified = file_mtime.isoformat()
                        
                        # 증분 인덱싱: 마지막 스캔 이후 수정된 파일만 포함
                        if incremental and last_scan_time and file_mtime <= last_scan_time:
                            # 자막 파일의 수정 시간도 확인
                            if has_subtitle:
                                subtitle_stat = os.stat(subtitle_path)
                                subtitle_mtime = datetime.fromtimestamp(subtitle_stat.st_mtime)
                                if subtitle_mtime <= last_scan_time:
                                    continue  # 미디어와 자막 모두 변경되지 않음
                            else:
                                continue  # 미디어만 있고 변경되지 않음
                    except:
                        file_size = 0
                        last_modified = datetime.now().isoformat()
                    
                    media_files.append({
                        "media_path": media_path,
                        "subtitle_path": subtitle_path if has_subtitle else None,
                        "has_subtitle": has_subtitle,
                        "size": file_size,
                        "last_modified": last_modified
                    })
        
        if incremental and last_scan_time:
            self.log("INFO", f"증분 스캔 완료. {len(media_files)}개의 변경된 미디어 파일이 발견되었습니다.")
        else:
            self.log("INFO", f"전체 스캔 완료. 총 {len(media_files)}개의 미디어 파일이 발견되었습니다.")
        return media_files
    
    def process_subtitle(self, subtitle_path, media_id):
        """자막 파일 처리 및 DB에 저장"""
        subtitle_count = 0
        min_english_ratio = self.config.get('min_english_ratio', 0.7)
        fallback_encodings = ['utf-8-sig', 'utf-8', 'euc-kr', 'cp949', 'ISO-8859-1']
        tried_encodings = set()
        subs = None
        encoding = None
        try:
            # 인코딩 감지
            encoding = detect_encoding(subtitle_path)
            if not encoding:
                encoding = 'utf-8-sig'  # BOM 처리를 위한 기본 인코딩
            tried_encodings.add(encoding.lower())
            self.log("INFO", f"자막 파일 '{subtitle_path}' 처리 중 (인코딩: {encoding})")
            # 자막 파일 파싱 (우선 감지된 인코딩)
            try:
                subs = pysrt.open(subtitle_path, encoding=encoding)
            except Exception as e:
                self.log("WARNING", f"pysrt.open 실패 (감지 인코딩: {encoding}): {e}")
                # fallback 인코딩 시도
                for enc in fallback_encodings:
                    if enc.lower() in tried_encodings:
                        continue
                    try:
                        subs = pysrt.open(subtitle_path, encoding=enc)
                        self.log("INFO", f"자막 파일 '{subtitle_path}' fallback 인코딩 성공: {enc}")
                        encoding = enc
                        break
                    except Exception as e2:
                        self.log("WARNING", f"pysrt.open 실패 (fallback 인코딩: {enc}): {e2}")
                        tried_encodings.add(enc.lower())
                if subs is None:
                    raise Exception(f"모든 인코딩 시도 실패: {tried_encodings}")
            # 자막 내용이 충분히 있는지 확인
            if len(subs) < 3:  # 최소 3개의 자막이 있어야 처리
                self.log("WARNING", f"'{subtitle_path}'에 충분한 자막이 없습니다.")
                return 0
            # 자막 내용을 결합하여 영어 비율 체크
            sample_text = " ".join([remove_html_tags(sub.text) for sub in subs[:20]])
            # 영어인지 확인
            if not is_english_subtitle(sample_text, min_english_ratio):
                self.log("WARNING", f"'{subtitle_path}'에 영어 자막이 없습니다.")
                return 0
            # 기존 자막 데이터 삭제 (재인덱싱의 경우)
            self.db.clear_subtitles_for_media(media_id)
            # 자막 처리
            for sub in subs:
                # HTML 태그 제거
                clean_text = remove_html_tags(sub.text.strip())
                if clean_text:  # 내용이 있는 경우만 처리
                    start_ms = time_to_ms(sub.start)
                    end_ms = time_to_ms(sub.end)
                    # 자막 저장 시도 및 결과 확인
                    result = self.db.insert_subtitle(
                        media_id, 
                        start_ms, 
                        end_ms, 
                        str(sub.start), 
                        str(sub.end), 
                        clean_text
                    )
                    if result:
                        subtitle_count += 1
                    else:
                        self.log("WARNING", f"자막 저장 실패: {clean_text[:30]}...")
            self.log("INFO", f"'{subtitle_path}'에서 {subtitle_count}개의 자막을 처리했습니다.")
        except Exception as e:
            self.log("ERROR", f"자막 처리 오류: {str(e)} - '{subtitle_path}'")
            import traceback
            self.log("DEBUG", traceback.format_exc())
            return 0
        return subtitle_count
    
    def _indexing_worker(self, incremental=False):
        """별도 스레드에서 실행되는 인덱싱 작업"""
        try:
            # 현재 프로세스 ID 저장
            import os
            self.current_status["pid"] = os.getpid()
            self._save_status()
            
            # 스캔 시작 시간 기록 (증분 인덱싱을 위함)
            scan_start_time = datetime.now().isoformat()
            
            # 미디어 파일 스캔 (증분 모드 적용)
            media_files = self.scan_directory(incremental)
            self.current_status["total_files"] = len(media_files)
            self._save_status()
            
            # 인덱싱 전략에 따른 처리
            strategy = self.config.get("indexing_strategy", "standard")
            self.log("INFO", f"인덱싱 전략: {strategy}")
            
            if strategy == "standard":
                # 표준 처리: 파일별로 순차 처리
                self._process_standard(media_files)
            elif strategy == "batch":
                # 일괄 처리: 모든 자막을 한 번에 처리
                self._process_batch(media_files)
            elif strategy == "parallel":
                # 병렬 처리: 여러 스레드에서 동시 처리
                self._process_parallel(media_files)
            elif strategy == "delayed_language":
                # 지연된 언어 감지: DB 저장 후 비영어 필터링
                self._process_delayed_language(media_files)
            else:
                # 알 수 없는 전략: 표준 처리로 폴백
                self.log("WARNING", f"알 수 없는 인덱싱 전략: {strategy}, 표준 처리로 진행합니다.")
                self._process_standard(media_files)
            
            # FTS 인덱스 재구축 - 검색 성능 최적화
            self.log("INFO", "FTS 인덱스 재구축 중...")
            start_time = time.time()
            self.db.rebuild_fts_index()
            rebuild_time = time.time() - start_time
            self.log("INFO", f"FTS 인덱스 재구축 완료 ({rebuild_time:.2f}초)")
            
            # 마지막 스캔 시간 업데이트
            self.config["last_scan_time"] = scan_start_time
            save_config(self.config)
            
            # 인덱싱 완료
            self.current_status["is_indexing"] = False
            self.current_status["pid"] = None
            
            mode_text = "증분" if incremental else "전체"
            self.log("INFO", f"{mode_text} 인덱싱이 완료되었습니다. "
                        f"{self.current_status['processed_files']}개 미디어, "
                        f"{self.current_status['subtitle_count']}개 자막 처리됨.")
            
        except Exception as e:
            self.log("ERROR", f"인덱싱 중 오류 발생: {str(e)}")
            self.current_status["is_indexing"] = False
            self.current_status["pid"] = None
            self._save_status()
    
    def _process_standard(self, media_files):
        """표준 처리: 파일별로 순차 처리"""
        for idx, media_info in enumerate(media_files):
            # 인덱싱이 중지되었거나 일시정지된 경우 중단
            if not self.current_status["is_indexing"] or self.is_paused:
                break
                
            # 현재 처리 중인 파일 업데이트
            self.current_status["current_file"] = media_info["media_path"]
            self.current_status["processed_files"] = idx
            self._save_status()
            
            # 자막이 있는 경우만 처리
            if media_info["has_subtitle"]:
                # 미디어 정보 DB에 저장 또는 업데이트
                media_id = self.db.upsert_media(media_info["media_path"])
                
                # 자막 처리
                subtitle_count = self.process_subtitle(media_info["subtitle_path"], media_id)
                self.current_status["subtitle_count"] += subtitle_count
                self._save_status()
    
    def _process_batch(self, media_files):
        """일괄 처리: 먼저 모든 미디어 정보를 저장한 후 자막 처리"""
        # 1단계: 모든 미디어 정보 저장
        media_ids = {}
        for idx, media_info in enumerate(media_files):
            # 인덱싱이 중지되었거나 일시정지된 경우 중단
            if not self.current_status["is_indexing"] or self.is_paused:
                break
                
            if media_info["has_subtitle"]:
                media_id = self.db.upsert_media(media_info["media_path"])
                media_ids[media_info["subtitle_path"]] = media_id
                
            # 진행상황 업데이트
            self.current_status["processed_files"] = idx
            self._save_status()
        
        # 2단계: 자막 처리
        for idx, (subtitle_path, media_id) in enumerate(media_ids.items()):
            # 인덱싱이 중지되었거나 일시정지된 경우 중단
            if not self.current_status["is_indexing"] or self.is_paused:
                break
                
            self.current_status["current_file"] = subtitle_path
            subtitle_count = self.process_subtitle(subtitle_path, media_id)
            self.current_status["subtitle_count"] += subtitle_count
            self._save_status()
    
    def _process_parallel(self, media_files):
        """병렬 처리: 여러 스레드에서 동시 처리"""
        # 최대 작업자 수 (기본값 = CPU 코어 수)
        max_workers = self.config.get("max_workers") or os.cpu_count()
        if not max_workers or max_workers <= 0:
            max_workers = 4  # 기본값
            
        self.log("INFO", f"병렬 처리 모드: {max_workers}개의 작업자로 처리합니다.")
        
        # 미디어 파일을 처리 준비 (자막이 있는 파일만)
        subtitle_files = [(media_info["subtitle_path"], 
                          self.db.upsert_media(media_info["media_path"])) 
                          for media_info in media_files 
                          if media_info["has_subtitle"]]
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            for subtitle_path, media_id in subtitle_files:
                # 인덱싱이 중지되었거나 일시정지된 경우 중단
                if not self.current_status["is_indexing"] or self.is_paused:
                    break
                    
                future = executor.submit(self.process_subtitle, subtitle_path, media_id)
                futures[future] = subtitle_path
            
            # 완료된 작업 처리
            for idx, future in enumerate(as_completed(futures)):
                # 인덱싱이 중지되었거나 일시정지된 경우 남은 작업 취소
                if not self.current_status["is_indexing"] or self.is_paused:
                    for f in futures:
                        if not f.done() and not f.cancelled():
                            f.cancel()
                    break
                    
                subtitle_path = futures[future]
                try:
                    subtitle_count = future.result()
                    self.current_status["subtitle_count"] += subtitle_count
                except Exception as e:
                    self.log("ERROR", f"병렬 처리 중 오류: {str(e)} - '{subtitle_path}'")
                
                self.current_status["current_file"] = subtitle_path
                self.current_status["processed_files"] = idx + 1
                self._save_status()
    
    def _process_delayed_language(self, media_files):
        """지연된 언어 감지: 모든 자막을 먼저 DB에 저장한 후, 나중에 영어 여부 확인"""
        # 1단계: 모든 미디어 및 자막을 DB에 저장 (언어 확인 없이)
        for idx, media_info in enumerate(media_files):
            # 인덱싱이 중지되었거나 일시정지된 경우 중단
            if not self.current_status["is_indexing"] or self.is_paused:
                break
                
            if media_info["has_subtitle"]:
                try:
                    media_id = self.db.upsert_media(media_info["media_path"])
                    
                    # 자막을 DB에 저장 (영어 확인 없이)
                    subtitle_count = 0
                    encoding = detect_encoding(media_info["subtitle_path"])
                    subs = pysrt.open(media_info["subtitle_path"], encoding=encoding or 'utf-8-sig')
                    
                    for sub in subs:
                        clean_text = remove_html_tags(sub.text.strip())
                        if clean_text:
                            start_ms = time_to_ms(sub.start)
                            end_ms = time_to_ms(sub.end)
                            self.db.insert_subtitle(
                                media_id, start_ms, end_ms, str(sub.start), 
                                str(sub.end), clean_text, verified=False
                            )
                            subtitle_count += 1
                    
                    self.log("INFO", f"{subtitle_count}개 자막 저장: '{media_info['subtitle_path']}'")
                    self.current_status["subtitle_count"] += subtitle_count
                except Exception as e:
                    self.log("ERROR", f"자막 처리 오류: {str(e)} - '{media_info['subtitle_path']}'")
            
            # 진행상황 업데이트
            self.current_status["current_file"] = media_info["media_path"]
            self.current_status["processed_files"] = idx + 1
            self._save_status()
        
        # 2단계: 저장된 자막의 영어 여부 확인 및 필터링
        self.log("INFO", "저장된 자막의 영어 여부 확인 중...")
        min_english_ratio = self.config.get('min_english_ratio', 0.7)
        
        # DB에서 확인되지 않은 자막 가져오기
        unverified_subtitles = self.db.get_unverified_subtitles()
        
        for media_id, subtitle_text in unverified_subtitles:
            # 인덱싱이 중지되었거나 일시정지된 경우 중단
            if not self.current_status["is_indexing"] or self.is_paused:
                break
                
            try:
                # 영어 여부 확인
                is_english = is_english_subtitle(subtitle_text, min_english_ratio)
                
                # 영어가 아닌 자막은 삭제
                if not is_english:
                    self.db.delete_subtitles_by_media(media_id)
                    self.log("INFO", f"영어가 아닌 자막 제거: 미디어 ID {media_id}")
                else:
                    # 영어 자막은 verified로 표시
                    self.db.mark_subtitles_verified(media_id)
            except Exception as e:
                self.log("ERROR", f"자막 언어 확인 중 오류: {str(e)} - 미디어 ID {media_id}")
                
        self.log("INFO", "자막 언어 확인 완료")