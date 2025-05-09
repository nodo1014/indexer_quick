"""
인덱싱 전략 모듈

미디어 파일과 자막을 인덱싱하는 다양한 전략을 정의합니다.
"""

import os
import time
import traceback
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from app.utils.logging import get_indexer_logger

# 로거 설정
logger = get_indexer_logger()


# FTS 인덱스 업데이트 함수
def update_fts_index(force: bool = False):
    """
    자막 변환 후 FTS 인덱스 업데이트
    
    Args:
        force: FTS 인덱스를 강제로 재구축할지 여부
        
    Returns:
        bool: 성공 여부
    """
    try:
        from app.database.subtitles import get_subtitle_count, rebuild_fts_index
        from app.database.connection import fetch_one
        
        logger.info("FTS 인덱스 업데이트 시작...")
        start_time = time.time()
        
        # subtitles 테이블의 레코드 수
        subtitles_count = get_subtitle_count()
        
        # FTS 테이블의 레코드 수
        fts_result = fetch_one("SELECT COUNT(*) as count FROM subtitles_fts")
        fts_count = fts_result["count"] if fts_result else 0
        
        # 레코드 수가 다르거나 강제 업데이트인 경우 FTS 인덱스 재구축
        if force or subtitles_count != fts_count:
            logger.info(f"FTS 인덱스 재구축 필요: subtitles={subtitles_count}, fts={fts_count}")
            result = rebuild_fts_index()
            
            if result and "count" in result:
                logger.info(f"FTS 인덱스 재구축 완료: {result['count']}개 항목 ({time.time() - start_time:.2f}초)")
                return True
            else:
                logger.error("FTS 인덱스 재구축 실패")
                return False
        else:
            logger.info(f"FTS 인덱스가 최신 상태입니다: {fts_count}개 항목")
            return True
            
    except Exception as e:
        logger.error(f"FTS 인덱스 업데이트 중 오류 발생: {str(e)}")
        logger.error(traceback.format_exc())
        return False


class IndexingStrategy(ABC):
    """인덱싱 전략 인터페이스"""
    
    @abstractmethod
    def process(self, indexer, media_files):
        """
        미디어 파일 목록을 처리하는 인덱싱 전략 구현
        
        Args:
            indexer: 상위 인덱서 인스턴스
            media_files: 처리할 미디어 파일 목록
        """
        pass
