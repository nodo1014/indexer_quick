/**
 * VideoPlayerCore
 * 비디오 플레이어의 핵심 기능을 담당하는 클래스
 * - 비디오 요소 제어
 * - 기본 이벤트 핸들링
 * - 미디어 로드 및 재생 관리
 */

class VideoPlayerCore {
  constructor() {
    this.video = document.getElementById("media-player");
    if (!this.video) {
      console.error("비디오 요소를 찾을 수 없습니다.");
      return;
    }

    // 기본 상태 변수
    this.isMediaLoading = false;  // 미디어 로딩 상태
    this.hasAudioTrack = true;    // 오디오 트랙 존재 여부
    this.debugMode = true;        // 디버그 모드 여부

    // 비디오 속성 기본 설정
    this._setupVideoProperties();
    
    // 오디오 설정 복원
    this._restoreAudioSettings();
    
    // 디버그 로그
    this.debugLog("VideoPlayerCore 인스턴스 생성됨");
  }

  /**
   * 비디오 요소의 기본 속성 설정
   * @private
   */
  _setupVideoProperties() {
    if (!this.video) return;
    
    this.video.crossOrigin = "anonymous";  // CORS 이슈 방지
    this.video.playsInline = true;         // 모바일 인라인 재생 지원
    this.video.preload = "metadata";       // 메타데이터 미리 로드
  }

  /**
   * 오디오 설정 복원 (localStorage에서)
   * @private
   */
  _restoreAudioSettings() {
    if (!this.video) return;
    
    // 음소거 상태 복원
    const savedMuted = localStorage.getItem("videoPlayerMuted");
    if (savedMuted !== null) {
      this.video.muted = savedMuted === "true";
    }
    
    // 볼륨 설정 복원
    const savedVolume = localStorage.getItem("videoPlayerVolume");
    if (savedVolume !== null) {
      this.video.volume = parseFloat(savedVolume);
    }
  }

  /**
   * 오디오 트랙 존재 여부 감지
   * @returns {boolean} 오디오 트랙 존재 여부
   */
  detectAudioTrack() {
    try {
      if (!this.video) return true;
      
      // 원래 음소거 상태 저장
      const wasMuted = this.video.muted;
      
      // 임시로 음소거 해제
      this.video.muted = false;
      
      // 볼륨이 0이면 임시로 조정
      if (this.video.volume <= 0) {
        this.video.volume = 0.5;
        this.debugLog("볼륨이 0이어서 0.5로 조정");
      }
      
      // 미디어 요소의 오디오 트랙 확인
      const hasAudioTrack = !this.video.muted && this.video.volume > 0;
      
      // 원래 음소거 상태로 복원
      this.video.muted = wasMuted;
      
      this.debugLog(`오디오 감지 확인: 음소거=${this.video.muted}, 볼륨=${this.video.volume}`);
      
      return hasAudioTrack;
    } catch (e) {
      this.debugLog(`오디오 감지 중 오류: ${e.message}`);
      return true; // 오류 발생 시 기본적으로 오디오가 있다고 가정
    }
  }

  /**
   * 비디오 소스 설정
   * @param {string} src - 비디오 URL
   * @param {function} callback - 로드 완료 후 콜백
   */
  setSource(src, callback = null) {
    if (!this.video) return;
    
    this.isMediaLoading = true;
    
    // 이전 이벤트 리스너 제거
    this.video.removeEventListener("loadedmetadata", this._onLoadedMetadata);
    this.video.removeEventListener("error", this._onLoadError);
    
    // 새 이벤트 리스너 추가
    this._onLoadedMetadata = () => {
      this.isMediaLoading = false;
      this.hasAudioTrack = this.detectAudioTrack();
      this.debugLog(`미디어 로드 완료: ${src}`);
      if (callback) callback(true);
    };
    
    this._onLoadError = () => {
      this.isMediaLoading = false;
      this.debugLog(`미디어 로드 실패: ${src}`);
      if (callback) callback(false);
    };
    
    this.video.addEventListener("loadedmetadata", this._onLoadedMetadata);
    this.video.addEventListener("error", this._onLoadError);
    
    // 비디오 소스 설정
    this.video.src = src;
    this.video.load();
  }

  /**
   * 비디오 재생
   * @returns {Promise} 재생 결과 Promise
   */
  play() {
    if (!this.video) return Promise.reject("비디오 요소가 없습니다.");
    return this.video.play().catch(error => {
      this.debugLog(`재생 실패: ${error.message}`);
      return Promise.reject(error);
    });
  }

  /**
   * 비디오 일시정지
   */
  pause() {
    if (!this.video) return;
    this.video.pause();
  }

  /**
   * 특정 시간으로 이동
   * @param {number} time - 이동할 시간(초)
   */
  seek(time) {
    if (!this.video) return;
    
    if (time < 0) time = 0;
    if (time > this.video.duration) time = this.video.duration;
    
    this.video.currentTime = time;
    this.debugLog(`시간 이동: ${time}초`);
  }

  /**
   * 볼륨 설정
   * @param {number} level - 볼륨 레벨 (0-1)
   */
  setVolume(level) {
    if (!this.video) return;
    
    if (level < 0) level = 0;
    if (level > 1) level = 1;
    
    this.video.volume = level;
    localStorage.setItem("videoPlayerVolume", level.toString());
  }

  /**
   * 음소거 토글
   * @param {boolean} mute - 음소거 여부
   */
  toggleMute(mute) {
    if (!this.video) return;
    
    this.video.muted = mute;
    localStorage.setItem("videoPlayerMuted", mute.toString());
  }

  /**
   * 현재 재생 시간 가져오기
   * @returns {number} 현재 재생 시간(초)
   */
  getCurrentTime() {
    return this.video ? this.video.currentTime : 0;
  }

  /**
   * 총 재생 시간 가져오기
   * @returns {number} 총 재생 시간(초)
   */
  getDuration() {
    return this.video ? this.video.duration : 0;
  }

  /**
   * 재생 중인지 확인
   * @returns {boolean} 재생 중이면 true
   */
  isPlaying() {
    return this.video ? !this.video.paused : false;
  }

  /**
   * 디버그 로그 출력
   * @param {string} message - 로그 메시지
   */
  debugLog(message) {
    if (this.debugMode) {
      console.log(`[VideoPlayerCore] ${message}`);
    }
  }
}

// 모듈 내보내기
export default VideoPlayerCore;
