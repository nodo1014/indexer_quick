/**
 * VideoPlayer 클래스 - Video.js 기반 통합 플레이어
 * Subtitle Controller와 Playback Manager 통합 관리
 */

import { SubtitleController } from './subtitle-controller.js';
import { PlaybackManager } from './playback-manager.js';
import { BookmarkManager } from './bookmark-manager.js';

export class VideoPlayer {
  constructor() {
    // 요소 참조
    this.video = document.getElementById("media-player");
    
    // 초기화 확인
    if (!this.video) {
      console.error("미디어 플레이어 요소(#media-player)를 찾을 수 없습니다.");
      return;
    }

    // 상태 변수
    this.isPlaying = false;
    this.isMediaLoading = false;
    this.isInitialized = false;
    this.debugMode = true;
    
    // Video.js 플레이어 인스턴스
    this.vjsPlayer = null;
    
    // 컴포넌트는 init에서 초기화
    this.subtitleController = null;
    this.playbackManager = null;
    this.bookmarkManager = null;
    
    this.debugLog("VideoPlayer 인스턴스 생성됨");
  }

  /**
   * 초기화 메서드 - Video.js 로드 및 설정
   * @returns {Promise} 초기화 완료 Promise
   */
  init() {
    return new Promise(async (resolve, reject) => {
      try {
        this.debugLog("VideoPlayer 초기화 시작");
        
        // Video.js 플레이어 초기화
        await this._initVideoJS();
        
        // 컴포넌트 초기화
        this.subtitleController = new SubtitleController(this);
        this.playbackManager = new PlaybackManager(this);
        this.bookmarkManager = new BookmarkManager(this);
        
        // 이벤트 리스너 설정
        this._setupEventListeners();
        
        // 컴포넌트 초기화
        this.subtitleController.init();
        this.playbackManager.init();
        this.bookmarkManager.init();
        
        this.isInitialized = true;
        this.debugLog("VideoPlayer 초기화 완료");
        resolve();
      } catch (error) {
        console.error("VideoPlayer 초기화 오류:", error);
        reject(error);
      }
    });
  }

  /**
   * Video.js 초기화
   * @private
   * @returns {Promise} 초기화 완료 Promise
   */
  _initVideoJS() {
    return new Promise((resolve, reject) => {
      if (!window.videojs) {
        const error = new Error("Video.js 라이브러리가 로드되지 않았습니다.");
        console.error(error);
        reject(error);
        return;
      }

      if (!this.video) {
        const error = new Error("비디오 요소를 찾을 수 없습니다.");
        console.error(error);
        reject(error);
        return;
      }

      // 기존 비디오 요소에 Video.js 클래스 추가
      this.video.classList.add("video-js", "vjs-big-play-centered");

      // Video.js 옵션
      const options = {
        fluid: true,
        preload: "metadata",
        playbackRates: [0.5, 0.75, 1, 1.25, 1.5, 2],
        controlBar: {
          children: [
            "playToggle",
            "volumePanel",
            "currentTimeDisplay",
            "timeDivider",
            "durationDisplay",
            "progressControl",
            "playbackRateMenuButton",
            "fullscreenToggle"
          ]
        }
      };

      try {
        // 이미 초기화되어 있는 경우 해제
        if (this.vjsPlayer) {
          this.vjsPlayer.dispose();
          this.vjsPlayer = null;
        }

        // Video.js 플레이어 초기화
        this.vjsPlayer = window.videojs(this.video, options, () => {
          this.debugLog("Video.js 플레이어 초기화 완료");
          resolve();
        });
      } catch (error) {
        console.error("Video.js 플레이어 초기화 오류:", error);
        reject(error);
      }
    });
  }

  /**
   * 이벤트 리스너 설정
   * @private
   */
  _setupEventListeners() {
    if (!this.vjsPlayer) {
      console.error("이벤트 리스너 설정 실패: Video.js 플레이어가 초기화되지 않았습니다.");
      return;
    }

    // 재생/일시정지 이벤트
    this.vjsPlayer.on("play", () => {
      this.isPlaying = true;
      this.debugLog("비디오 재생 시작");
    });

    this.vjsPlayer.on("pause", () => {
      this.isPlaying = false;
      this.debugLog("비디오 일시정지");
    });

    // 종료 이벤트
    this.vjsPlayer.on("ended", () => {
      this.isPlaying = false;
      this.debugLog("비디오 재생 종료");
      if (this.playbackManager) {
        this.playbackManager.handleVideoEnded();
      }
    });

    // 미디어 로드 이벤트
    this.vjsPlayer.on("loadedmetadata", () => {
      this.isMediaLoading = false;
      this.debugLog("미디어 메타데이터 로드 완료");
    });

    // 시간 업데이트 이벤트 (자막 동기화 용)
    this.vjsPlayer.on("timeupdate", () => {
      if (this.subtitleController) {
        this.subtitleController.updateHighlightByCurrentTime();
      }
    });

    // 플레이어 외부 컨트롤 연결
    this._connectExternalControls();
    
    this.debugLog("이벤트 리스너 설정 완료");
  }

  /**
   * 외부 비디오 컨트롤 버튼 연결
   * @private
   */
  _connectExternalControls() {
    // 이전/다음 영상 버튼
    const prevVideoBtn = document.getElementById("prev-video-btn");
    const nextVideoBtn = document.getElementById("next-video-btn");
    
    if (prevVideoBtn) {
      prevVideoBtn.addEventListener("click", () => {
        console.log("이전 비디오 버튼 클릭");
        if (this.playbackManager) {
          this.playbackManager.navigateToAdjacentVideo(-1);
        }
      });
    }

    if (nextVideoBtn) {
      nextVideoBtn.addEventListener("click", () => {
        console.log("다음 비디오 버튼 클릭");
        if (this.playbackManager) {
          this.playbackManager.navigateToAdjacentVideo(1);
        }
      });
    }

    // 이전/다음 자막 버튼
    const prevLineBtn = document.getElementById("prev-line-btn");
    const nextLineBtn = document.getElementById("next-line-btn");
    
    if (prevLineBtn) {
      prevLineBtn.addEventListener("click", () => {
        console.log("이전 자막 버튼 클릭");
        if (this.playbackManager) {
          this.playbackManager.jumpToSubtitle(-1);
        }
      });
    }

    if (nextLineBtn) {
      nextLineBtn.addEventListener("click", () => {
        console.log("다음 자막 버튼 클릭");
        if (this.playbackManager) {
          this.playbackManager.jumpToSubtitle(1);
        }
      });
    }

    // 반복 재생 버튼
    const repeatLineBtn = document.getElementById("repeat-line-btn");
    if (repeatLineBtn) {
      repeatLineBtn.addEventListener("click", () => {
        console.log("반복 재생 버튼 클릭");
        if (this.playbackManager) {
          this.playbackManager.toggleRepeat();
        }
      });
    }

    // 재생 모드 설정
    const playbackModeSelect = document.getElementById("playback-mode");
    if (playbackModeSelect) {
      playbackModeSelect.addEventListener("change", (event) => {
        console.log(`재생 모드 변경: ${event.target.value}`);
        if (this.playbackManager) {
          this.playbackManager.setPlaybackMode(event.target.value);
        }
      });
    }
    
    this.debugLog("외부 컨트롤 버튼 연결 완료");
  }

  /**
   * 자막 클릭 핸들러 설정 (외부에서 접근 가능하도록)
   */
  setupSubtitleClickHandlers() {
    if (this.subtitleController) {
      this.subtitleController.setupSubtitleClickHandlers();
    } else {
      console.error("자막 컨트롤러가 초기화되지 않았습니다.");
    }
  }

  /**
   * 현재 자막 표시 초기화 (외부에서 접근 가능하도록)
   */
  clearCurrentSubtitleDisplay() {
    if (this.subtitleController) {
      this.subtitleController.clearCurrentSubtitleDisplay();
    } else {
      console.error("자막 컨트롤러가 초기화되지 않았습니다.");
    }
  }

  /**
   * 미디어 소스 설정
   * @param {string} src - 미디어 URL
   */
  setSource(src) {
    if (!this.vjsPlayer) {
      console.error("Video.js 플레이어가 초기화되지 않았습니다.");
      return;
    }
    
    if (!src) {
      console.error("소스 URL이 제공되지 않았습니다.");
      return;
    }
    
    this.isMediaLoading = true;
    console.log("미디어 소스 설정:", src);
    
    const mimeType = this._getMimeType(src);
    
    try {
      this.vjsPlayer.src({
        src: src,
        type: mimeType
      });
      
      // 파일명 표시 업데이트
      const filename = this._getFilenameFromPath(src);
      this.updateCurrentFilename(filename);
      
      this.debugLog(`미디어 소스 설정 완료: ${filename} (${src})`);
    } catch (error) {
      console.error("미디어 소스 설정 오류:", error, src);
    }
  }

  /**
   * 미디어 타입 추론
   * @param {string} src - 미디어 URL
   * @returns {string} MIME 타입
   * @private
   */
  _getMimeType(src) {
    if (!src) return '';
    
    const ext = src.split('.').pop().toLowerCase();
    
    const mimeTypes = {
      'mp4': 'video/mp4',
      'webm': 'video/webm',
      'ogg': 'video/ogg',
      'mp3': 'audio/mpeg',
      'wav': 'audio/wav',
      'aac': 'audio/aac',
      'flac': 'audio/flac',
      'mkv': 'video/x-matroska'
    };
    
    return mimeTypes[ext] || '';
  }

  /**
   * 경로에서 파일명 추출
   * @param {string} path - 파일 경로
   * @returns {string} 파일명
   * @private
   */
  _getFilenameFromPath(path) {
    if (!path) return 'Unknown';
    return path.split('/').pop() || path;
  }

  /**
   * 현재 파일명 표시 업데이트
   * @param {string} filename - 파일명
   */
  updateCurrentFilename(filename) {
    const filenameEl = document.getElementById("current-filename");
    if (filenameEl) {
      filenameEl.textContent = `현재 파일: ${filename}`;
    }
  }

  /**
   * 미디어 세그먼트 재생 (시작 시간 ~ 종료 시간)
   * @param {number} startTime - 시작 시간 (초)
   * @param {number} endTime - 종료 시간 (초)
   */
  playSegment(startTime, endTime) {
    if (!this.vjsPlayer) {
      console.error("Video.js 플레이어가 초기화되지 않았습니다.");
      return;
    }
    
    // 숫자로 변환
    startTime = parseFloat(startTime);
    endTime = parseFloat(endTime);
    
    console.log(`세그먼트 재생 요청: ${startTime}초 ~ ${endTime}초`);
    
    // 잘못된 시간 값 검사 (NaN 또는 음수)
    if (isNaN(startTime) || startTime < 0) {
      console.warn("유효하지 않은 시작 시간:", startTime);
      startTime = 0;
    }
    
    if (isNaN(endTime) || endTime <= startTime) {
      console.warn("유효하지 않은 종료 시간:", endTime);
      endTime = startTime + 5; // 기본값: 시작 시간 + 5초
    }
    
    // 소스가 로드되지 않은 경우
    if (this.isMediaLoading || this.vjsPlayer.readyState() < 1) {
      console.log("미디어 로드 중, 준비 완료 후 재생될 예정입니다.");
      
      // 미디어 로드 완료 후 재생
      const playWhenReady = () => {
        this.vjsPlayer.off('loadedmetadata', playWhenReady);
        this._executePlaySegment(startTime, endTime);
      };
      
      this.vjsPlayer.on('loadedmetadata', playWhenReady);
      return;
    }
    
    this._executePlaySegment(startTime, endTime);
  }

  /**
   * 실제 세그먼트 재생 실행
   * @param {number} startTime - 시작 시간 (초)
   * @param {number} endTime - 종료 시간 (초)
   * @private
   */
  _executePlaySegment(startTime, endTime) {
    if (!this.vjsPlayer) {
      console.error("Video.js 플레이어가 초기화되지 않았습니다.");
      return;
    }
    
    console.log(`세그먼트 재생 실행: ${startTime}초 ~ ${endTime}초`);
    
    // 미디어 지속 시간보다 큰 경우 조정
    const duration = this.vjsPlayer.duration();
    if (isFinite(duration) && startTime > duration) {
      console.warn("시작 시간이 미디어 길이보다 깁니다. 조정합니다.", startTime, "->", 0);
      startTime = 0;
    }
    
    if (isFinite(duration) && endTime > duration) {
      console.warn("종료 시간이 미디어 길이보다 깁니다. 조정합니다.", endTime, "->", duration);
      endTime = duration;
    }
    
    // 재생 상태 업데이트
    console.log(`실제 재생 시간: ${startTime}초 ~ ${endTime}초 (총 길이: ${duration}초)`);
    
    // 현재 시간을 시작 시간으로 설정
    this.vjsPlayer.currentTime(startTime);
    
    // 이전 이벤트 리스너 제거
    if (this._timeUpdateHandler) {
      this.vjsPlayer.off('timeupdate', this._timeUpdateHandler);
      this._timeUpdateHandler = null;
    }
    
    // 종료 시간에 도달하면 일시정지하는 리스너
    this._timeUpdateHandler = () => {
      if (!this.vjsPlayer) return;
      
      const currentTime = this.vjsPlayer.currentTime();
      
      // 종료 시간에 도달했는지 확인 (0.5초 여유)
      if (currentTime >= endTime - 0.5) {
        console.log(`종료 시간(${endTime}초)에 도달, 일시정지`);
        this.vjsPlayer.pause();
        this.vjsPlayer.off('timeupdate', this._timeUpdateHandler);
        this._timeUpdateHandler = null;
        
        // 재생 완료 이벤트 발생
        if (this.playbackManager) {
          this.playbackManager.onSegmentEnded();
        }
      }
    };
    
    // 시간 업데이트 이벤트에 리스너 등록
    this.vjsPlayer.on('timeupdate', this._timeUpdateHandler);
    
    // 재생 시작
    this.vjsPlayer.play().then(() => {
      console.log("재생 시작됨");
    }).catch(error => {
      console.error("재생 시작 실패:", error);
      
      // 사용자 상호작용이 필요한 경우 안내 버튼 표시 (자동 재생 정책 때문)
      const existingPlayButton = document.getElementById('force-play-button');
      if (existingPlayButton) {
        existingPlayButton.remove();
      }
      
      const playButton = document.createElement('button');
      playButton.id = 'force-play-button';
      playButton.textContent = '재생';
      playButton.className = 'fixed top-4 right-4 bg-blue-500 text-white px-4 py-2 rounded z-50';
      playButton.onclick = () => {
        this.vjsPlayer.play();
        playButton.remove();
      };
      document.body.appendChild(playButton);
    });
  }

  /**
   * 현재 재생 시간 가져오기
   * @returns {number} 현재 시간(초)
   */
  getCurrentTime() {
    return this.vjsPlayer ? this.vjsPlayer.currentTime() : 0;
  }

  /**
   * 디버그 로깅
   * @param {string} message - 로그 메시지
   */
  debugLog(message) {
    if (this.debugMode) {
      console.log(`[VideoPlayer] ${message}`);
    }
  }

  /**
   * 리소스 정리
   */
  dispose() {
    try {
      if (this.vjsPlayer) {
        this.vjsPlayer.dispose();
        this.vjsPlayer = null;
      }
      this.debugLog("리소스 정리 완료");
    } catch (error) {
      console.error("리소스 정리 오류:", error);
    }
  }
}

// 기본 내보내기
export default VideoPlayer;