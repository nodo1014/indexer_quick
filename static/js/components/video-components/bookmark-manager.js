/**
 * BookmarkManager
 * 비디오 플레이어의 북마크 및 태그 관련 기능을 담당하는 클래스
 * - 북마크 토글
 * - 태그 관리
 * - 북마크/태그 필터링
 */

export class BookmarkManager {
  constructor(player) {
    this.player = player;
    this.bookmarks = new Set();
    this.tags = new Map(); // Map<mediaPath:startTime, string[]>
    this.isBookmarkFilterActive = false;
    this.debugMode = true;
  }

  /**
   * 초기화 메서드
   */
  init() {
    this._loadBookmarks();
    this._setupEventListeners();
    this.setupSubtitleFeatures();
    this.debugLog("BookmarkManager 초기화 완료");
  }

  /**
   * 북마크 및 태그 관련 이벤트 리스너 설정
   * @private
   */
  _setupEventListeners() {
    // 북마크 필터 버튼
    const bookmarkFilterBtn = document.getElementById('bookmark-filter-btn');
    if (bookmarkFilterBtn) {
      bookmarkFilterBtn.addEventListener('click', () => {
        this.toggleBookmarkFilter();
      });
    }

    // 태그 클릭/추가/삭제 이벤트는 동적으로 setupSubtitleFeatures()에서 처리
  }

  /**
   * 북마크/태그 필터 토글
   */
  toggleBookmarkFilter() {
    this.isBookmarkFilterActive = !this.isBookmarkFilterActive;
    
    // 필터 버튼 상태 업데이트
    const filterBtn = document.getElementById('bookmark-filter-btn');
    if (filterBtn) {
      if (this.isBookmarkFilterActive) {
        filterBtn.classList.add('active');
        filterBtn.textContent = "★ 모두 보기";
      } else {
        filterBtn.classList.remove('active');
        filterBtn.textContent = "★ 북마크만 보기";
      }
    }
    
    // 자막 필터링 적용
    this._applyBookmarkFilter();
    
    this.debugLog(`북마크 필터 ${this.isBookmarkFilterActive ? '활성화' : '비활성화'}`);
  }

  /**
   * 북마크 필터 적용
   * @private
   */
  _applyBookmarkFilter() {
    const subtitles = document.querySelectorAll('.subtitle-pair');
    
    subtitles.forEach(subtitle => {
      const mediaPath = subtitle.dataset.mediaPath;
      const startTime = subtitle.dataset.startTime;
      const key = this._getBookmarkKey(mediaPath, startTime);
      
      if (this.isBookmarkFilterActive) {
        // 북마크 필터 활성화: 북마크된 항목만 표시
        subtitle.style.display = this.bookmarks.has(key) ? '' : 'none';
      } else {
        // 필터 비활성화: 모든 항목 표시
        subtitle.style.display = '';
      }
    });
    
    // 결과 수 업데이트
    this._updateResultCount();
  }

  /**
   * 결과 개수 표시 업데이트
   * @private
   */
  _updateResultCount() {
    const resultInfo = document.getElementById('current-result-info');
    if (!resultInfo) return;
    
    const visibleCount = document.querySelectorAll('.subtitle-pair:not([style*="display: none"])').length;
    const totalCount = document.querySelectorAll('.subtitle-pair').length;
    
    resultInfo.textContent = this.isBookmarkFilterActive 
      ? `북마크 ${visibleCount}/${totalCount}`
      : `결과 ${totalCount}개`;
  }

  /**
   * 북마크 및 태그 기능 설정
   */
  setupSubtitleFeatures() {
    document.addEventListener('click', (event) => {
      // 북마크 버튼 클릭 처리
      if (event.target.classList.contains('bookmark-btn')) {
        const subtitleElement = event.target.closest('.subtitle-pair');
        if (subtitleElement) {
          this._handleBookmarkClick(event.target, subtitleElement);
        }
      }
      
      // 태그 버튼 클릭 처리
      if (event.target.classList.contains('tag-btn')) {
        const subtitleElement = event.target.closest('.subtitle-pair');
        if (subtitleElement) {
          this._showTagInput(subtitleElement);
        }
      }
      
      // 태그 삭제 버튼 클릭 처리
      if (event.target.classList.contains('tag-remove')) {
        const tagEl = event.target.closest('.tag-item');
        const subtitleElement = event.target.closest('.subtitle-pair');
        if (tagEl && subtitleElement) {
          const tag = tagEl.dataset.tag;
          this._removeTag(subtitleElement, tag);
        }
      }
    });
    
    // 태그 입력 처리
    document.addEventListener('keypress', (event) => {
      if (event.key === 'Enter' && event.target.classList.contains('tag-input')) {
        const subtitleElement = event.target.closest('.subtitle-pair');
        if (subtitleElement) {
          const tag = event.target.value.trim();
          if (tag) {
            this._addTag(subtitleElement, tag);
            event.target.value = '';
          }
          
          // 입력 UI 숨기기
          event.target.parentElement.style.display = 'none';
        }
      }
    });
    
    // 초기 북마크/태그 렌더링
    this.renderTagsForAll();
  }

  /**
   * 모든 자막 요소에 대해 태그와 북마크 렌더링
   */
  renderTagsForAll() {
    const subtitles = document.querySelectorAll('.subtitle-pair');
    
    subtitles.forEach(subtitle => {
      const mediaPath = subtitle.dataset.mediaPath;
      const startTime = subtitle.dataset.startTime;
      const key = this._getBookmarkKey(mediaPath, startTime);
      
      // 북마크 상태 업데이트
      const bookmarkBtn = subtitle.querySelector('.bookmark-btn');
      if (bookmarkBtn) {
        bookmarkBtn.textContent = this.bookmarks.has(key) ? '★' : '☆';
        bookmarkBtn.classList.toggle('active', this.bookmarks.has(key));
      }
      
      // 태그 렌더링
      this._renderTags(subtitle);
    });
  }

  /**
   * 북마크 클릭 핸들러
   * @param {HTMLElement} bookmarkBtn - 북마크 버튼 요소
   * @param {HTMLElement} subtitleElement - 자막 요소
   * @private
   */
  _handleBookmarkClick(bookmarkBtn, subtitleElement) {
    const mediaPath = subtitleElement.dataset.mediaPath;
    const startTime = subtitleElement.dataset.startTime;
    const key = this._getBookmarkKey(mediaPath, startTime);
    
    // 북마크 토글
    const isBookmarked = this.bookmarks.has(key);
    
    if (isBookmarked) {
      // 북마크 제거
      this.bookmarks.delete(key);
      bookmarkBtn.textContent = '☆';
      bookmarkBtn.classList.remove('active');
    } else {
      // 북마크 추가
      this.bookmarks.add(key);
      bookmarkBtn.textContent = '★';
      bookmarkBtn.classList.add('active');
    }
    
    // 서버에 북마크 상태 저장
    this._saveBookmarkToServer(mediaPath, startTime, !isBookmarked);
    
    // 북마크 로컬 저장
    this._saveBookmarks();
    
    // 북마크 필터 적용 중이면 화면 업데이트
    if (this.isBookmarkFilterActive) {
      this._applyBookmarkFilter();
    }
    
    this.debugLog(`북마크 ${isBookmarked ? '제거' : '추가'}: ${mediaPath} (${startTime}s)`);
  }

  /**
   * 태그 입력 UI 표시
   * @param {HTMLElement} subtitleElement - 자막 요소
   * @private
   */
  _showTagInput(subtitleElement) {
    // 태그 입력 영역 찾기 또는 생성
    let tagInputContainer = subtitleElement.querySelector('.tag-input-container');
    
    if (!tagInputContainer) {
      tagInputContainer = document.createElement('div');
      tagInputContainer.className = 'tag-input-container';
      tagInputContainer.innerHTML = `
        <input type="text" class="tag-input" placeholder="태그 입력 후 엔터" />
      `;
      
      // 태그 컨테이너 다음에 추가
      const tagContainer = subtitleElement.querySelector('.tag-container');
      if (tagContainer) {
        tagContainer.after(tagInputContainer);
      } else {
        subtitleElement.appendChild(tagInputContainer);
      }
    }
    
    // 표시 및 포커스
    tagInputContainer.style.display = 'block';
    tagInputContainer.querySelector('.tag-input').focus();
  }

  /**
   * 태그 추가
   * @param {HTMLElement} subtitleElement - 자막 요소
   * @param {string} tag - 추가할 태그
   * @private
   */
  _addTag(subtitleElement, tag) {
    const mediaPath = subtitleElement.dataset.mediaPath;
    const startTime = subtitleElement.dataset.startTime;
    const key = this._getBookmarkKey(mediaPath, startTime);
    
    // 태그 목록 가져오기 또는 생성
    let tagList = this.tags.get(key) || [];
    
    // 이미 있는 태그면 무시
    if (tagList.includes(tag)) {
      this.debugLog(`이미 존재하는 태그: ${tag}`);
      return;
    }
    
    // 태그 추가
    tagList.push(tag);
    this.tags.set(key, tagList);
    
    // 서버에 태그 저장
    this._saveTagToServer(mediaPath, startTime, tag);
    
    // 태그 렌더링
    this._renderTags(subtitleElement);
    
    this.debugLog(`태그 추가: ${tag}, ${mediaPath} (${startTime}s)`);
  }

  /**
   * 태그 제거
   * @param {HTMLElement} subtitleElement - 자막 요소
   * @param {string} tagToRemove - 제거할 태그
   * @private
   */
  _removeTag(subtitleElement, tagToRemove) {
    const mediaPath = subtitleElement.dataset.mediaPath;
    const startTime = subtitleElement.dataset.startTime;
    const key = this._getBookmarkKey(mediaPath, startTime);
    
    // 태그 목록 가져오기
    let tagList = this.tags.get(key) || [];
    
    // 태그 제거
    tagList = tagList.filter(tag => tag !== tagToRemove);
    this.tags.set(key, tagList);
    
    // 서버에서 태그 제거
    this._deleteTagFromServer(mediaPath, startTime, tagToRemove);
    
    // 태그 렌더링
    this._renderTags(subtitleElement);
    
    this.debugLog(`태그 제거: ${tagToRemove}, ${mediaPath} (${startTime}s)`);
  }

  /**
   * 자막 요소에 태그 렌더링
   * @param {HTMLElement} subtitleElement - 자막 요소
   * @private
   */
  _renderTags(subtitleElement) {
    const mediaPath = subtitleElement.dataset.mediaPath;
    const startTime = subtitleElement.dataset.startTime;
    const key = this._getBookmarkKey(mediaPath, startTime);
    
    // 태그 목록 가져오기
    const tagList = this.tags.get(key) || [];
    
    // 태그 컨테이너 찾기 또는 생성
    let tagContainer = subtitleElement.querySelector('.tag-container');
    
    if (!tagContainer) {
      tagContainer = document.createElement('div');
      tagContainer.className = 'tag-container';
      
      // 자막 텍스트 다음에 추가
      const subtitleText = subtitleElement.querySelector('.subtitle-text-ko') || 
                           subtitleElement.querySelector('.subtitle-text-en');
      if (subtitleText) {
        subtitleText.after(tagContainer);
      } else {
        subtitleElement.appendChild(tagContainer);
      }
    }
    
    // 태그 HTML 생성
    if (tagList.length > 0) {
      tagContainer.innerHTML = tagList.map(tag => `
        <span class="tag-item" data-tag="${tag}">
          ${tag}
          <button class="tag-remove">×</button>
        </span>
      `).join('');
      tagContainer.style.display = 'flex';
    } else {
      tagContainer.innerHTML = '';
      tagContainer.style.display = 'none';
    }
  }

  /**
   * 서버에 북마크 저장
   * @param {string} mediaPath - 미디어 경로
   * @param {number} startTime - 시작 시간
   * @param {boolean} isBookmarked - 북마크 상태
   * @private
   */
  _saveBookmarkToServer(mediaPath, startTime, isBookmarked) {
    if (window.toggleBookmarkInDB) {
      window.toggleBookmarkInDB(mediaPath, startTime, isBookmarked)
        .catch(error => {
          this.debugLog(`북마크 저장 실패: ${error.message}`);
        });
    }
  }

  /**
   * 서버에 태그 저장
   * @param {string} mediaPath - 미디어 경로
   * @param {number} startTime - 시작 시간
   * @param {string} tag - 태그
   * @private
   */
  _saveTagToServer(mediaPath, startTime, tag) {
    if (window.addTagToDB) {
      window.addTagToDB(mediaPath, startTime, tag)
        .catch(error => {
          this.debugLog(`태그 저장 실패: ${error.message}`);
        });
    }
  }

  /**
   * 서버에서 태그 제거
   * @param {string} mediaPath - 미디어 경로
   * @param {number} startTime - 시작 시간
   * @param {string} tag - 태그
   * @private
   */
  _deleteTagFromServer(mediaPath, startTime, tag) {
    if (window.deleteTagFromDB) {
      window.deleteTagFromDB(mediaPath, startTime, tag)
        .catch(error => {
          this.debugLog(`태그 삭제 실패: ${error.message}`);
        });
    }
  }

  /**
   * 북마크 키 생성
   * @param {string} mediaPath - 미디어 경로
   * @param {number} startTime - 시작 시간
   * @returns {string} 북마크 키
   * @private
   */
  _getBookmarkKey(mediaPath, startTime) {
    return `${mediaPath}:${startTime}`;
  }

  /**
   * 북마크 로컬 저장
   * @private
   */
  _saveBookmarks() {
    try {
      localStorage.setItem('subtitle-bookmarks', JSON.stringify([...this.bookmarks]));
    } catch (error) {
      this.debugLog(`북마크 저장 실패: ${error.message}`);
    }
  }

  /**
   * 북마크 로드
   * @private
   */
  _loadBookmarks() {
    try {
      const savedBookmarks = localStorage.getItem('subtitle-bookmarks');
      if (savedBookmarks) {
        this.bookmarks = new Set(JSON.parse(savedBookmarks));
      }
    } catch (error) {
      this.debugLog(`북마크 로드 실패: ${error.message}`);
    }
  }

  /**
   * 디버그 로그 출력
   * @param {string} message - 로그 메시지
   */
  debugLog(message) {
    if (this.debugMode) {
      console.log(`[BookmarkManager] ${message}`);
    }
  }
} 