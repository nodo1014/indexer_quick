#!/usr/bin/env python
"""
데이터베이스 경로 설정 스크립트

config.json에 저장된 위치를 확인하고 데이터베이스 환경 변수를 설정합니다.
"""

import os
import json
import logging
import sys
import argparse

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_config():
    """설정 파일에서 데이터베이스 경로를 로드"""
    config_path = "config.json"
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config
        except Exception as e:
            logger.error(f"설정 파일 로드 오류: {e}")
            return {"db_path": "media_index.db"}
    else:
        logger.warning(f"설정 파일이 존재하지 않습니다: {config_path}")
        return {"db_path": "media_index.db"}

def update_config(config, key, value):
    """설정 파일 업데이트"""
    config_path = "config.json"
    
    config[key] = value
    
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        logger.info(f"설정 파일 업데이트 완료: {key}={value}")
        return True
    except Exception as e:
        logger.error(f"설정 파일 업데이트 오류: {e}")
        return False

def set_db_path_env(db_path):
    """데이터베이스 경로 환경 변수 설정"""
    os.environ["DB_PATH"] = db_path
    logger.info(f"환경 변수 설정: DB_PATH={db_path}")

def check_db_path():
    """현재 데이터베이스 경로 확인"""
    config = get_config()
    db_path = config.get("db_path", "media_index.db")
    
    # 절대 경로 확인
    if not os.path.isabs(db_path):
        abs_path = os.path.abspath(db_path)
        logger.info(f"현재 DB 경로 (상대): {db_path}")
        logger.info(f"현재 DB 경로 (절대): {abs_path}")
    else:
        logger.info(f"현재 DB 경로 (절대): {db_path}")
    
    # 파일 존재 여부 확인
    if os.path.exists(db_path):
        size_mb = os.path.getsize(db_path) / (1024 * 1024)
        logger.info(f"DB 파일 크기: {size_mb:.2f} MB")
    else:
        logger.warning(f"DB 파일이 존재하지 않습니다: {db_path}")
    
    return db_path

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="데이터베이스 경로 관리 도구")
    parser.add_argument("--check", action="store_true", help="현재 DB 경로 확인")
    parser.add_argument("--set", type=str, help="DB 경로 지정")
    parser.add_argument("--reset", action="store_true", help="DB 경로 기본값(media_index.db)으로 초기화")
    
    args = parser.parse_args()
    
    # 기본 동작은 현재 경로 확인
    if not (args.check or args.set or args.reset):
        args.check = True
    
    config = get_config()
    
    if args.check:
        check_db_path()
    
    if args.set:
        update_config(config, "db_path", args.set)
        set_db_path_env(args.set)
    
    if args.reset:
        default_path = "media_index.db"
        update_config(config, "db_path", default_path)
        set_db_path_env(default_path)
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 