"""
문서 라우터 모듈

마크다운 문서를 HTML로 렌더링하여 제공하는 기능을 담당합니다.
"""

import os
import re
import markdown
import frontmatter
from pathlib import Path
from typing import Dict, List, Optional
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

# 라우터 설정
router = APIRouter(tags=["docs"])

# 템플릿 설정
templates = Jinja2Templates(directory="templates")

# 문서 디렉토리 설정
DOCS_DIR = Path("docs")

def get_markdown_files() -> List[Dict[str, str]]:
    """
    문서 디렉토리에서 마크다운 파일 목록을 가져옵니다.
    
    Returns:
        List[Dict[str, str]]: 마크다운 파일 목록 (경로, 제목)
    """
    if not DOCS_DIR.exists():
        return []
        
    markdown_files = []
    
    for file_path in DOCS_DIR.glob("**/*.md"):
        # 파일 경로를 상대 경로로 변환
        relative_path = file_path.relative_to(DOCS_DIR)
        
        # frontmatter에서 제목 추출 또는 파일명에서 제목 생성
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                post = frontmatter.load(f)
                title = post.get('title', None)
                
                if not title:
                    # 파일명에서 제목 생성
                    title = str(relative_path.stem).replace('_', ' ').title()
                    
            # 파일 정보 추가
            markdown_files.append({
                'path': str(relative_path),
                'title': title
            })
        except Exception as e:
            print(f"Error loading markdown file {file_path}: {e}")
            continue
    
    return sorted(markdown_files, key=lambda x: x['title'])

def render_markdown(file_path: Path) -> str:
    """
    마크다운 파일을 HTML로 변환합니다.
    
    Args:
        file_path: 마크다운 파일 경로
        
    Returns:
        str: 변환된 HTML
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # frontmatter 추출
        post = frontmatter.loads(content)
        
        # 마크다운을 HTML로 변환
        extensions = [
            'markdown.extensions.tables',
            'markdown.extensions.fenced_code',
            'markdown.extensions.codehilite',
            'markdown.extensions.toc'
        ]
        
        html_content = markdown.markdown(post.content, extensions=extensions)
        
        return html_content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error rendering markdown: {str(e)}")

@router.get("/docs", response_class=HTMLResponse)
async def docs_index(request: Request):
    """
    문서 홈페이지를 반환합니다.
    """
    markdown_files = get_markdown_files()
    
    # 문서가 없으면 안내 메시지 표시
    if not markdown_files:
        return templates.TemplateResponse(
            "docs/index.html", 
            {"request": request, "title": "문서 없음", "message": "문서가 없습니다."}
        )
    
    return templates.TemplateResponse(
        "docs/index.html", 
        {"request": request, "title": "API 문서", "docs": markdown_files}
    )

@router.get("/docs/{doc_path:path}", response_class=HTMLResponse)
async def view_doc(request: Request, doc_path: str):
    """
    특정 문서를 보여줍니다.
    
    Args:
        request: FastAPI 요청 객체
        doc_path: 문서 경로
    """
    # .md 확장자가 없으면 추가
    if not doc_path.endswith('.md'):
        doc_path = f"{doc_path}.md"
    
    # 문서 파일 경로
    file_path = DOCS_DIR / doc_path
    
    # 파일이 존재하지 않으면 404 오류
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Document not found")
    
    # 마크다운을 HTML로 변환
    html_content = render_markdown(file_path)
    
    # 문서 제목 추출
    title = os.path.basename(doc_path).replace('.md', '').replace('_', ' ').title()
    
    return templates.TemplateResponse(
        "docs/document.html", 
        {
            "request": request, 
            "title": title, 
            "content": html_content,
            "docs": get_markdown_files(),
            "current_doc": doc_path
        }
    ) 