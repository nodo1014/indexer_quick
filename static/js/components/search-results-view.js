/**
 * SearchResultsView - 검색 결과 표시 모듈
 * 검색 결과를 가공하고 화면에 표시하는 기능을 담당합니다.
 */

export class SearchResultsView {
  constructor() {
    this.debugMode = true;
    this.resultsContainer = document.getElementById("search-results-list");
    this.subtitleResults = document.getElementById("subtitle-results");
    this.resultInfo = document.getElementById("current-result-info");
    this.cache = null; // 마지막 검색 결과 캐시
    
    this.debug("SearchResultsView 인스턴스 생성됨");
  }

  /**
   * 초기화 함수
   */
  init() {
    this.debug("SearchResultsView 초기화됨");
    return this;
  }

  /**
   * 검색 결과 표시
   * @param {Array} results - 검색 결과 배열
   */
  displayResults(results) {
    this.debug(`검색 결과 표시: ${results ? results.length : 0}개 항목`);
    this.cache = results; // 결과 캐시 저장

    // 결과가 없을 경우
    if (!results || results.length === 0) {
      if (this.subtitleResults) {
        this.subtitleResults.innerHTML = `
          <div class="text-center p-4 text-gray-500">
            <p>검색 결과가 없습니다.</p>
            <p class="text-xs mt-2">참고: 검색은 미디어가 있는 자막만을 대상으로 합니다.</p>
          </div>
        `;
      }
      
      if (this.resultsContainer) {
        this.resultsContainer.innerHTML = "";
      }
      
      // 결과 정보 표시 업데이트
      if (this.resultInfo) {
        this.resultInfo.textContent = "0개의 결과";
      }
      
      return;
    }

    // 검색 결과를 그룹화하여 표시
    try {
      // 결과 구조 로깅 - 디버깅을 위해 더 자세히 출력
      if (results[0]) {
        this.debug(`검색 결과 첫 번째 항목 구조:`);
        this.debug(JSON.stringify(results[0], null, 2));
      }
      
      let allSubtitles = [];
      
      // 검색 결과 구조 확인 및 처리
      if (results.length > 0) {
        // 경우 1: 각 항목이 미디어 파일이고 subtitles 배열을 포함하는 구조
        if (results[0].subtitles && Array.isArray(results[0].subtitles)) {
          this.debug('결과 구조 유형 1: 미디어 파일과 subtitles 배열');
          // 각 미디어 파일의 자막들을 하나의 배열로 변환
          results.forEach(mediaFile => {
            this.debug(`미디어 파일 처리: ${mediaFile.fileName || mediaFile.mediaPath}`);
            
            if (Array.isArray(mediaFile.subtitles)) {
              // 각 자막에 미디어 정보 추가
              const mediaSubtitles = mediaFile.subtitles.map(subtitle => ({
                ...subtitle,
                media_path: mediaFile.mediaPath || subtitle.mediaPath,
                streaming_url: mediaFile.streamingUrl || subtitle.streamingUrl,
                file_name: mediaFile.fileName || subtitle.fileName
              }));
              
              allSubtitles = allSubtitles.concat(mediaSubtitles);
            }
          });
        } 
        // 경우 2: 각 항목이 자막 자체인 구조
        else if (results[0].content || results[0].en || results[0].startTime || results[0].start_time) {
          this.debug('결과 구조 유형 2: 자막 배열');
          allSubtitles = results.map(subtitle => {
            // 미디어 경로가 없는 경우 처리
            const media_path = subtitle.mediaPath || subtitle.media_path || '';
            if (!media_path) {
              this.debug(`미디어 경로가 없는 자막 발견: ${subtitle.content || subtitle.en}`);
            }
            
            return {
              ...subtitle,
              media_path: media_path,
              streaming_url: subtitle.streamingUrl || subtitle.streaming_url || `/api/media/${encodeURIComponent(media_path)}`,
              file_name: subtitle.fileName || subtitle.file_name || (media_path ? media_path.split('/').pop() : '알 수 없는 파일')
            };
          });
          
          // 미디어 경로가 있는 자막만 필터링 (중요: 검색은 미디어가 있는 자막만을 대상으로 함)
          const filteredSubtitles = allSubtitles.filter(subtitle => subtitle.media_path && subtitle.media_path.trim() !== '');
          
          if (filteredSubtitles.length < allSubtitles.length) {
            this.debug(`미디어가 없는 자막 ${allSubtitles.length - filteredSubtitles.length}개 필터링됨`);
          }
          
          allSubtitles = filteredSubtitles;
        }
        // 경우 3: API 응답이 results 배열이 아닌 results.items 배열을 사용하는 경우
        else if (results[0].items && Array.isArray(results[0].items)) {
          this.debug('결과 구조 유형 3: items 배열을 포함한 객체');
          // items 배열을 처리
          results.forEach(result => {
            if (Array.isArray(result.items)) {
              const processedItems = result.items.map(item => ({
                ...item,
                media_path: item.mediaPath || item.media_path || result.mediaPath || '',
                streaming_url: item.streamingUrl || item.streaming_url || result.streamingUrl || '',
                file_name: item.fileName || item.file_name || result.fileName || ''
              }));
              
              allSubtitles = allSubtitles.concat(processedItems);
            }
          });
        }
      }
      
      this.debug(`처리된 총 자막 수: ${allSubtitles.length}`);
      
      if (this.subtitleResults) {
        // 새로운 형식: subtitle-pair 요소 생성
        const subtitlesHtml = allSubtitles.map((subtitle, index) => {
          // 북마크 상태 확인
          const isBookmarked = subtitle.is_bookmarked ? 'bookmarked' : '';
          
          // 미디어 경로와 시간 정보 가져오기 (다양한 가능한 속성명 지원)
          const mediaPath = subtitle.media_path || subtitle.mediaPath || '';
          const streamingUrl = subtitle.streaming_url || subtitle.streamingUrl || 
                              `/api/media/${encodeURIComponent(mediaPath)}`;
          
          // 시간 값을 초 단위로 표준화 (API 응답은 밀리초일 수 있음)
          let startTime = subtitle.startTime || subtitle.start_time || 0;
          let endTime = subtitle.endTime || subtitle.end_time || 0;
          
          // 밀리초를 초 단위로 변환 (1000보다 크면 밀리초로 가정)
          if (startTime > 1000) startTime = startTime / 1000;
          if (endTime > 1000) endTime = endTime / 1000;
          
          if (endTime <= startTime) {
            endTime = startTime + 5; // 기본 5초 지속
          }
          
          // 시간 포맷팅
          const formattedTime = subtitle.time || this.formatTime(startTime);
          
          // 한국어 자막이 있는 경우 함께 표시
          const englishText = subtitle.en || subtitle.content || '';
          const koreanText = subtitle.ko || '';
          
          // 태그 정보 가져오기
          const tags = subtitle.tags || [];
          const tagsHtml = tags.length > 0 
            ? `<div class="tags-container mt-1">
                ${tags.map(tag => `<span class="tag px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded">${tag}</span>`).join(' ')}
               </div>` 
            : '';
              
          this.debug(`[${index}] 자막 항목 생성: ${englishText.substring(0, 30)}...`);

          return `
            <div class="subtitle-pair ${isBookmarked} mb-3 p-3 rounded bg-white border border-gray-200 hover:bg-blue-50 cursor-pointer relative" 
                 data-media-path="${mediaPath}"
                 data-start-time="${startTime}"
                 data-end-time="${endTime}"
                 data-streaming-url="${streamingUrl}">
              <div class="flex items-start mb-1 justify-between">
                <div class="flex-grow">
                  <div class="subtitle-text-en text-gray-900">${englishText}</div>
                  <div class="subtitle-text-ko text-blue-600 mt-1">${koreanText}</div>
                  ${tagsHtml}
                </div>
                <div class="ml-2 flex-shrink-0 bookmark-container">
                  <button class="bookmark-btn ${isBookmarked ? 'active' : ''}" data-media-path="${mediaPath}" data-start-time="${startTime}">
                    ${isBookmarked ? '★' : '☆'}
                  </button>
                  <button class="tag-btn ml-1 text-gray-400 hover:text-blue-500" data-media-path="${mediaPath}" data-start-time="${startTime}" title="태그 추가">
                    🏷️
                  </button>
                </div>
              </div>
              <div class="text-xs text-gray-500 flex justify-between items-center">
                <div class="subtitle-time">${formattedTime}</div>
                <div class="subtitle-source">${subtitle.file_name || mediaPath.split('/').pop()}</div>
              </div>
            </div>
          `;
        }).join('');

        this.subtitleResults.innerHTML = subtitlesHtml;
        
        // 현재 결과 정보 표시
        if (this.resultInfo) {
          this.resultInfo.textContent = `${allSubtitles.length}개의 결과`;
        }
        
        // 결과 표시 후 이벤트 핸들러 등록 완료 이벤트 발생
        this._emitResultsRendered();
      } else {
        console.error("subtitle-results 요소를 찾을 수 없습니다.");
      }
    } catch (error) {
      console.error("검색 결과 표시 중 오류 발생:", error);
      if (this.subtitleResults) {
        this.subtitleResults.innerHTML = `
          <div class="text-center p-4 text-red-500">
            <p>검색 결과 처리 중 오류가 발생했습니다: ${error.message}</p>
          </div>
        `;
      }
    }
  }

  /**
   * 검색 UI를 로딩 상태로 업데이트
   * @param {boolean} isLoading - 로딩 상태 여부
   */
  updateUIForLoading(isLoading) {
    // 검색 폼과 결과 영역 비활성화
    this.disableSearchForm(isLoading);
    
    // 결과 영역에 로딩 표시
    if (isLoading && this.subtitleResults) {
      this.subtitleResults.innerHTML = `
        <div class="text-center p-4">
          <div class="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500"></div>
          <p class="mt-2 text-gray-600">검색 중...</p>
        </div>
      `;
    }
  }

  /**
   * 검색 폼 비활성화/활성화
   * @param {boolean} disable - 비활성화 여부
   */
  disableSearchForm(disable) {
    const searchForm = document.getElementById("search-form");
    if (!searchForm) return;
    
    const inputs = searchForm.querySelectorAll("input, select, button");
    inputs.forEach(input => {
      input.disabled = disable;
    });
  }
  
  /**
   * 오류 메시지 표시
   * @param {string} errorMessage - 표시할 오류 메시지
   */
  displayError(errorMessage) {
    this.debug(`오류 표시: ${errorMessage}`);
    
    if (this.subtitleResults) {
      this.subtitleResults.innerHTML = `
        <div class="text-center p-4 text-red-500">
          <p>오류가 발생했습니다: ${errorMessage}</p>
        </div>
      `;
    }
    
    // 결과 정보 표시 업데이트
    if (this.resultInfo) {
      this.resultInfo.textContent = '오류 발생';
    }
    
    // 검색 폼 활성화
    this.disableSearchForm(false);
  }

  /**
   * 오류 메시지 표시
   * @param {string} message - 오류 메시지
   */
  displayError(message) {
    this.debug(`오류 표시: ${message}`);
    
    if (this.subtitleResults) {
      this.subtitleResults.innerHTML = `
        <div class="text-center p-4 text-red-500">
          <p>${message}</p>
        </div>
      `;
    }
    
    // 검색 폼 활성화
    this.disableSearchForm(false);
  }

  /**
   * 시간(초) 포맷 변환 (초 -> 시:분:초)
   * @param {number} seconds - 초 단위 시간
   * @returns {string} 포맷된 시간 문자열
   */
  formatTime(seconds) {
    if (seconds === undefined || seconds === null) return "00:00";

    // 문자열이면 숫자로 변환
    seconds = parseFloat(seconds);
    
    if (isNaN(seconds)) return "00:00";
    
    // 밀리초로 표현된 경우 초로 변환
    if (seconds > 1000) {
      seconds = seconds / 1000;
    }

    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    
    // 두 자리 숫자로 패딩
    const pad = (n) => (n < 10 ? "0" + n : n);
    
    if (h > 0) {
      return `${pad(h)}:${pad(m)}:${pad(s)}`;
    } else {
      return `${pad(m)}:${pad(s)}`;
    }
  }

  /**
   * 결과 렌더링 완료 이벤트 발생
   * @private
   */
  _emitResultsRendered() {
    // 커스텀 이벤트 발생
    const event = new CustomEvent('searchResultsRendered', { 
      detail: { resultsCount: this.cache ? this.cache.length : 0 } 
    });
    document.dispatchEvent(event);
    this.debug('searchResultsRendered 이벤트 발생');
  }

  /**
   * 디버그 로그 출력
   * @param {string} message - 로그 메시지
   */
  debug(message) {
    if (this.debugMode) {
      console.log(`[SearchResultsView] ${message}`);
    }
  }
} 