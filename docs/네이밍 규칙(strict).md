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



### 📘 프로젝트 구조 및 명명 규칙 (Strict)

다음은 이 프로젝트에서 반드시 지켜야 하는 디렉토리 구조, 파일명, 클래스 및 함수 명명 규칙입니다. 어떤 파일을 생성하거나 리팩토링하든, 이 규칙을 어기지 마십시오.

---

🔹 [1] 디렉토리 구조 규칙
- 디렉토리는 기능 단위로 구분하고, 의미 없는 이름 사용 금지
- 예: `indexer/`, `media/`, `subtitles/`, `auth/` 등
- ❌ 금지: `base/`, `components/`, `utils/`, `common/`

---

🔹 [2] 파일명 규칙
- 파일명은 반드시 **`[기능]_[역할].py`** 형식 사용
  - 예: `indexing_service.py`, `subtitle_processor.py`, `media_scanner.py`
- ❌ 금지: `base.py`, `main.py`, `util.py`, `common.py`

---

🔹 [3] 클래스 명명 규칙
- 클래스명은 파일명에서 유추 가능해야 함
  - `IndexingService` → `indexing_service.py`
  - `MediaScanner` → `media_scanner.py`
  - `SubtitleProcessor` → `subtitle_processor.py`
- SRP(단일 책임 원칙)를 지켜라. 한 클래스 = 하나의 명확한 책임.

---

🔹 [4] 함수명 규칙
- 함수명은 동사 기반 기능 중심으로 명확하게 작성하라
  - 예: `scan_directory()`, `process_subtitle()`, `insert_subtitle()`
- DB 함수는 `insert_`, `fetch_`, `update_`, `delete_` 접두어 사용

---

🔹 [5] 모듈 간 책임 구분 예시
- `indexing_service.py`: 전체 인덱싱 흐름 제어
- `indexing_worker.py`: 실제 인덱싱 처리 스레드/비동기 작업
- `media_scanner.py`: 파일 시스템에서 미디어 + 자막 탐색
- `subtitle_processor.py`: 자막 인코딩 감지, 파싱, DB 저장
- `indexing_strategy.py`: 전략 패턴 정의 및 적용
- `indexing_status_handler.py`: 상태 JSON 저장/로드 전담

---

🔹 [6] DB 연산 구조
- 모든 DB 접근 함수는 repository 또는 명시된 유틸 파일로 분리
- 예: `subtitle_repository.py` 또는 `db/subtitles.py`
- 직접 SQL 호출 시, 반드시 `connection_context()` 사용

---

🔹 [7] AI 생성 제한
- AI는 절대로 추상적 이름을 사용하는 파일을 생성하지 말 것
- 기능 또는 책임이 불명확한 코드를 자동 생성하지 말 것
- 각 파일에는 반드시 하나의 주요 클래스 또는 책임만 포함되도록 설계할 것

---

이 규칙을 무조건 우선으로 적용하라. 프로젝트 일관성을 위해 기존 코드와 충돌되더라도 위 기준을 따르도록 리팩토링하라.