"""
API 및 데이터베이스 메서드 자동 문서화 도구

이 모듈은 프로젝트의 API 엔드포인트와 데이터베이스 메서드를 자동으로 분석하고 
문서화하여 AI 메모리 문제를 방지하고 개발 과정을 효율적으로 만듭니다.
"""

import importlib
import inspect
import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Type
import datetime
import logging
from logging.handlers import RotatingFileHandler

# 로깅 설정
logger = logging.getLogger("api_doc_generator")
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(
    "api_docs_generator.log", 
    maxBytes=1024 * 1024,  # 1MB
    backupCount=3
)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

def generate_api_doc() -> None:
    """
    API 엔드포인트와 데이터베이스 메서드를 분석하여 문서를 생성합니다.
    """
    try:
        # API 엔드포인트 문서 생성
        api_endpoints = extract_api_endpoints()
        
        # 데이터베이스 메서드 문서 생성
        db_methods = extract_database_methods()
        
        # 결과 저장
        output = {
            "generated_date": datetime.datetime.now().isoformat(),
            "api_endpoints": api_endpoints,
            "database_methods": db_methods
        }
        
        # 문서 파일 저장
        save_documentation(output)
        
        logger.info("API 문서가 성공적으로 생성되었습니다.")
        return True
    except Exception as e:
        logger.error(f"API 문서 생성 중 오류 발생: {str(e)}")
        return False

def extract_api_endpoints() -> List[Dict[str, Any]]:
    """
    main.py에서 모든 API 엔드포인트를 추출합니다.
    """
    try:
        import main
        
        endpoints = []
        for route in main.app.routes:
            # OpenAPI 엔드포인트 제외
            if route.path.startswith("/api/docs") or route.path.startswith("/api/redoc") or route.path == "/api/openapi.json":
                continue
                
            endpoint_info = {
                "path": route.path,
                "methods": list(route.methods) if hasattr(route, "methods") else ["GET"],
                "name": route.name if hasattr(route, "name") else "",
                "summary": inspect.getdoc(route.endpoint) if hasattr(route, "endpoint") else ""
            }
            
            # 함수 파라미터 분석
            if hasattr(route, "endpoint") and callable(route.endpoint):
                params = inspect.signature(route.endpoint).parameters
                endpoint_info["parameters"] = [
                    {"name": name, "type": str(param.annotation).replace("<class '", "").replace("'>", "")}
                    for name, param in params.items()
                ]
            
            endpoints.append(endpoint_info)
        
        return endpoints
    except Exception as e:
        logger.error(f"API 엔드포인트 추출 중 오류 발생: {str(e)}")
        return []

def extract_database_methods() -> List[Dict[str, Any]]:
    """
    database.py에서 모든 데이터베이스 메서드를 추출합니다.
    """
    try:
        import database
        
        db_methods = []
        
        # Database 클래스 분석
        if hasattr(database, "Database"):
            db_class = database.Database
            for name, method in inspect.getmembers(db_class, predicate=inspect.isfunction):
                # 내장 메서드 무시
                if name.startswith("__"):
                    continue
                
                method_info = {
                    "name": name,
                    "docstring": inspect.getdoc(method),
                    "parameters": []
                }
                
                # 함수 파라미터 분석
                params = inspect.signature(method).parameters
                method_info["parameters"] = [
                    {"name": name, "type": str(param.annotation).replace("<class '", "").replace("'>", "")}
                    for name, param in params.items() if name != "self"
                ]
                
                db_methods.append(method_info)
        
        return db_methods
    except Exception as e:
        logger.error(f"데이터베이스 메서드 추출 중 오류 발생: {str(e)}")
        return []

def save_documentation(output: Dict[str, Any]) -> None:
    """
    생성된 문서를 JSON 파일로 저장합니다.
    """
    output_dir = Path("static/meta")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # API 문서 저장
    with open(output_dir / "api_documentation.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    # 프론트엔드에서 사용할 수 있는 간략한 버전 생성
    frontend_doc = {
        "updated_at": output["generated_date"],
        "endpoints": [{"path": ep["path"], "methods": ep["methods"], "name": ep["name"]} 
                     for ep in output["api_endpoints"]]
    }
    
    with open(output_dir / "api_endpoints.json", "w", encoding="utf-8") as f:
        json.dump(frontend_doc, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    # 명령줄에서 직접 실행할 때 문서 생성
    generate_api_doc()