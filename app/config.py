"""
설정 관리 모듈

애플리케이션 설정을 로드하고 저장하는 기능을 제공합니다.
"""

import os
import json
from pathlib import Path
from typing import Any, Dict, Optional, Union


class Config:
    """설정 관리 클래스"""
    
    def __init__(self, config_path: str = "config.json"):
        """
        설정 관리 클래스 초기화
        
        Args:
            config_path: 설정 파일 경로 (기본값: "config.json")
        """
        self.config_path = Path(config_path)
        self.data = self.load()
    
    def load(self) -> Dict[str, Any]:
        """
        설정 파일 로드
        
        Returns:
            Dict[str, Any]: 설정 데이터
        """
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as file:
                    return json.load(file)
            except Exception as e:
                print(f"설정 파일 로딩 오류: {e}")
                
        return self._get_default_config()
    
    def save(self) -> bool:
        """
        현재 설정을 파일에 저장
        
        Returns:
            bool: 저장 성공 여부
        """
        try:
            with open(self.config_path, 'w', encoding='utf-8') as file:
                json.dump(self.data, file, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"설정 저장 오류: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        설정 값 조회
        
        Args:
            key: 설정 키
            default: 키가 없을 경우 반환할 기본값
        
        Returns:
            Any: 설정 값 또는 기본값
        """
        return self.data.get(key, default)
    
    def set(self, key: str, value: Any) -> bool:
        """
        설정 값 변경
        
        Args:
            key: 설정 키
            value: 설정 값
        
        Returns:
            bool: 설정 성공 여부
        """
        self.data[key] = value
        return self.save()
    
    def update(self, settings: Dict[str, Any]) -> bool:
        """
        여러 설정 값 일괄 업데이트
        
        Args:
            settings: 업데이트할 설정 키-값 쌍
        
        Returns:
            bool: 업데이트 성공 여부
        """
        self.data.update(settings)
        return self.save()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """
        기본 설정 데이터 반환
        
        Returns:
            Dict[str, Any]: 기본 설정 데이터
        """
        return {
            "root_dir": "",
            "media_extensions": [".mp4", ".mkv", ".avi", ".mov", ".wmv"],
            "subtitle_extension": ".srt",
            "db_path": "media_index.db",
            "indexing_strategy": "standard",
            "max_threads": os.cpu_count() or 4,
            "last_scan_time": None
        }
    
    def get_absolute_media_path(self, relative_path: str) -> str:
        """
        상대 경로를 절대 경로로 변환
        
        Args:
            relative_path: 미디어 루트 디렉토리를 기준으로 한 상대 경로
            
        Returns:
            str: 절대 경로
        """
        # 이미 절대 경로라면 그대로 반환
        if os.path.isabs(relative_path):
            return relative_path
            
        # 현재 마운트 포인트 확인
        mount_point = self.data.get('path_handling', {}).get('media_mount_point')
        if not mount_point:
            mount_point = self.data.get('root_dir', '')
            
        return os.path.join(mount_point, relative_path)
    
    def get_relative_media_path(self, absolute_path: str) -> str:
        """
        절대 경로를 미디어 루트 디렉토리를 기준으로 한 상대 경로로 변환
        
        Args:
            absolute_path: 절대 경로
            
        Returns:
            str: 상대 경로 (미디어 루트 디렉토리를 기준으로)
        """
        # 이미 상대 경로라면 그대로 반환
        if not os.path.isabs(absolute_path):
            return absolute_path
            
        # 현재 마운트 포인트 확인
        mount_point = self.data.get('path_handling', {}).get('media_mount_point')
        if not mount_point:
            mount_point = self.data.get('root_dir', '')
            
        if not mount_point or not absolute_path.startswith(mount_point):
            # 대체 마운트 포인트 확인
            alt_mount_points = self.data.get('path_handling', {}).get('alternative_mount_points', [])
            for alt_mount in alt_mount_points:
                if absolute_path.startswith(alt_mount):
                    mount_point = alt_mount
                    break
                    
        # 마운트 포인트로 시작하지 않으면 원래 경로 반환
        if not mount_point or not absolute_path.startswith(mount_point):
            return absolute_path
            
        # 마운트 포인트를 제거하여 상대 경로 생성
        rel_path = absolute_path[len(mount_point):].lstrip('/')
        return rel_path
        
    def should_store_relative_paths(self) -> bool:
        """
        상대 경로로 저장할지 여부를 확인
        
        Returns:
            bool: 상대 경로로 저장할지 여부
        """
        return self.data.get('path_handling', {}).get('store_relative_paths', False)
        
    def use_fixed_media_path(self) -> bool:
        """
        고정된 미디어 경로 정책을 사용할지 여부를 확인
        
        Returns:
            bool: 고정 경로 정책 사용 여부
        """
        return self.data.get('path_handling', {}).get('use_fixed_media_path', False)
        
    def get_media_path(self, path: str) -> str:
        """
        미디어 파일 경로를 통일된 형식으로 변환
        이 함수는 북마크/태그 참조를 위한 일관된 경로를 보장합니다.
        
        Args:
            path: 처리할 미디어 경로
            
        Returns:
            str: 통일된 형식의 미디어 경로
        """
        # 이미 상대 경로인 경우 절대 경로로 변환
        if not os.path.isabs(path):
            return self.get_absolute_media_path(path)
            
        # 마운트 포인트 확인
        mount_point = self.data.get('path_handling', {}).get('media_mount_point')
        if not mount_point:
            mount_point = self.data.get('root_dir', '')
            
        # 경로가 마운트 포인트로 시작하지 않는 경우, 대체 마운트 포인트 확인
        if not path.startswith(mount_point):
            alt_mount_points = self.data.get('path_handling', {}).get('alternative_mount_points', [])
            
            for alt_mount in alt_mount_points:
                if path.startswith(alt_mount):
                    # 경로의 시작 부분을 대체 마운트 포인트에서 기본 마운트 포인트로 변경
                    relative_part = path[len(alt_mount):].lstrip('/')
                    return os.path.join(mount_point, relative_part)
        
        # 이미 기본 마운트 포인트로 시작하는 경우 또는 다른 경로인 경우
        return path


# 전역 설정 객체 생성
config = Config()