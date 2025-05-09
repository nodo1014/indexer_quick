# 프로젝트 진행 상황 (2025-05-09)

## 프로젝트 개요

이 프로젝트는 지정된 디렉토리에서 미디어 파일(.mp4, .mkv 등)과 영어 자막(.srt)을 스캔하여 데이터베이스에 인덱싱하는 웹 애플리케이션입니다. 사용자는 인덱싱된 자막을 검색하고, 미디어 파일을 재생하며, 특정 자막 위치로 이동할 수 있습니다.

### 핵심 기능

- 미디어 파일 및 영어 자막 인덱싱
- 자막 내용 검색
- 검색된 자막을 통한 미디어 파일 재생
- 북마크 및 태그 기능 (개발 중)

### 주요 기술 스택

- 백엔드: FastAPI, SQLite
- 프론트엔드: HTML, htmx, Tailwind CSS
- 비디오 플레이어: 자체 구현 + Video.js (통합 중)

## 최근 작업 내역

### 데이터베이스 연결 방식 단순화 (2025-05-09)

- 데이터베이스 연결 풀링 제거 및 단일 연결 방식으로 변경:
  - 복잡한 연결 풀 관리 코드 제거
  - 단일 전역 연결 변수로 대체하여 코드 단순화
  - get_connection() 및 close_connection() 함수 단순화
  - 스레드 잠금, 큐, 메타데이터 관련 코드 제거
- app/main.py 파일 수정:
  - 풀링 관련 함수에서 단일 연결 함수로 임포트 변경
  - 초기화 및 종료 관련 코드 단순화
  - init_db() 함수의 비동기 호출 문제 수정
- 성능 영향 최소화:
  - WAL 모드 및 성능 최적화 설정 유지
  - SQLite 설정 최적화로 단일 연결에서도 효율적인 성능 보장

### 데이터베이스 API 일관성 및 커넥션 풀링 구현 (2025-05-09)

- 레거시 `database.py` 파일 완전 제거:
  - 모든 임포트 패턴을 모듈화된 `app/database/` 구조로 통일
  - 레거시 호환성 계층 제거로 코드 일관성 확보
  - 중복되는 유틸리티 함수 및 쿼리 제거
- 데이터베이스 연결 풀링 도입:
  - `app/database/connection.py`에 SQLite 연결 풀 구현
  - `get_connection()` 함수를 풀링 방식으로 개선
  - 커넥션 재사용을 통한 성능 최적화
  - 장기 실행 쿼리의 병렬 처리 지원 강화
- 데이터베이스 관련 유틸리티 함수 중앙화:
  - 트랜잭션 및 커넥션 관리 함수 표준화
  - 쿼리 타임아웃 및 재시도 메커니즘 추가
  - 데이터베이스 오류 로깅 개선
  - 디버그 모드에서의 쿼리 실행 시간 모니터링 추가
- 코드 통합을 위한 전체 프로젝트 리팩토링:
  - 모든 데이터베이스 액세스 코드를 신규 API로 마이그레이션 완료
  - 타입 힌트 일관성 개선
  - 개선된 오류 처리 및 예외 처리

### FTS 인덱스 스키마 및 자동화 개선 (2025-05-08)

- FTS(Full-Text Search) 인덱스 구조 개선:
  - 기존 구조에서 외부 테이블 참조 방식으로 변경 (`content='subtitles'`, `content_rowid='id'`)
  - FTS 테이블 스키마 간소화 및 성능 최적화
  - 서버 시작 시 FTS 인덱스 자동 검증 및 복구 기능 추가
- FTS 인덱스 손상 문제 해결:
  - 데이터베이스 손상 시 FTS 인덱스 복구 기능 구현
  - FTS 인덱스와 자막 테이블의 레코드 수 불일치 자동 감지
  - `rebuild_fts.py` 및 `repair_database.py` 스크립트 개선
- 검색 성능 및 안정성 강화:
  - FTS 검색 API 안정성 개선 (`app/routes/search.py`)
  - `app/database/schema.py`의 `rebuild_fts_index()` 함수 최적화
  - 다양한 검색 방법 지원 (FTS 및 LIKE 검색)

### 데이터베이스 구조 리팩토링 (2024-06-05)

- 기존 단일 파일의 `database.py`를 모듈식 패키지로 분리 완료:
  - `app/database/__init__.py`: 패키지 초기화 및 Database 클래스 제공
  - `app/database/connection.py`: 데이터베이스 연결 및 쿼리 실행 관리
  - `app/database/schema.py`: 테이블 정의 및 데이터베이스 스키마 관리
  - `app/database/media.py`: 미디어 파일 관련 CRUD 함수 모음
  - `app/database/subtitles.py`: 자막 관련 CRUD 함수 모음
- 타입 힌트 적용으로 코드 가독성 및 유지보수성 향상
- 레거시 코드 호환성을 위한 Database 클래스 유지
- 오류 처리 및 로깅 개선
- 루트 디렉토리의 database.py 파일 제거 (legacy/ 디렉토리로 이동)

### 인덱서 서비스 리팩토링 (2024-06-05)

- 인덱싱 로직을 `app/services/indexer.py`로 완전히 이전 완료:
  - `IndexerService` 클래스 기반의 구조화된 설계
  - 상태 관리 및 로깅 기능 통합
  - 다양한 인덱싱 전략 구현 (표준, 배치, 병렬, 지연 언어 감지)
  - 인덱싱 작업의 일시 중지/재개 기능 개선
- 유틸리티 함수를 app/utils 모듈로 이동하여 중복 제거
- 비동기 프로세스 관리 개선
- 예상 완료 시간 계산 및 UI 표시 기능 추가
- 루트 디렉토리의 indexer.py 파일 제거 (legacy/ 디렉토리로 이동)

### app/utils 구현 (2024-05-30)

- 리팩토링 계획에 따라 app/utils 디렉토리에 유틸리티 함수 구현 완료:
  - `app/utils/constants.py`: 상수 정의 (데이터베이스, 미디어, 인덱싱 등 관련 상수)
  - `app/utils/helpers.py`: 도움 함수 (시간 변환, 파일 처리, 경로 관리 등)
  - `app/utils/logging.py`: 로깅 설정 (로거 생성, 로그 파일 관리)
  - `app/utils/__init__.py`: 패키지 초기화 (각 모듈의 주요 함수 및 상수 임포트)
- 기존 코드의 중복 유틸리티 함수들을 정리하고 app/utils로 이동
- 모듈화 및 타입 힌트 추가로 코드 가독성 향상
- app/services 코드에서 app/utils 모듈 사용하도록 업데이트 진행 중

### 리팩토링 진행 상황 점검 및 업데이트 (2024-05-25)

- 프로젝트 구조 분석 및 현재 상태 검토
- 대규모 파일 분석: 리팩토링이 필요한 파일 식별
  - `indexer.py` (689 라인) - 루트 디렉토리에 있는 레거시 파일
  - `database.py` (672 라인) - 루트 디렉토리에 있는 레거시 파일
  - `app/main.py` (506 라인) - 분리가 필요한 라우트 함수들 포함
  - `app/database.py` (985 라인) - 더 세분화된 모듈로 분리 필요
- 현재 리팩토링 상태 점검:
  - app/ 디렉토리 기반 구조로 전환 진행 중
  - 핵심 기능은 app/ 디렉토리로 이미 이동됨

### Video.js 라이브러리 통합 (2024-05-09)

- 비디오 플레이어 코드를 Video.js 라이브러리 기반으로 전면 리팩토링
  - `/static/js/components/video-components/video-player.js` 파일 구조 변경
  - `/static/js/components/video-components/subtitle-controller.js` 비디오 플레이어 통합
  - `/static/js/components/video-components/playback-manager.js` 재생 관리 기능 개선
  - `/static/js/components/video-components/bookmark-manager.js` 북마크 기능 최적화
- 불필요한 레거시 코드 제거 및 최적화
- 모듈화된 ES 모듈 구조로 코드 개선
- 템플릿 파일 (`/templates/search.html`) Video.js 지원 추가

### 서버 및 API 개선 (2024-05-07)

- FastAPI 문서 자동 생성 기능 비활성화로 인한 API 엔드포인트 접근 문제 진단
- `/settings` 및 `/api/index` POST 엔드포인트 정상 동작하도록 서버 코드 수정
  - `/api/index`에서 JSON 데이터 파싱 방식 개선 (request.json() 사용)
- 인덱싱 상태 및 로그가 정상적으로 반환되는지 확인
- 인덱싱 로그 생성 함수(`log`)의 위치 및 역할 파악
  - `/app/services/indexer.py` 내 IndexerService 클래스의 log 함수가 인덱싱 로그를 관리

### 프론트엔드 개선 (2024-05-08)

- Video Player 컴포넌트 리팩토링
  - 단일 파일에서 모듈화된 구조로 변경
  - ES 모듈 방식으로 코드 구성
  - 각 기능별 컴포넌트 분리:
    - `video-player-core.js`: 비디오 요소 제어 및 기본 기능
    - `subtitle-controller.js`: 자막 표시 및 제어
    - `playback-manager.js`: 재생 모드 및 반복 재생 관리
    - `bookmark-manager.js`: 북마크 및 태그 관리
    - `video-player.js`: 메인 통합 클래스
  - 코드 가독성 및 유지보수성 향상
  - 관심사 분리를 통한 모듈화

### 프로젝트 구조 리팩토링 (진행 중)

- 디렉토리 구조 개선 및 코드 모듈화
- app/ 디렉토리로 주요 코드 이동:
  - app/routes/: API 라우트 코드 분리
  - app/services/: 비즈니스 로직 서비스 분리
  - app/models/: 데이터 모델 분리
  - app/utils/: 유틸리티 함수 분리 (구현 완료)

### 문서화 개선

- '사용법.md' 작성 - 사용자를 위한 매뉴얼
- 'PROGRESS.md' 업데이트 - 개발 진행 상황 및 계획 문서화

## 현재 파일 구조

```
/Volumes/p31/coding/indexer_quick/
├── 사용법.md                    # 사용자 매뉴얼
├── 유글리쉬.md                  # 영어 자막 관련 가이드
├── 유튜브 확장.md                # YouTube 확장 관련 가이드
├── 자막인코딩.md                 # 자막 인코딩 관련 가이드
├── api_doc_generator.py        # API 문서 생성 스크립트
├── api_docs_generator.log      # API 문서 생성 로그
├── check_search.py             # 검색 기능 점검 스크립트
├── check_subtitles.py          # 자막 점검 스크립트
├── config.json                 # 애플리케이션 설정 파일
├── database_debug.log          # 데이터베이스 디버그 로그
├── database_verbose.log        # 데이터베이스 상세 로그
├── edit_search.py              # 검색 기능 편집 스크립트
├── fix_db.py                   # 데이터베이스 수정 스크립트
├── indexer_verbose.log         # 인덱서 상세 로그
├── indexer.log                 # 인덱서 로그
├── indexing_status.json        # 인덱싱 상태 정보
├── main.py                     # 애플리케이션 진입점
├── media_index.db              # 메인 데이터베이스 파일
├── media_index.db-shm          # SQLite 공유 메모리 파일
├── media_index.db-wal          # SQLite WAL 파일
├── media_index.db.backup_*     # 데이터베이스 백업 파일들
├── PROGRESS.md                 # 프로젝트 진행 상황 문서
├── README.md                   # 프로젝트 README 파일
├── rebuild_fts.py              # FTS 인덱스 재구축 스크립트
├── refactoring_plan.md         # 리팩토링 계획 문서
├── repair_database.py          # 데이터베이스 복구 스크립트
├── requirements.txt            # 필요한 Python 패키지 목록
├── server.log                  # 서버 로그 파일
├── __pycache__/                # Python 바이트코드 캐시 디렉토리
│
├── app/                        # 메인 애플리케이션 코드
│   ├── __init__.py             # 패키지 초기화 파일
│   ├── config.py               # 설정 관리
│   ├── main.py                 # FastAPI 애플리케이션 정의
│   ├── PROGRESS.md             # 앱 진행 상황 문서
│   ├── subtitle_db.py          # 자막 데이터베이스 관리
│   ├── subtitle_watcher.py     # 자막 파일 변경 감시
│   │
│   ├── database/               # 데이터베이스 액세스 계층
│   │   ├── __init__.py         # 패키지 초기화 및 Database 클래스
│   │   ├── connection.py       # 데이터베이스 연결 관리 (풀링 포함)
│   │   ├── media.py            # 미디어 파일 관련 CRUD
│   │   ├── schema.py           # 스키마 정의 및 관리
│   │   ├── subtitles.py        # 자막 관련 CRUD
│   │   └── __pycache__/        # 바이트코드 캐시
│   │
│   ├── models/                 # 데이터 모델
│   │   ├── __init__.py         # 패키지 초기화
│   │   ├── media.py            # 미디어 모델
│   │   ├── subtitle.py         # 자막 모델
│   │   └── __pycache__/        # 바이트코드 캐시
│   │
│   ├── routes/                 # API 라우트
│   │   ├── __init__.py         # 패키지 초기화
│   │   ├── database_manager.py # 데이터베이스 관리 라우트
│   │   ├── docs.py             # 문서화 라우트
│   │   ├── indexing.py         # 인덱싱 라우트
│   │   ├── search.py           # 검색 라우트
│   │   ├── settings.py         # 설정 라우트
│   │   ├── stats.py            # 통계 라우트
│   │   ├── subtitle_handler.py # 자막 처리 라우트
│   │   └── __pycache__/        # 바이트코드 캐시
│   │
│   ├── services/               # 비즈니스 로직 서비스
│   │   ├── __init__.py         # 패키지 초기화
│   │   ├── indexer.py          # 인덱싱 서비스
│   │   ├── search.py           # 검색 서비스
│   │   ├── stats.py            # 통계 서비스
│   │   └── __pycache__/        # 바이트코드 캐시
│   │
│   ├── subtitle/               # 자막 처리 모듈
│   │   ├── __init__.py         # 패키지 초기화
│   │   ├── __pycache__/        # 바이트코드 캐시
│   │   ├── encodings/          # 인코딩 관련
│   │   ├── extractors/         # 자막 추출 관련
│   │   └── utils/              # 자막 유틸리티
│   │
│   ├── utils/                  # 유틸리티 기능
│   │   ├── __init__.py         # 패키지 초기화
│   │   └── ...                 # 기타 유틸리티 모듈
│   │
│   └── __pycache__/            # 바이트코드 캐시
│
├── config/                     # 설정 파일 디렉토리
│   └── subtitle_encoding_config.json # 자막 인코딩 설정
│
├── docs/                       # 문서 디렉토리
│   └── api_reference.md        # API 참조 문서
│
├── legacy/                     # 레거시 코드 디렉토리
│   ├── database.py             # 이전 데이터베이스 코드
│   ├── indexer.py              # 이전 인덱서 코드
│   └── app/
│       └── routes/             # 이전 라우트 코드
│
├── logs/                       # 로그 디렉토리
│   ├── indexer_verbose.log     # 인덱서 상세 로그
│   ├── indexer.log             # 인덱서 기본 로그
│   ├── database/               # 데이터베이스 로그
│   ├── services/               # 서비스 로그
│   └── stats_service/          # 통계 서비스 로그
│
├── static/                     # 정적 파일 디렉토리
│   ├── favicon.ico             # 파비콘
│   ├── css/                    # CSS 파일
│   ├── img/                    # 이미지 파일
│   ├── js/                     # 자바스크립트 파일
│   └── meta/                   # 메타데이터 파일
│
└── templates/                  # 템플릿 디렉토리
    ├── ai_interface.html       # AI 인터페이스 템플릿
    ├── base.html               # 기본 레이아웃 템플릿
    ├── dashboard.html          # 대시보드 템플릿
    ├── database_manager.html   # 데이터베이스 관리 템플릿
    ├── index.html              # 메인 페이지 템플릿
    ├── indexing_filter.html    # 인덱싱 필터 템플릿
    ├── indexing_process.html   # 인덱싱 프로세스 템플릿
    ├── search.html             # 검색 페이지 템플릿
    ├── settings.html           # 설정 페이지 템플릿
    ├── subtitle_conversion_process.html # 자막 변환 템플릿
    ├── subtitle_encoding.html  # 자막 인코딩 템플릿
    ├── docs/                   # 문서 템플릿
    └── partials/               # 부분 템플릿
```

## 다음 작업 예정

### 대규모 파일 리팩토링

- ✅ `database.py`를 모듈별 데이터 액세스 객체로 분리 (완료)
- ✅ `indexer.py`를 app/services/indexer.py로 완전히 이전 (완료)
- app/ 디렉토리의 남은 큰 파일들 추가 분리:
  - `app/main.py`(506라인)에서 라우트 함수들을 app/routes/ 모듈로 더 분리

### 서비스 계층 개선

- app/services/indexer.py와 루트의 indexer.py의 기능 통합
- app/services 내 모듈 간 의존성 개선
- 서비스 객체 생성 및 관리 방식 표준화

### 인덱싱 기능 개선

- 인덱싱 로그 파일 기록 방식 개선
- 인덱싱 상태/로그 UI 개선 및 오류 처리 고도화
- 증분 인덱싱 기능 강화 (변경된 파일만 업데이트)

### 미디어 플레이어 개선

- Video.js 라이브러리와 기존 플레이어 통합 구현 완료
- 미디어 재생 관련 UI/UX 개선
- 북마크 및 태그 시스템 구현 완료

### 검색 기능 강화

- 검색 결과 페이지 UI/UX 개선
- 검색 필터링 기능 추가 (시간대, 미디어 유형 등)
- 전문 검색(Full-text search) 최적화

### 성능 최적화

- 데이터베이스 인덱싱 및 쿼리 최적화
- 대용량 데이터 처리 성능 개선
- 메모리 사용량 최적화

### 향후 계획

- 다중 언어 자막 지원 확장
- 사용자 인증 및 개인화 기능
- 공유 및 내보내기 기능

## 진행 중인 이슈

1. 레거시 파일(`indexer.py`, `database.py`)과 리팩토링된 코드 간의 기능 충돌 가능성
2. 포트 충돌 문제: ERROR: [Errno 48] Address already in use - 서버 실행 시 발생
3. 인덱싱 프로세스에서 간헐적으로 발생하는 오류 디버깅
4. 대용량 데이터베이스에서의 검색 성능 최적화
5. 검색 결과 페이지에서의 미디어 재생 기능 개선
6. Video Player 모듈 리팩토링 완료 및 통합 테스트

## 테스트 항목

- [x] 기본 인덱싱 기능
- [x] 증분 인덱싱 기능
- [ ] 대용량 미디어 컬렉션 처리 성능
- [x] 기본 검색 기능
- [ ] 복잡한 검색 쿼리 처리
- [ ] 다양한 자막 형식 지원
- [ ] 미디어 플레이어 기능
- [ ] 북마크 및 태그 기능

## [2025-05-08] 자막 검색 및 비디오 재생 기능 오류 수정

### FTS 인덱스 불일치 문제 해결

- 문제: subtitles 테이블과 subtitles_fts 테이블의 레코드 수 불일치로 검색 결과 누락
- 원인:
  - FTS 테이블 스키마와 실제 테이블 구조의 불일치
  - 외부 테이블 참조 방식과 직접 필드 방식 사용의 혼합
- 해결:
  - FTS 테이블 스키마 수정 (외부 테이블 참조 방식으로 통일)
  - `app/database/schema.py`의 FTS 관련 함수 개선
  - 서버 시작 시 FTS 인덱스 자동 점검 및 재구축 기능 추가
- 관련 파일: `app/database/schema.py`, `rebuild_fts.py`, `repair_database.py`

### 검색 성능 최적화

- FTS5 인덱스 사용으로 텍스트 검색 속도 대폭 개선
- 대용량 데이터베이스에서도 빠른 검색 응답 가능
- 자막 파일 처리 시 즉시 FTS 인덱스 갱신 기능 추가
- 관련 파일: `app/routes/search.py`, `app/services/search.py`

### 데이터베이스 복구 도구 개선

- 데이터베이스 손상 시 복구 프로세스 자동화
- 스키마 불일치 문제 해결을 위한 동적 컬럼 매핑 기능 추가
- 백업 및 복구 프로세스 안정성 향상
- 관련 파일: `repair_database.py`

## [2025-05-08] 자막 검색 및 비디오 재생 기능 오류 수정

### 1. 자막 검색 결과 표시 문제 해결

- 문제: 검색된 자막이 화면에 표시되지 않음
- 원인: API 응답 구조가 변경되었으나 클라이언트 표시 코드가 업데이트되지 않음
- 해결: `search.js`의 `displayResults` 함수 수정으로 새로운 API 응답 구조(`mediaPath`, `streamingUrl`, `subtitles` 배열)에 맞게 로직 개선
- 관련 파일: `static/js/search.js`

### 2. 자막 클릭 시 비디오 재생 문제 해결

- 문제: 검색된 자막을 클릭했을 때 비디오 플레이어가 재생되지 않음
- 원인:
  - 자막 데이터 형식 불일치 (`start_time`/`startTime` 등)
  - 비디오 플레이어의 세그먼트 재생 로직 문제
- 해결:
  - `subtitle-controller.js`의 `playSingleSubtitle` 메서드 개선
  - `video-player.js`의 `playSegment`, `_executePlaySegment` 메서드 강화
  - 유효하지 않은 시간 값 검사 및 처리 로직 추가
- 관련 파일:
  - `static/js/components/video-components/subtitle-controller.js`
  - `static/js/components/video-components/video-player.js`

### 3. 북마크 및 태그 기능 복원

- 문제: 디자인 변경 과정에서 북마크 및 태그 버튼이 사라짐
- 해결: 북마크 버튼 및 태그 버튼을 템플릿에 재추가
- 관련 파일: `static/js/search.js`

### 다음 계획

- 비디오 플레이어 컴포넌트 간 통신 개선
- 에러 핸들링 강화
- 추가 디버깅 로그 정리

## [2023-05-09] 자막 처리 모듈 리팩토링

### 주요 구현 내용

- 기존 단일 파일(subtitle_encoding.py, 2333줄)을 기능별로 분리하여 모듈화 완료
- 새로운 구조적인 패키지(app/subtitle/) 구성 및 구현:
  - `app/subtitle/encodings/`: 인코딩 감지 및 변환 관련 모듈
  - `app/subtitle/extractors/`: 자막 추출 관련 모듈
  - `app/subtitle/utils/`: 자막 처리 유틸리티 모듈
- FastAPI 라우터 구조 개선:
  - 기존: `app/routes/subtitle_encoding.py` (단일 대형 파일)
  - 신규: `app/routes/subtitle_handler.py` (라우팅 로직만 포함하는 간결한 파일)
- API 엔드포인트 통합 및 정리:
  - 기존: `/subtitle-encoding/*`
  - 신규: `/subtitle/*` (통합된 경로)
- API 하위 호환성 유지:
  - 이전 경로 `/subtitle-encoding/*`에서 새 경로 `/subtitle/*`로 자동 리다이렉트 추가
  - 하위 호환성을 위한 HTTP 308 영구 리다이렉트 적용

### 리팩토링 세부 사항

1. **인코딩 처리 모듈 분리**:

   - `app/subtitle/encodings/detector.py`: 파일 인코딩 감지 기능
   - `app/subtitle/encodings/converter.py`: 인코딩 변환 기능

2. **자막 추출 모듈 분리**:

   - `app/subtitle/extractors/extractor.py`: 기본 추출 인터페이스
   - `app/subtitle/extractors/smi_extractor.py`: SMI 형식 자막 전용 추출기
   - `app/subtitle/extractors/ass_extractor.py`: ASS/SSA 형식 자막 전용 추출기

3. **유틸리티 기능 분리**:

   - `app/subtitle/utils/config.py`: 자막 관련 설정 관리
   - `app/subtitle/utils/html.py`: HTML 태그 처리
   - `app/subtitle/utils/filename.py`: 파일명 조작 및 처리
   - `app/subtitle/utils/time.py`: 시간 형식 변환
   - `app/subtitle/utils/media.py`: 미디어 파일 처리

4. **HTMX 기능 유지**:

   - 모든 기존 HTMX 템플릿 기능 그대로 지원
   - 부분 페이지 렌더링 및 비동기 업데이트 기능 유지

5. **레거시 코드 보존**:
   - `legacy/app/routes/subtitle_encoding.py`: 기존 코드 백업
   - 필요시 참조 가능하도록 구조 유지

### 성능 및 코드 품질 개선

- 중복 코드 제거로 전체 코드베이스 크기 감소
- 모듈화로 인한 유지보수성 및 가독성 향상
- 비동기 처리 개선
- 오류 상황에 대한 명확한 로깅 및 예외 처리
- 타입 힌트 추가로 개발 시 코드 완성 및 오류 검증 향상

### 향후 계획

- 더 효율적인 인코딩 감지 알고리즘 구현
- OS별 특화된 코드 경로 추가
- 통합 테스트 및 단위 테스트 작성
- 자막 분석 및 변환 UI/UX 개선

## [2023-05-10] 마크다운 기반 API 문서 시스템 구현

### 주요 구현 내용

- 마크다운 문서를 HTML로 변환하여 보여주는 문서 시스템 구현
- 프로젝트 구조, API 엔드포인트, 라우터 정보를 체계적으로 정리한 문서 작성
- 문서 목록 및 탐색 기능 제공

### 개선된 부분

- `docs/api_reference.md`: API와 라우터에 대한 포괄적인 문서화
- `app/routes/docs.py`: 마크다운 렌더링 기능을 제공하는 라우터 모듈
- `templates/docs/`: 문서를 표시하기 위한 템플릿 파일들
  - `docs_layout.html`: 문서 페이지의 기본 레이아웃
  - `index.html`: 문서 목록 페이지
  - `document.html`: 개별 문서 페이지

### 기술적 세부 사항

- Python 마크다운 파서를 사용하여 마크다운을 HTML로 변환
- 코드 하이라이팅을 위한 Pygments 통합
- 문서 메타데이터 처리를 위한 front-matter 지원
- 반응형 디자인으로 모바일 및 데스크탑 환경 모두 지원

### 남은 작업

- 추가 문서 작성 (아키텍처 설계, 개발 가이드 등)
- API 자동 문서화 연동 (OpenAPI 스펙 문서와 통합)
- 검색 기능 추가
- 문서 버전 관리 시스템 도입

관련 파일:

- app/routes/docs.py
- docs/api_reference.md
- templates/docs/docs_layout.html
- templates/docs/index.html
- templates/docs/document.html
