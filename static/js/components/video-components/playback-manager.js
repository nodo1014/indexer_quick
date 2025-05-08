/**
 * PlaybackManager
 * 비디오 플레이어의 재생 관련 기능을 담당하는 클래스
 * - 재생 모드 관리 (검색 결과, 순차 재생, 랜덤, 반복)
 * - 자막 반복 재생
 * - 비디오 간 이동
 */

export class PlaybackManager {
  constructor(player) {
    this.player = player;
    this.playbackMode = "search-results"; // 기본 모드: 검색 결과만 재생
    this.isRepeating = false;
    this.repeatHandler = null;
    this.repeatCount = 0;
    this.maxRepeatCount = 2;
    this.currentSubtitleIndex = -1;
    this.debugMode = true;
    this.searchResultsPlaybackPause = 1500; // 검색 결과 연속 재생 시 대기 시간(ms)
    this.continuousPlaybackTimer = null;
  }

  /**
   * 초기화 메서드
   */
  init() {
    // 반복 횟수 설정 UI 연결
    this._connectRepeatCountControl();
    this.debugLog("PlaybackManager 초기화 완료");
  }

  /**
   * 반복 횟수 입력 연결
   * @private
   */
  _connectRepeatCountControl() {
    const repeatCountInput = document.getElementById('repeat-count');
    if (repeatCountInput) {
      // 초기 값 설정
      this.maxRepeatCount = parseInt(repeatCountInput.value) || 2;
      
      // 변경 이벤트 리스너
      repeatCountInput.addEventListener('change', () => {
        const newValue = parseInt(repeatCountInput.value) || 2;
        this.maxRepeatCount = Math.max(1, Math.min(10, newValue));
        repeatCountInput.value = this.maxRepeatCount;
        this.debugLog(`반복 횟수 설정: ${this.maxRepeatCount}`);
      });
    }
  }

  /**
   * 재생 모드 설정
   * @param {string} mode - 재생 모드 ('search-results', 'sequential', 'random', 'repeat-one')
   */
  setPlaybackMode(mode) {
    // 유효한 모드인지 확인
    const validModes = ['search-results', 'sequential', 'random', 'repeat-one'];
    if (!validModes.includes(mode)) {
      this.debugLog(`유효하지 않은 재생 모드: ${mode}`);
      return;
    }

    // 반복 재생 중이면 중지
    if (this.isRepeating) {
      this.stopRepeat();
    }

    this.playbackMode = mode;
    this.debugLog(`재생 모드 설정: ${mode}`);
  }

  /**
   * 비디오 종료 이벤트 핸들러
   */
  handleVideoEnded() {
    if (this.playbackMode === 'sequential' || this.playbackMode === 'random') {
      this.playNextVideo();
    }
  }

  /**
   * 세그먼트 재생 완료 이벤트 핸들러
   */
  onSegmentEnded() {
    console.log("세그먼트 재생 완료. 모드:", this.playbackMode, "반복:", this.isRepeating);
    
    // 반복 모드인 경우
    if (this.isRepeating) {
      this.handleRepeat();
      return;
    }
    
    // 재생 모드에 따른 처리
    switch (this.playbackMode) {
      case 'search-results':
        // 검색 결과 순서대로 재생
        this.playNextSearchResult();
        break;
        
      case 'sequential':
        // 다음 자막으로 이동
        this.jumpToSubtitle(1);
        break;
        
      case 'random':
        // 랜덤한 자막 재생 (아직 구현 안됨)
        this.playRandomSubtitle();
        break;
        
      case 'repeat-one':
        // 현재 자막 반복
        if (this.player.subtitleController.currentSubtitleElement) {
          this.player.subtitleController.playSingleSubtitle(
            this.player.subtitleController.currentSubtitleElement
          );
        }
        break;
        
      default:
        // 아무 동작 안함 (자동 재생 중단)
        break;
    }
  }

  /**
   * 반복 재생 처리
   */
  handleRepeat() {
    if (!this.player || !this.player.subtitleController) return;
    
    // 현재 반복 횟수 증가
    this.currentRepeatCount++;
    
    // 반복 횟수 표시 업데이트
    const statusElement = document.getElementById('playback-status');
    if (statusElement) {
      statusElement.textContent = `${this.currentRepeatCount}/${this.maxRepeatCount}회 반복 중`;
      statusElement.classList.remove('hidden');
    }
    
    // 최대 반복 횟수에 도달했는지 확인
    if (this.currentRepeatCount >= this.maxRepeatCount) {
      console.log("최대 반복 횟수에 도달함:", this.maxRepeatCount);
      
      // 반복 종료
      this.isRepeating = false;
      
      // 상태 표시 숨김
      if (statusElement) {
        statusElement.classList.add('hidden');
      }
      
      // 다음 재생 모드에 따라 처리
      switch (this.playbackMode) {
        case 'search-results':
          this.playNextSearchResult();
          break;
        case 'sequential':
          this.jumpToSubtitle(1);
          break;
        default:
          break;
      }
      
      return;
    }
    
    // 현재 자막 다시 재생
    const currentElement = this.player.subtitleController.currentSubtitleElement;
    if (currentElement) {
      this.player.subtitleController.playSingleSubtitle(currentElement);
    }
  }

  /**
   * 검색 결과에서 다음 자막 재생
   */
  playNextSearchResult() {
    this.jumpToSubtitle(1);
  }

  /**
   * 랜덤 자막 재생 (미구현)
   */
  playRandomSubtitle() {
    const allSubtitles = document.querySelectorAll('.subtitle-pair');
    if (allSubtitles.length === 0) return;
    
    const randomIndex = Math.floor(Math.random() * allSubtitles.length);
    const randomSubtitle = allSubtitles[randomIndex];
    
    if (randomSubtitle && this.player.subtitleController) {
      this.player.subtitleController.playSingleSubtitle(randomSubtitle);
    }
  }

  /**
   * 재생 상태 메시지 업데이트
   * @param {string} message - 표시할 메시지
   */
  updatePlaybackStatus(message) {
    const statusElement = document.getElementById('playback-status');
    if (statusElement) {
      statusElement.textContent = message;
      
      // 메시지가 있으면 표시, 없으면 숨김
      if (message) {
        statusElement.classList.remove('hidden');
      } else {
        statusElement.classList.add('hidden');
      }
    }
  }

  /**
   * 순차 재생 (다음 자막)
   */
  playSequential() {
    // 단순히 다음 자막으로 이동
    this.player.subtitleController.jumpToSubtitle(1);
  }

  /**
   * 랜덤 재생
   */
  playRandom() {
    // 모든 자막 요소 가져오기
    const allSubtitles = document.querySelectorAll('.subtitle-pair');
    if (allSubtitles.length === 0) {
      this.debugLog("재생할 자막이 없음");
      return;
    }
    
    // 랜덤 인덱스 생성
    const randomIndex = Math.floor(Math.random() * allSubtitles.length);
    
    // 랜덤 자막 재생
    this.player.subtitleController.playSingleSubtitle(allSubtitles[randomIndex]);
  }

  /**
   * 반복 재생 토글
   */
  toggleRepeat() {
    if (this.isRepeating) {
      this.stopRepeat();
    } else {
      this.startRepeat();
    }
  }

  /**
   * 반복 재생 시작
   */
  startRepeat() {
    // 이미 반복 중이면 중지
    if (this.isRepeating) return;
    
    // 현재 자막이 없으면 반복 불가
    const currentSubtitle = document.querySelector('.subtitle-pair.playing');
    if (!currentSubtitle) {
      this.debugLog("반복할 자막이 없음");
      return;
    }
    
    // 반복 상태 설정
    this.isRepeating = true;
    this.repeatCount = 0;
    
    // 반복 버튼 UI 업데이트
    const repeatButton = document.getElementById('repeat-line-btn');
    if (repeatButton) {
      repeatButton.classList.add('active');
      repeatButton.setAttribute('title', '반복 중지');
    }
    
    // 현재 자막 재시작
    this.player.subtitleController.playSingleSubtitle(currentSubtitle);
    
    this.debugLog(`문장 반복 시작 (최대 ${this.maxRepeatCount}회)`);
  }

  /**
   * 반복 재생 중지
   */
  stopRepeat() {
    if (!this.isRepeating) return;
    
    this.isRepeating = false;
    this.repeatCount = 0;
    
    // 반복 버튼 UI 업데이트
    const repeatButton = document.getElementById('repeat-line-btn');
    if (repeatButton) {
      repeatButton.classList.remove('active');
      repeatButton.setAttribute('title', '문장 반복');
    }
    
    this.debugLog("문장 반복 중지");
  }

  /**
   * 다음 또는 이전 자막으로 이동
   * @param {number} direction - 이동 방향 (1: 다음, -1: 이전)
   */
  jumpToSubtitle(direction) {
    // 반복 재생 중이면 중지
    if (this.isRepeating) {
      this.stopRepeat();
    }
    
    // SubtitleController에 위임
    this.player.subtitleController.jumpToSubtitle(direction);
  }

  /**
   * 인접한 비디오로 이동
   * @param {number} direction - 이동 방향 (1: 다음, -1: 이전)
   */
  navigateToAdjacentVideo(direction) {
    // 방향 검증
    if (direction !== 1 && direction !== -1) return;
    
    if (!this.player.vjsPlayer) {
      this.debugLog("비디오 플레이어가 초기화되지 않음");
      return;
    }
    
    // 현재 재생 중인 미디어 URL 가져오기
    const currentSrc = this.player.vjsPlayer.src();
    if (!currentSrc) {
      this.debugLog("현재 재생 중인 미디어가 없음");
      return;
    }
    
    // URL에서 미디어 경로 추출
    const match = currentSrc.match(/\/media\/(.+)$/);
    if (!match) {
      this.debugLog("미디어 경로를 추출할 수 없음");
      return;
    }
    
    const currentMediaPath = decodeURIComponent(match[1]);
    
    // 같은 미디어 파일을 가진 자막 요소 찾기
    const allSubtitles = Array.from(document.querySelectorAll('.subtitle-pair'));
    
    // 미디어 파일 그룹화
    const mediaGroups = {};
    allSubtitles.forEach(el => {
      const mediaPath = el.dataset.mediaPath;
      if (!mediaGroups[mediaPath]) {
        mediaGroups[mediaPath] = [];
      }
      mediaGroups[mediaPath].push(el);
    });
    
    // 미디어 파일 목록
    const mediaFiles = Object.keys(mediaGroups);
    const currentIndex = mediaFiles.indexOf(currentMediaPath);
    
    if (currentIndex === -1) {
      this.debugLog("현재 미디어를 목록에서 찾을 수 없음");
      return;
    }
    
    // 다음/이전 인덱스 계산
    let nextIndex = currentIndex + direction;
    
    // 인덱스 범위 확인
    if (nextIndex < 0) nextIndex = 0;
    if (nextIndex >= mediaFiles.length) nextIndex = mediaFiles.length - 1;
    
    // 인덱스가 변경되지 않았으면 건너뛰기
    if (nextIndex === currentIndex) return;
    
    // 다음/이전 미디어 파일의 첫 번째 자막 재생
    const nextMediaPath = mediaFiles[nextIndex];
    const nextMediaElements = mediaGroups[nextMediaPath];
    
    if (nextMediaElements && nextMediaElements.length > 0) {
      this.player.subtitleController.playSingleSubtitle(nextMediaElements[0]);
    }
  }

  /**
   * 디버그 로그 출력
   * @param {string} message - 로그 메시지
   */
  debugLog(message) {
    if (this.debugMode) {
      console.log(`[PlaybackManager] ${message}`);
    }
  }
} 