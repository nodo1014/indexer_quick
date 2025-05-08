# 프로젝트 진행 상황 (2024-05-30)

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
app/                        # 메인 애플리케이션 코드
  ├── __init__.py           # 애플리케이션 초기화
  ├── config.py             # 설정 관리
  ├── database.py           # 데이터베이스 연결 및 쿼리 관리
  ├── main.py               # FastAPI 애플리케이션 정의
  ├── models/               # 데이터 모델
  │   ├── __init__.py
  │   ├── media.py
  │   └── subtitle.py
  ├── routes/               # API 라우트
  │   ├── __init__.py
  │   ├── indexing.py
  │   ├── search.py
  │   └── stats.py
  ├── services/             # 비즈니스 로직 서비스
  │   ├── __init__.py
  │   ├── indexer.py
  │   ├── search.py
  │   └── stats.py
  └── utils/                # 유틸리티 기능 (구현 완료)
      ├── __init__.py       # 패키지 초기화 및 임포트
      ├── constants.py      # 상수 정의
      ├── helpers.py        # 도움 함수
      └── logging.py        # 로깅 설정

static/                     # 정적 파일 (CSS, JS, 이미지)
  ├── css/                  # CSS 파일
  ├── js/                   # 자바스크립트 파일
  │   └── components/       # 컴포넌트 모듈
  │       └── video-components/  # 비디오 플레이어 컴포넌트
  │           ├── video-player.js
  │           ├── subtitle-controller.js
  │           ├── playback-manager.js
  │           └── bookmark-manager.js
  └── img/                  # 이미지 파일

templates/                  # Jinja2 템플릿
  ├── base.html             # 기본 레이아웃 템플릿
  ├── index.html            # 메인 페이지
  ├── search.html           # 검색 페이지
  └── settings.html         # 설정 페이지

# 루트 디렉토리의 레거시 파일 (리팩토링 필요)
indexer.py                  # 레거시 인덱서 코드 (689 라인)
database.py                 # 레거시 데이터베이스 코드 (672 라인)
media_index.db              # SQLite 데이터베이스
config.json                 # 애플리케이션 설정 파일
main.py                     # 애플리케이션 진입점
```

## 다음 작업 예정

### 대규모 파일 리팩토링
- 루트 디렉토리의 레거시 파일 리팩토링:
  - `indexer.py`를 app/services/indexer.py로 완전히 이전
  - `database.py`를 app/database.py 및 관련 모듈로 분리
- app/ 디렉토리의 큰 파일들 추가 분리:
  - `app/main.py`(506라인)에서 라우트 함수들을 app/routes/ 모듈로 더 분리
  - `app/database.py`(985라인)를 모델별 데이터 액세스 객체로 분리

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

## [2023-05-10] 비디오 플레이어 코드 리팩토링 및 자막 클릭 재생 문제 해결

### 1. 비디오 플레이어 관련 코드 통합 및 리팩토링
- 문제: 여러 JavaScript 파일에 중복된 비디오 플레이어 코드로 인한 혼란 및 충돌
- 원인:
  - `/static/js/components/video-components/` 디렉토리의 모듈화된 구현
  - `/static/js/components/video-js/` 디렉토리의 Video.js 어댑터
  - `/static/js/components/video-player.js` 레거시 구현
- 해결:
  - `templates/search.html`: 비디오 플레이어 초기화 코드 단일화 및 개선
  - `static/js/components/video-components/video-player.js`: 코드 정리 및 Promise 기반 초기화
  - `static/js/components/video-components/subtitle-controller.js`: 자막 클릭 핸들러 개선
  - `static/js/search.js`: 중복 코드 제거 및 자막 데이터 처리 개선

### 2. 비디오 재생 동작 개선
- 문제: 자막 클릭 시 비디오가 재생되지 않는 문제
- 원인:
  - 자막 요소의 데이터 속성 값 불일치 (`mediaPath`/`media_path`, `startTime`/`start_time` 등)
  - 비디오 플레이어 초기화 순서 문제
  - 클릭 이벤트 전파 문제 (북마크/태그 버튼 클릭 시에도 자막 클릭 이벤트 발생)
- 해결:
  - `SubtitleController._extractMediaDataFromElement()` 메서드 구현으로 다양한 데이터 속성명 처리
  - 자막 요소 클릭 처리 로직 개선 (버튼 클릭 시 자막 재생 이벤트 방지)
  - 시간 값 처리 개선 (밀리초/초 자동 변환, 유효하지 않은 값 처리)

### 3. 디버깅 및 오류 처리 개선
- 모든 관련 코드에 디버깅 로그 추가
- 오류 발생 시 더 자세한 오류 메시지 제공
- 누락될 수 있는 요소에 대한 존재 여부 확인 로직 추가
- Promise 기반 초기화로 비동기 작업 순서 보장

### 4. 인터페이스 개선
- 북마크 필터링 기능 구현 (북마크된 자막만 표시)
- 검색 결과 처리 및 표시 로직 개선
- 자막 데이터 형식 변환 (밀리초/초 단위 자동 처리)

### 다음 계획
- 나머지 레거시 코드 및 중복 코드 정리 (`static/js/components/video-js/` 디렉토리 등)
- 북마크 및 태그 기능 추가 개선
- 검색 결과에서 미디어 파일별 그룹화 기능 추가
- 사용자 인터페이스 개선
