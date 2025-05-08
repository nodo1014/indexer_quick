"""
자막 관련 모델 정의

자막과 관련된 데이터 모델 클래스를 제공합니다.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class SubtitleBase(BaseModel):
    """자막 기본 모델"""
    media_id: int
    start_time: int  # 밀리초 단위
    end_time: int  # 밀리초 단위
    start_time_text: str  # 표시용 시간 텍스트 (HH:MM:SS,mmm)
    end_time_text: str  # 표시용 시간 텍스트 (HH:MM:SS,mmm)
    content: str  # 자막 내용
    lang: str = "en"  # 언어 코드 (기본값: 영어)


class SubtitleCreate(SubtitleBase):
    """자막 생성 모델"""
    pass


class SubtitleUpdate(BaseModel):
    """자막 업데이트 모델"""
    media_id: Optional[int] = None
    start_time: Optional[int] = None
    end_time: Optional[int] = None
    start_time_text: Optional[str] = None
    end_time_text: Optional[str] = None
    content: Optional[str] = None
    lang: Optional[str] = None


class SubtitleInDB(SubtitleBase):
    """데이터베이스 내 자막 모델"""
    id: int

    class Config:
        orm_mode = True


class Subtitle(SubtitleInDB):
    """자막 응답 모델"""
    media_path: Optional[str] = None
    highlight: Optional[str] = None  # 검색 결과에서 강조 표시된 텍스트
    
    @classmethod
    def from_db(cls, db_model: dict):
        """데이터베이스 모델에서 응답 모델 생성"""
        # 기본 필드 복사
        subtitle = cls(
            id=db_model['id'],
            media_id=db_model['media_id'],
            start_time=db_model['start_time'],
            end_time=db_model['end_time'],
            start_time_text=db_model['start_time_text'],
            end_time_text=db_model['end_time_text'],
            content=db_model['content'],
            lang=db_model['lang']
        )
        
        # 추가 필드가 있으면 설정
        if 'media_path' in db_model:
            subtitle.media_path = db_model['media_path']
        
        if 'highlight' in db_model:
            subtitle.highlight = db_model['highlight']
            
        return subtitle


class SubtitleList(BaseModel):
    """자막 목록 응답 모델"""
    items: List[Subtitle]
    total: int
    page: int
    per_page: int
    total_pages: int


class SearchQuery(BaseModel):
    """자막 검색 쿼리 모델"""
    query: str
    lang: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    page: int = 1
    per_page: int = 50


class SearchResult(BaseModel):
    """검색 결과 모델"""
    items: List[Subtitle]
    query: str
    total_results: int
    page: int
    per_page: int
    total_pages: int
    filters_applied: Dict[str, Any] = Field(default_factory=dict)