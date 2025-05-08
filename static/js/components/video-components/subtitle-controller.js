/**
 * SubtitleController
 * 비디오 플레이어의 자막 관련 기능을 담당하는 클래스
 * - 자막 표시 및 제어
 * - 자막 하이라이트 처리
 * - 자막 검색 결과 관리
 */

export class SubtitleController {
  constructor(player) {
    this.player = player;
    this.currentSubtitleElement = null;
    this.debugMode = true;

    // 데이터 속성 매핑 (API 응답 필드명 차이 대응)
    this.dataAttributes = {
      mediaPath: ['mediaPath', 'media_path'],
      streamingUrl: ['streamingUrl', 'streaming_url'],
      startTime: ['startTime', 'start_time'],
      endTime: ['endTime', 'end_time']
    };
  }

  /**
   * 초기화 메서드
   */
  init() {
    this.setupSubtitleClickHandlers();
    this.debugLog("SubtitleController 초기화 완료");
  }

  /**
   * 자막 클릭 핸들러 설정
   */
  setupSubtitleClickHandlers() {
    // 이전 핸들러 제거
    document.removeEventListener('click', this._handleSubtitleClick);
    
    // 새 핸들러 등록
    this._handleSubtitleClick = this._handleSubtitleClick.bind(this);
    document.addEventListener('click', this._handleSubtitleClick);

    this.debugLog("자막 클릭 핸들러 설정 완료");
  }

  /**
   * 자막 클릭 이벤트 핸들러
   * @param {Event} event - 클릭 이벤트
   * @private
   */
  _handleSubtitleClick(event) {
    // 클릭된 요소 또는 부모 중에 subtitle-pair 클래스를 가진 요소 찾기
    const subtitleElement = event.target.closest('.subtitle-pair');
    if (subtitleElement) {
      console.log('자막 요소 클릭됨:', subtitleElement);
      
      // 버튼 클릭인 경우 이벤트 처리하지 않음 (북마크, 태그 버튼 등)
      if (event.target.tagName === 'BUTTON' || 
          event.target.closest('button') || 
          event.target.tagName === 'A' || 
          event.target.closest('a')) {
        console.log('버튼 클릭은 무시됨');
        return;
      }
      
      // 자막 요소 재생
      this.playSingleSubtitle(subtitleElement);
    }
  }

  /**
   * 단일 자막 재생
   * @param {HTMLElement} subtitleElement - 재생할 자막 요소
   */
  playSingleSubtitle(subtitleElement) {
    if (!subtitleElement) {
      console.error("자막 요소가 없습니다.");
      return;
    }
    
    if (!this.player) {
      console.error("플레이어가 초기화되지 않았습니다.");
      return;
    }

    try {
      // 자막 정보 추출
      const mediaData = this._extractMediaDataFromElement(subtitleElement);
      console.log('추출된 자막 데이터:', mediaData);
      
      if (!mediaData.mediaPath || !mediaData.streamingUrl) {
        console.error("필수 미디어 정보가 없는 자막 요소:", subtitleElement);
        return;
      }

      // 현재 자막 요소 업데이트
      this.currentSubtitleElement = subtitleElement;

      // 자막 하이라이트 및 현재 표시 업데이트
      this.highlightCurrentSubtitle(subtitleElement);
      this.updateCurrentSubtitleDisplay(subtitleElement);

      // 현재 재생 중인 미디어와 다른 경우 새 소스 설정
      if (this.player.vjsPlayer && this.player.vjsPlayer.src() !== mediaData.streamingUrl) {
        console.log('새 미디어 소스 설정:', mediaData.streamingUrl);
        this.player.setSource(mediaData.streamingUrl);
        
        // 미디어 로드 후 특정 시간으로 이동하여 재생
        const playWhenReady = () => {
          this.player.vjsPlayer.off('loadedmetadata', playWhenReady);
          console.log('미디어 로드 완료, 재생 시작:', mediaData.startTime, mediaData.endTime);
          this.player.playSegment(mediaData.startTime, mediaData.endTime);
        };
        
        this.player.vjsPlayer.one('loadedmetadata', playWhenReady);
      } else {
        // 같은 미디어이면 바로 재생
        console.log('같은 미디어, 세그먼트 바로 재생:', mediaData.startTime, mediaData.endTime);
        this.player.playSegment(mediaData.startTime, mediaData.endTime);
      }
    } catch (error) {
      console.error("자막 재생 중 오류 발생:", error);
    }
  }

  /**
   * 자막 요소에서 미디어 데이터 추출
   * @param {HTMLElement} element - 자막 요소
   * @returns {Object} 미디어 데이터 객체
   * @private
   */
  _extractMediaDataFromElement(element) {
    const result = {};
    
    // 데이터 속성 매핑에 따라 각 속성 추출
    for (const [key, attrNames] of Object.entries(this.dataAttributes)) {
      // 여러 가능한 속성명 시도
      for (const attrName of attrNames) {
        const value = element.dataset[attrName];
        if (value !== undefined) {
          // 시간 값은 숫자로 변환
          if (key === 'startTime' || key === 'endTime') {
            result[key] = parseFloat(value);
          } else {
            result[key] = value;
          }
          break; // 첫 번째 매칭되는 속성 사용
        }
      }
    }
    
    // streamingUrl이 없으면 mediaPath로부터 생성
    if (!result.streamingUrl && result.mediaPath) {
      result.streamingUrl = `/api/media/${encodeURIComponent(result.mediaPath)}`;
    }
    
    // endTime이 없으면 startTime + 5초로 설정
    if (result.startTime !== undefined && result.endTime === undefined) {
      result.endTime = result.startTime + 5;
    }
    
    return result;
  }

  /**
   * 다음 또는 이전 자막으로 이동
   * @param {number} direction - 이동 방향 (1: 다음, -1: 이전)
   * @returns {boolean} 성공 여부
   */
  jumpToSubtitle(direction) {
    // 방향 값 검증
    if (direction !== 1 && direction !== -1) return false;

    // 현재 재생 중인 자막이 없는 경우
    if (!this.currentSubtitleElement) {
      // 검색 결과에서 첫 번째 자막 선택
      const firstSubtitle = document.querySelector('.subtitle-pair');
      if (firstSubtitle) {
        this.playSingleSubtitle(firstSubtitle);
        return true;
      }
      return false;
    }

    // 모든 자막 요소 배열
    const allSubtitles = Array.from(document.querySelectorAll('.subtitle-pair'));
    
    // 현재 자막의 인덱스 찾기
    const currentIndex = allSubtitles.indexOf(this.currentSubtitleElement);
    if (currentIndex === -1) return false;

    // 다음 또는 이전 인덱스 계산
    const nextIndex = currentIndex + direction;
    
    // 인덱스 범위 확인
    if (nextIndex < 0 || nextIndex >= allSubtitles.length) return false;

    // 새 자막 재생
    this.playSingleSubtitle(allSubtitles[nextIndex]);
    return true;
  }

  /**
   * 현재 자막 강조 표시
   * @param {HTMLElement} subtitleElement - 강조할 자막 요소
   */
  highlightCurrentSubtitle(subtitleElement) {
    // 기존 강조 표시 제거
    document.querySelectorAll('.subtitle-pair.playing').forEach(el => {
      el.classList.remove('playing');
    });

    // 새 자막 강조 표시
    if (subtitleElement) {
      subtitleElement.classList.add('playing');
      
      // 뷰포트에 보이도록 스크롤
      subtitleElement.scrollIntoView({
        behavior: 'smooth',
        block: 'center'
      });
    }
  }

  /**
   * 현재 자막 표시 업데이트
   * @param {HTMLElement} subtitleElement - 표시할 자막 요소
   */
  updateCurrentSubtitleDisplay(subtitleElement) {
    if (!subtitleElement) {
      this.clearCurrentSubtitleDisplay();
      return;
    }

    // 현재 자막 표시 영역 요소
    const currentSubtitleEn = document.getElementById('current-subtitle-en');
    const currentSubtitleKo = document.getElementById('current-subtitle-ko');
    
    if (!currentSubtitleEn && !currentSubtitleKo) {
      console.log("현재 자막 표시 영역을 찾을 수 없습니다.");
      return;
    }

    try {
      // 자막 텍스트 가져오기
      const englishText = subtitleElement.querySelector('.subtitle-text-en')?.textContent || '';
      const koreanText = subtitleElement.querySelector('.subtitle-text-ko')?.textContent || '';

      // 자막 표시 업데이트
      if (currentSubtitleEn) currentSubtitleEn.textContent = englishText;
      if (currentSubtitleKo) currentSubtitleKo.textContent = koreanText;
      
      this.debugLog(`현재 자막 업데이트: ${englishText.substring(0, 30)}...`);
    } catch (error) {
      console.error("자막 표시 업데이트 오류:", error);
    }
  }

  /**
   * 현재 자막 표시 초기화
   */
  clearCurrentSubtitleDisplay() {
    const currentSubtitleEn = document.getElementById('current-subtitle-en');
    const currentSubtitleKo = document.getElementById('current-subtitle-ko');
    
    if (currentSubtitleEn) currentSubtitleEn.textContent = '';
    if (currentSubtitleKo) currentSubtitleKo.textContent = '';
  }

  /**
   * 현재 재생 시간에 따라 자막 하이라이트 업데이트
   */
  updateHighlightByCurrentTime() {
    if (!this.player || !this.player.vjsPlayer) return;
    
    try {
      const currentTime = this.player.getCurrentTime();
      const currentSrc = this.player.vjsPlayer.src();
      
      if (!currentSrc) return;
      
      // 모든 자막 요소 확인
      const allSubtitles = document.querySelectorAll('.subtitle-pair');
      let activeSubtitle = null;
      
      // 현재 시간에 해당하는 자막 찾기
      for (const subtitle of allSubtitles) {
        const mediaData = this._extractMediaDataFromElement(subtitle);
        
        // 현재 재생 중인 미디어와 일치하는지 확인 (streamingUrl 기준)
        const matchesPath = currentSrc === mediaData.streamingUrl || 
                           currentSrc.includes(encodeURIComponent(mediaData.mediaPath));
        
        if (matchesPath && 
            currentTime >= mediaData.startTime && 
            currentTime <= mediaData.endTime) {
          activeSubtitle = subtitle;
          break;
        }
      }
      
      // 현재 활성 자막이 변경되었으면 하이라이트 및 표시 업데이트
      if (activeSubtitle && this.currentSubtitleElement !== activeSubtitle) {
        this.currentSubtitleElement = activeSubtitle;
        this.highlightCurrentSubtitle(activeSubtitle);
        this.updateCurrentSubtitleDisplay(activeSubtitle);
      }
    } catch (error) {
      console.error("자막 하이라이트 업데이트 오류:", error);
    }
  }

  /**
   * 디버그 로그 출력
   * @param {string} message - 로그 메시지
   */
  debugLog(message) {
    if (this.debugMode) {
      console.log(`[SubtitleController] ${message}`);
    }
  }
} 