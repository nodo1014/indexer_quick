# 미디어 자막 인덱서

영상 및 오디오 파일의 영어 자막(.srt)을 인덱싱하고 검색할 수 있는 웹 애플리케이션입니다.

## 개요

이 프로젝트는 지정된 디렉토리에서 미디어 파일(.mp4, .mkv 등)과 영어 자막(.srt)을 스캔하여 SQLite 데이터베이스에 인덱싱합니다. 사용자는 인덱싱된 자막을 검색하고, 미디어 파일을 재생하며, 특정 자막 위치로 이동할 수 있습니다.

## 주요 기능

- **미디어 인덱싱**: 
  - 지정된 디렉토리에서 미디어 파일과 자막 파일을 자동으로 스캔
  - 증분 인덱싱 지원 (이미 인덱싱된 파일을 건너뜀)
  - 멀티스레드 처리로 빠른 인덱싱 속도
  - 영어 자막 자동 감지 및 필터링

- **자막 검색**:
  - 인덱싱된 자막에서 텍스트 검색
  - 검색 결과에서 미디어 파일 및 해당 자막 확인
  - 타임코드별 결과 표시

- **미디어 재생**:
  - 검색 결과에서 미디어 파일 직접 재생
  - 자막 위치로 정확한 이동
  - 반복 재생, 북마크 기능 지원

- **사용자 인터페이스**:
  - 직관적인 웹 인터페이스
  - htmx를 통한 실시간 업데이트
  - 인덱싱 진행 상황 실시간 모니터링

## 설치 및 실행

### 요구 사항

- Python 3.8 이상
- pip (Python 패키지 관리자)

### 설치 과정

1. 저장소 클론 또는 다운로드:
   ```bash
   git clone <repository-url>
   cd <project-directory>
   ```

2. 가상 환경 생성 및 활성화:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # 또는
   venv\Scripts\activate  # Windows
   ```

3. 의존성 설치:
   ```bash
   pip install -r requirements.txt
   ```

4. 애플리케이션 설정:
   `config.json` 파일에서 루트 디렉토리 경로 및 기타 설정을 구성하세요.

### 실행

```bash
python main.py
```

서버가 시작되면 웹 브라우저에서 `http://localhost:8080`으로 접속하세요.

## 설정

`config.json` 파일에서 다음 설정을 구성할 수 있습니다:

- `root_dir`: 미디어 파일을 스캔할 디렉토리 경로
- `media_extensions`: 인식할 미디어 파일 확장자 목록
- `subtitle_extension`: 자막 파일 확장자 (기본: .srt)
- `min_english_ratio`: 영어 자막으로 판단할 최소 영문 비율
- `db_path`: 데이터베이스 파일 경로
- `max_threads`: 인덱싱에 사용할 최대 스레드 수

## 개발 정보

### 기술 스택

- **백엔드**: 
  - [FastAPI](https://fastapi.tiangolo.com/) - 비동기 웹 프레임워크
  - [SQLite](https://www.sqlite.org/) - 데이터베이스
  - [Jinja2](https://jinja.palletsprojects.com/) - 템플릿 엔진

- **프론트엔드**:
  - [htmx](https://htmx.org/) - AJAX 기능을 HTML에 추가
  - [Tailwind CSS](https://tailwindcss.com/) - 유틸리티 우선 CSS 프레임워크
  - 자체 구현 비디오 플레이어 (Video.js 통합 중)

# AI 코딩 규칙

## DB 접근 규칙

🎯 목적: DB 접근 코드를 분산하지 않고, 반드시 `database.subtitles`, `database.media` 등의 모듈을 통해서만 수행하게 리팩토링한다.

1. `indexing.py`, `subtitle_db.py`, `routes`, `services` 파일 등에서 `db.get_connection()`, `conn.cursor()`, `cursor.execute()` 등을 직접 호출하지 말 것.
2. 이러한 DB 작업은 반드시 `database/subtitles.py` 또는 `database/media.py`로 이전하고, 해당 모듈의 함수만 호출하도록 수정한다.
3. FTS 연동(`subtitles_fts`)은 `INSERT INTO subtitles` 시 트리거로 자동 반영되므로, 절대 `subtitles_fts`에 직접 INSERT/UPDATE/DELETE 하지 않는다.
4. 기존 스키마 및 DB 구조는 절대로 변경하지 않는다.
5. 반환 타입은 기존과 동일하게 유지하며 (`sqlite3.Row` → `dict` 변환 포함), 기존 호출부에서 `.get(...)`이나 `["field"]` 접근 방식이 깨지지 않게 한다.
6. 예외 처리 (`try/except`, logging 등)는 기존 수준으로 유지하되, repository 계층에서 담당한다.
7. 기존 클래스(`SubtitleDatabase` 등)는 필요 시 wrapper로 유지하되, DB 로직을 직접 포함하지 않도록 정리한다.
8. 리팩토링 후 기존 라우트, 서비스 기능이 그대로 동작하도록 smoke test 수준으로라도 함수 사용 예가 통과되도록 한다.

