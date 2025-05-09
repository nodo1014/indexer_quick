"""
인덱서 패키지 초기화 모듈
"""

# 표준 인덱싱 전략에서 생성된 indexer_service 인스턴스 가져오기
from app.services.indexer.strategy_standard import indexer_service

# 전략 클래스 가져오기
from app.services.indexer.base import IndexingStrategy
from app.services.indexer.strategy_standard import StandardIndexingStrategy
from app.services.indexer.strategy_delayed_language import DelayedLanguageIndexingStrategy