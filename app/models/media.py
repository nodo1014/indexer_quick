"""
미디어 파일 관련 모델 정의

미디어 파일과 관련된 데이터 모델 클래스를 제공합니다.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class MediaBase(BaseModel):
    """미디어 파일 기본 모델"""
    path: str
    has_subtitle: bool = False
    size: int = 0
    last_modified: Optional[str] = None


class MediaCreate(MediaBase):
    """미디어 파일 생성 모델"""
    pass


class MediaUpdate(BaseModel):
    """미디어 파일 업데이트 모델"""
    path: Optional[str] = None
    has_subtitle: Optional[bool] = None
    size: Optional[int] = None
    last_modified: Optional[str] = None


class MediaInDB(MediaBase):
    """데이터베이스 내 미디어 파일 모델"""
    id: int

    class Config:
        orm_mode = True


class Media(MediaInDB):
    """미디어 파일 응답 모델"""
    subtitle_count: Optional[int] = None
    file_name: Optional[str] = None
    file_extension: Optional[str] = None
    
    @classmethod
    def from_db(cls, db_model: dict, subtitle_count: Optional[int] = None):
        """데이터베이스 모델에서 응답 모델 생성"""
        import os
        
        # 파일 이름과 확장자 추출
        basename = os.path.basename(db_model['path']) if db_model.get('path') else ""
        root, ext = os.path.splitext(basename)
        
        return cls(
            id=db_model['id'],
            path=db_model['path'],
            has_subtitle=db_model['has_subtitle'],
            size=db_model['size'],
            last_modified=db_model['last_modified'],
            subtitle_count=subtitle_count,
            file_name=root,
            file_extension=ext
        )


class MediaList(BaseModel):
    """미디어 파일 목록 응답 모델"""
    items: List[Media]
    total: int
    page: int
    per_page: int
    total_pages: int