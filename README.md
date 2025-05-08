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

### 디렉토리 구조

```
app/                        # 메인 애플리케이션 코드
  ├── models/               # 데이터 모델
  ├── routes/               # API 라우트
  ├── services/             # 비즈니스 로직 서비스
  └── utils/                # 유틸리티 기능

static/                     # 정적 파일 (CSS, JS, 이미지)
templates/                  # Jinja2 템플릿
```

### 개발 문서

자세한 개발 진행 상황과 계획은 다음 문서를 참조하세요:
- [프로젝트 진행 상황](PROGRESS.md): 개발 진행 현황 및 향후 계획
- [사용법 가이드](사용법.md): 애플리케이션 사용 방법
- [리팩토링 계획](refactoring_plan.md): 코드 개선 계획

## 라이선스

이 프로젝트는 MIT 라이선스 하에 제공됩니다. 