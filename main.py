"""
이 파일은 app 패키지의 main.py를 실행하기 위한 진입점입니다.
리팩토링된 코드를 사용합니다.
"""

import uvicorn
from app.main import app

# 서버 직접 실행 코드
if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8080, reload=True)