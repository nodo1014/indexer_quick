"""
인덱싱 서비스 모듈 (리팩토링됨)

이 파일은 호환성을 위해 유지됩니다.
실제 구현은 app/services/indexer/ 디렉토리로 이동되었습니다.
"""

# 리팩토링된 인덱서 서비스 가져오기
from app.services.indexer import indexer_service

# 업데이트 함수 가져오기
from app.services.indexer.base import update_fts_index
