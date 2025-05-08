# 자막 인덱서 애플리케이션 리팩토링 계획

## 1. 목표

- 코드 가독성 및 유지보수성 향상
- 중복 코드 제거
- 관심사 분리를 통한 모듈화
- FastAPI 기능 활용 최적화
- 확장성 개선

## 2. 디렉토리 구조

```
app/
  ├── __init__.py          # 애플리케이션 초기화
  ├── config.py            # 설정 관리
  ├── database.py          # 데이터베이스 연결 관리
  ├── main.py              # FastAPI 애플리케이션 엔트리포인트
  │
  ├── models/              # 데이터 모델 정의
  │   ├── __init__.py
  │   ├── media.py         # 미디어 파일 관련 모델
  │   └── subtitle.py      # 자막 관련 모델
  │
  ├── routes/              # API 라우팅
  │   ├── __init__.py
  │   ├── ai.py            # AI 관련 라우트
  │   ├── indexing.py      # 인덱싱 관련 라우트
  │   ├── search.py        # 검색 관련 라우트
  │   ├── settings.py      # 설정 관련 라우트
  │   └── stats.py         # 통계 관련 라우트
  │
  ├── services/            # 비즈니스 로직
  │   ├── __init__.py
  │   ├── indexer.py       # 인덱싱 서비스
  │   ├── media.py         # 미디어 관리 서비스
  │   ├── search.py        # 검색 서비스
  │   └── stats.py         # 통계 서비스
  │
  └── utils/               # 유틸리티 함수
      ├── __init__.py
      ├── constants.py     # 상수 정의
      ├── helpers.py       # 도움 함수
      └── logging.py       # 로깅 설정
```

## 3. 리팩토링 단계

### 3.1 설정 관리 분리

1. `app/config.py` 파일에 설정 관리 로직 이동
   - 설정 파일 로드 및 저장
   - 기본 설정 정의
   - 환경 변수 지원

### 3.2 데이터베이스 계층 개선

1. `app/database.py` 개선

   - 데이터베이스 연결 관리
   - 테이블 초기화
   - 공통 쿼리 함수

2. 데이터 모델 정의
   - `app/models/media.py`: 미디어 파일 모델
   - `app/models/subtitle.py`: 자막 모델

### 3.3 서비스 계층 구현

1. 인덱서 서비스 (`app/services/indexer.py`)

   - 인덱싱 프로세스 관리
   - 자막 파싱 로직

2. 미디어 관리 서비스 (`app/services/media.py`)

   - 미디어 파일 CRUD 작업
   - 자막 정보 관리

3. 검색 서비스 (`app/services/search.py`)

   - 자막 검색 로직
   - 검색 결과 포맷팅

4. 통계 서비스 (`app/services/stats.py`)
   - 통계 계산 로직
   - 보고서 생성

### 3.4 API 라우트 분리

1. 검색 관련 라우트 (`app/routes/search.py`)

   - 자막 검색 엔드포인트

2. 인덱싱 관련 라우트 (`app/routes/indexing.py`)

   - 인덱싱 시작/중지/일시정지/재개 엔드포인트
   - 인덱싱 상태 엔드포인트

3. 설정 관련 라우트 (`app/routes/settings.py`)

   - 설정 조회 및 저장 엔드포인트
   - 디렉토리 브라우징 엔드포인트

4. 통계 관련 라우트 (`app/routes/stats.py`)

   - 통계 데이터 제공 엔드포인트

5. AI 관련 라우트 (`app/routes/ai.py`)
   - AI 시스템을 위한 엔드포인트

### 3.5 유틸리티 함수 분리

1. 도움 함수 (`app/utils/helpers.py`)

   - 공통으로 사용되는 도움 함수

2. 상수 정의 (`app/utils/constants.py`)

   - 애플리케이션 전반에서 사용되는 상수

3. 로깅 설정 (`app/utils/logging.py`)
   - 로깅 설정 및 필터

### 3.6 메인 애플리케이션 재구성

1. 새로운 `app/main.py` 구현
   - FastAPI 애플리케이션 초기화
   - 라우트 등록
   - 미들웨어 설정
   - 정적 파일 및 템플릿 설정

## 4. 개선 사항

1. **FastAPI 기능 활용**

   - 의존성 주입 시스템 적극 활용
   - Pydantic 모델 사용
   - 경로 연산자 개선

2. **데이터 검증**

   - 입력 데이터 검증 강화
   - 오류 처리 개선

3. **API 문서화**

   - OpenAPI 스키마 개선
   - 라우트 문서화 향상

4. **테스트 지원**
   - 단위 테스트 용이성 향상
   - 모의 객체(mock) 사용 용이성

## 5. 실행 계획

1. **설정 관리** 구현
2. **데이터베이스 계층** 구현
3. **모델** 구현
4. **서비스** 구현
5. **라우트** 구현
6. **메인 애플리케이션** 구현

각 단계마다 기능이 올바르게 작동하는지 검증하고 필요시 조정합니다.
