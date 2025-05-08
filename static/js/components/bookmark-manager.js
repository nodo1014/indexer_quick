/**
 * BookmarkManager - 자막 북마크 관리 모듈
 * 자막 북마크 기능과 관련된 UI 및 기능을 관리합니다.
 */

export class BookmarkManager {
  constructor() {
    this.debugMode = true;
    this.currentFilter = false; // false: 모든 항목 표시, true: 북마크된 항목만 표시
    this.debug("BookmarkManager 인스턴스 생성됨");
  }

  /**
   * 초기화 함수
   */
  init() {
    this.debug("BookmarkManager 초기화됨");
    this.setupBookmarkToggle();
    return this;
  }

  /**
   * 페이지 내 북마크 버튼에 이벤트 핸들러 설정
   */
  setupBookmarkButtons() {
    const bookmarkButtons = document.querySelectorAll(".bookmark-btn");
    this.debug(`북마크 버튼 설정: ${bookmarkButtons.length}개 발견`);

    bookmarkButtons.forEach((button) => {
      button.addEventListener("click", async (e) => {
        e.stopPropagation(); // 자막 클릭 이벤트 전파 방지

        const subtitleElement = button.closest(".subtitle-pair");
        if (!subtitleElement) return;

        const mediaPath = subtitleElement.dataset.mediaPath;
        const startTime = subtitleElement.dataset.startTime;
        const isCurrentlyBookmarked = button.textContent.trim() === "★";

        try {
          // 북마크 상태 토글
          const success = await window.bookmarkToDB(
            mediaPath, 
            startTime, 
            !isCurrentlyBookmarked
          );

          if (success) {
            // UI 업데이트
            button.textContent = isCurrentlyBookmarked ? "☆" : "★";
            button.classList.toggle("active");
            
            // 자막 요소에 북마크 클래스 토글
            if (isCurrentlyBookmarked) {
              subtitleElement.classList.remove("bookmarked");
            } else {
              subtitleElement.classList.add("bookmarked");
            }

            this.debug(`북마크 ${isCurrentlyBookmarked ? '제거' : '추가'}: ${mediaPath} - ${startTime}`);
            
            // 북마크 필터가 활성화된 경우, 표시 상태 업데이트
            if (this.currentFilter) {
              this.toggleBookmarkedView(true);
            } else {
              // 결과 카운트만 업데이트
              this.updateDisplayedResultCount();
            }
          }
        } catch (error) {
          console.error("북마크 오류:", error);
        }
      });
    });
  }

  /**
   * 북마크 필터 토글 버튼 이벤트 설정
   */
  setupBookmarkToggle() {
    // 버튼 모양의 북마크 필터 토글
    const bookmarkFilterBtn = document.getElementById('bookmark-filter-btn');
    if (bookmarkFilterBtn) {
      bookmarkFilterBtn.addEventListener('click', () => {
        this.currentFilter = !this.currentFilter;
        this.toggleBookmarkedView(this.currentFilter);
        
        // 버튼 상태 변경
        if (this.currentFilter) {
          bookmarkFilterBtn.textContent = "모두 보기";
          bookmarkFilterBtn.classList.add('active');
        } else {
          bookmarkFilterBtn.textContent = "북마크만 보기";
          bookmarkFilterBtn.classList.remove('active');
        }
      });
    } else {
      this.debug("북마크 필터 버튼을 찾을 수 없습니다.");
    }
  }

  /**
   * 북마크 표시 전환
   * @param {boolean} showBookmarkedOnly - true인 경우 북마크된 항목만 표시
   */
  toggleBookmarkedView(showBookmarkedOnly) {
    const subtitleItems = document.querySelectorAll('.subtitle-pair');
    this.debug(`북마크 필터 변경: ${showBookmarkedOnly ? '북마크만' : '전체'} 표시 (${subtitleItems.length}개 항목)`);
    
    subtitleItems.forEach(item => {
      if (showBookmarkedOnly) {
        // 북마크된 항목만 표시
        item.style.display = item.classList.contains('bookmarked') ? '' : 'none';
      } else {
        // 모든 항목 표시
        item.style.display = '';
      }
    });
    
    // 현재 표시된 결과 수 업데이트
    this.updateDisplayedResultCount();
    
    // 현재 필터 상태 저장
    this.currentFilter = showBookmarkedOnly;
  }

  /**
   * 표시된 결과 수 업데이트
   */
  updateDisplayedResultCount() {
    const resultInfo = document.getElementById("current-result-info");
    if (!resultInfo) return;
    
    const visibleItems = document.querySelectorAll('.subtitle-pair:not([style*="display: none"])').length;
    const totalItems = document.querySelectorAll('.subtitle-pair').length;
    
    if (visibleItems < totalItems) {
      resultInfo.textContent = `${visibleItems}/${totalItems}개의 결과 표시됨`;
    } else {
      resultInfo.textContent = `${totalItems}개의 결과`;
    }
  }

  /**
   * 디버그 로그 출력
   * @param {string} message - 로그 메시지
   */
  debug(message) {
    if (this.debugMode) {
      console.log(`[BookmarkManager] ${message}`);
    }
  }
} 