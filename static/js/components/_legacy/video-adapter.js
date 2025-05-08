/**
 * Video.js 어댑터
 * 2단계: 기존 비디오 시스템과 Video.js 연동
 */

class VideoJSAdapter {
  constructor() {
    // 플레이어 인스턴스 참조
    this.videojs = null; // videojs 객체
    this.vjsPlayer = null; // videojs 플레이어 인스턴스
    this.originalPlayer = null; // 기존 플레이어 인스턴스

    // 자막 및 초기화 모듈 참조
    this.subtitles = null;
    this.initializer = null;

    // 현재 비디오 정보
    this.currentVideoUrl = "";
    this.currentVideoType = "";

    // 어댑터 기능 활성화 상태
    this.initialized = false;
    this.adaptDone = false;
    this.isDebug = true;

    // Video.js 요소 ID
    this.videoElementId = "media-player";

    // 연결 상태 확인을 위한 이벤트 리스너 설정
    this._setupInitializationListener();
  }

  /**
   * 초기화 모듈, 플레이어 및 자막 설정
   */
  _setupInitializationListener() {
    // 비디오 요소가 준비되었을 때 초기화
    window.addEventListener("DOMContentLoaded", () => {
      this._initComponent();
    });

    // Video.js 초기화 완료 이벤트 구독
    document.addEventListener("videojs:ready", (e) => {
      if (this.initialized) return;

      this.vjsPlayer = e.detail.player;
      this._debugLog("Video.js 플레이어 준비됨");
      this._connectSubtitles();
    });
  }

  /**
   * 어댑터 초기화 및 모듈 로딩
   */
  _initComponent() {
    // 이미 초기화된 경우 스킵
    if (this.initialized) return;

    // 비디오 요소 확인
    const videoElement = document.getElementById(this.videoElementId);
    if (!videoElement) {
      this._debugLog("비디오 요소를 찾을 수 없습니다. 초기화를 중단합니다.");
      return;
    }

    // Video.js 초기화 모듈 생성
    this.initializer = new VideoJSPlayerInit();

    // 어댑터 초기화 완료
    this.initialized = true;
    this._debugLog("어댑터 초기화 완료");
  }

  /**
   * 자막 모듈 연결
   */
  _connectSubtitles() {
    if (!this.vjsPlayer) {
      this._debugLog(
        "Video.js 플레이어가 준비되지 않았습니다. 자막을 연결할 수 없습니다."
      );
      return;
    }

    // 자막 모듈 초기화
    this.subtitles = new VideoJSSubtitles(this.vjsPlayer);
    this._debugLog("자막 모듈 초기화 완료");

    // 자막 컨트롤 추가
    setTimeout(() => {
      this.subtitles.addSubtitleControls();
    }, 500);
  }

  /**
   * 기존 비디오 플레이어와 연결
   * @param {Object} originalPlayer - 기존 비디오 플레이어 인스턴스
   */
  connect(originalPlayer) {
    if (!originalPlayer) {
      this._debugLog("연결할 기존 플레이어가 제공되지 않았습니다.");
      return false;
    }

    this.originalPlayer = originalPlayer;
    this._debugLog("기존 플레이어와 연결됨");

    // 초기화되지 않은 경우 초기화
    if (!this.initialized) {
      this._initComponent();
    }

    return true;
  }

  /**
   * Video.js 플레이어 생성 및 초기화
   * @param {Object} options - Video.js 초기화 옵션
   * @returns {Promise} 플레이어 생성 완료 Promise
   */
  createPlayer(options = {}) {
    return new Promise((resolve, reject) => {
      // 초기화 상태 확인
      if (!this.initialized || !this.initializer) {
        this._initComponent();
      }

      // 이미 플레이어가 생성된 경우
      if (this.vjsPlayer) {
        resolve(this.vjsPlayer);
        return;
      }

      // 컨테이너 요소 확인
      const videoElement = document.getElementById(this.videoElementId);
      if (!videoElement) {
        reject(new Error("비디오 요소를 찾을 수 없습니다."));
        return;
      }

      // 기본 옵션과 사용자 옵션 병합
      const playerOptions = {
        controls: true,
        autoplay: false,
        preload: "auto",
        fluid: true,
        responsive: true,
        playbackRates: [0.5, 0.75, 1, 1.25, 1.5, 2],
        language: "ko",
        ...options,
      };

      // Video.js 플레이어 생성
      this._debugLog("Video.js 플레이어 생성 중...");

      // 비디오 요소에 필요한 클래스 추가
      videoElement.classList.add("video-js", "vjs-big-play-centered");

      // 플레이어 생성 (Promise 또는 객체 반환)
      const playerResult = this.initializer.createPlayer(
        this.videoElementId,
        playerOptions
      );

      // Promise 객체인 경우 처리
      if (playerResult instanceof Promise) {
        playerResult
          .then((result) => {
            this.vjsPlayer = result.player;
            this.videojs = result.videojs;

            // 자막 모듈 연결
            this._connectSubtitles();
            this._setupEventHandlers();

            resolve(result);
          })
          .catch((error) => {
            this._debugLog(`플레이어 생성 중 오류: ${error.message}`);
            reject(error);
          });
      } else if (playerResult) {
        // 객체가 바로 반환된 경우
        this.vjsPlayer = playerResult.player;
        this.videojs = playerResult.videojs;

        // 자막 모듈 연결
        this._connectSubtitles();
        this._setupEventHandlers();

        resolve(playerResult);
      } else {
        reject(new Error("플레이어 생성에 실패했습니다."));
      }
    });
  }

  /**
   * Video.js 이벤트 핸들러 설정
   */
  _setupEventHandlers() {
    if (!this.vjsPlayer) return;

    this.vjsPlayer.on("play", () => {
      this._debugLog("비디오 재생 시작");
      // 기존 플레이어에 이벤트 전파 (필요시)
      if (
        this.originalPlayer &&
        typeof this.originalPlayer.onPlay === "function"
      ) {
        this.originalPlayer.onPlay();
      }
    });

    this.vjsPlayer.on("pause", () => {
      this._debugLog("비디오 일시정지");
      // 기존 플레이어에 이벤트 전파 (필요시)
      if (
        this.originalPlayer &&
        typeof this.originalPlayer.onPause === "function"
      ) {
        this.originalPlayer.onPause();
      }
    });

    this.vjsPlayer.on("ended", () => {
      this._debugLog("비디오 재생 종료");
      // 기존 플레이어에 이벤트 전파 (필요시)
      if (
        this.originalPlayer &&
        typeof this.originalPlayer.onEnded === "function"
      ) {
        this.originalPlayer.onEnded();
      }
    });

    this.vjsPlayer.on("error", () => {
      const error = this.vjsPlayer.error();
      this._debugLog(
        `비디오 에러 발생: ${error ? error.message : "알 수 없는 오류"}`
      );
    });

    // 시간 변경 이벤트 - 기존 UI 업데이트용
    this.vjsPlayer.on("timeupdate", () => {
      const currentTime = this.vjsPlayer.currentTime();

      // 기존 플레이어의 시간 업데이트 이벤트 호출 (필요시)
      if (
        this.originalPlayer &&
        typeof this.originalPlayer.onTimeUpdate === "function"
      ) {
        this.originalPlayer.onTimeUpdate(currentTime);
      }
    });

    // 로딩 완료 이벤트
    this.vjsPlayer.on("loadedmetadata", () => {
      this._debugLog("비디오 메타데이터 로딩 완료");

      // 비디오가 로드되면 페이지의 자막 검색 및 추가
      if (this.subtitles) {
        setTimeout(() => {
          this.subtitles.extractAndAddVisibleSubtitles();
        }, 500);
      }
    });
  }

  /**
   * 비디오 소스 설정
   * @param {string} src - 비디오 URL
   * @param {string} type - 비디오 MIME 타입 (옵션)
   * @returns {Promise} 비디오 로드 Promise
   */
  setSource(src, type) {
    return new Promise((resolve, reject) => {
      // 플레이어가 없으면 먼저 생성
      if (!this.vjsPlayer) {
        this.createPlayer()
          .then(() => {
            this._loadVideoSource(src, type, resolve, reject);
          })
          .catch((error) => {
            reject(error);
          });
      } else {
        this._loadVideoSource(src, type, resolve, reject);
      }
    });
  }

  /**
   * 실제 비디오 소스 로딩 처리
   */
  _loadVideoSource(src, type, resolve, reject) {
    if (!src) {
      reject(new Error("비디오 소스 URL이 필요합니다."));
      return;
    }

    // 이미 같은 소스가 로드되었는지 확인
    if (this.currentVideoUrl === src) {
      resolve(this.vjsPlayer);
      return;
    }

    this.currentVideoUrl = src;

    // 비디오 타입 결정 (제공되지 않은 경우)
    if (!type) {
      const extension = src.split(".").pop().toLowerCase();
      if (extension === "mp4") {
        type = "video/mp4";
      } else if (extension === "m3u8") {
        type = "application/x-mpegURL";
      } else if (extension === "webm") {
        type = "video/webm";
      } else {
        type = "video/mp4"; // 기본값
      }
    }

    this.currentVideoType = type;

    try {
      // 비디오 소스 설정
      this.vjsPlayer.src({
        src: src,
        type: type,
      });

      // 메타데이터 로드 이벤트 처리
      this.vjsPlayer.one("loadedmetadata", () => {
        this._debugLog(`비디오 로드 완료: ${src}`);
        resolve(this.vjsPlayer);
      });

      // 에러 처리
      this.vjsPlayer.one("error", () => {
        const error = this.vjsPlayer.error();
        const errorMessage = error ? error.message : "알 수 없는 오류";
        this._debugLog(`비디오 로드 실패: ${errorMessage}`);
        reject(new Error(errorMessage));
      });
    } catch (error) {
      this._debugLog(`비디오 소스 설정 중 오류: ${error.message}`);
      reject(error);
    }
  }

  /**
   * 특정 시간 구간 재생
   * @param {number} startTime - 시작 시간(초)
   * @param {number} endTime - 종료 시간(초, 옵션)
   */
  playSegment(startTime, endTime) {
    if (!this.vjsPlayer) {
      this._debugLog("플레이어가 준비되지 않았습니다.");
      return;
    }

    // 시작 시간 유효성 검사
    if (typeof startTime !== "number" || startTime < 0) {
      this._debugLog("유효한 시작 시간이 필요합니다.");
      return;
    }

    // 종료 시간 유효성 검사 (제공된 경우)
    if (endTime && (typeof endTime !== "number" || endTime <= startTime)) {
      this._debugLog("종료 시간은 시작 시간보다 커야 합니다.");
      return;
    }

    // 현재 시간 설정
    this.vjsPlayer.currentTime(startTime);

    // 재생 시작 (안정성을 위해 약간의 지연 추가)
    setTimeout(() => {
      this.vjsPlayer
        .play()
        .then(() => {
          this._debugLog(`${startTime}초부터 재생 시작`);

          // 종료 시간이 지정된 경우, 해당 시간에 정지하도록 설정
          if (endTime) {
            const timeUpdateHandler = () => {
              if (this.vjsPlayer.currentTime() >= endTime) {
                this.vjsPlayer.pause();
                this.vjsPlayer.off("timeupdate", timeUpdateHandler);
                this.vjsPlayer.trigger("segmentended", {
                  start: startTime,
                  end: endTime,
                });
              }
            };

            this.vjsPlayer.on("timeupdate", timeUpdateHandler);
          }
        })
        .catch((error) => {
          this._debugLog(`재생 시작 중 오류: ${error.message}`);

          if (error.name === "NotAllowedError") {
            this._debugLog(
              "자동 재생 정책으로 인한 문제. 음소거 상태로 재생 시도"
            );
            this.vjsPlayer.muted(true);
            this.vjsPlayer.play().catch((err) => {
              this._debugLog(`음소거 상태에서도 재생 실패: ${err.message}`);
            });
          }
        });
    }, 100);
  }

  /**
   * 재생 일시정지
   */
  pause() {
    if (this.vjsPlayer) {
      this.vjsPlayer.pause();
    }
  }

  /**
   * 재생 시작/재개
   */
  play() {
    if (this.vjsPlayer) {
      this.vjsPlayer.play();
    }
  }

  /**
   * 음소거 토글
   * @param {boolean} mute - 음소거 여부 (값이 없으면 현재 상태 반전)
   * @returns {boolean} - 변경 후 음소거 상태
   */
  toggleMute(mute) {
    if (!this.vjsPlayer) return false;

    if (typeof mute === "boolean") {
      this.vjsPlayer.muted(mute);
    } else {
      this.vjsPlayer.muted(!this.vjsPlayer.muted());
    }

    return this.vjsPlayer.muted();
  }

  /**
   * 볼륨 설정
   * @param {number} level - 볼륨 레벨 (0.0 ~ 1.0)
   */
  setVolume(level) {
    if (!this.vjsPlayer) return;

    // 유효성 검사
    if (typeof level !== "number" || level < 0 || level > 1) {
      this._debugLog("볼륨은 0과 1 사이의 값이어야 합니다.");
      return;
    }

    this.vjsPlayer.volume(level);
  }

  /**
   * 현재 재생 시간 가져오기
   * @returns {number} 현재 재생 시간(초)
   */
  getCurrentTime() {
    return this.vjsPlayer ? this.vjsPlayer.currentTime() : 0;
  }

  /**
   * 비디오 전체 길이 가져오기
   * @returns {number} 비디오 전체 길이(초)
   */
  getDuration() {
    return this.vjsPlayer ? this.vjsPlayer.duration() : 0;
  }

  /**
   * 비디오가 재생 중인지 확인
   * @returns {boolean} 재생 중이면 true
   */
  isPlaying() {
    return this.vjsPlayer ? !this.vjsPlayer.paused() : false;
  }

  /**
   * 특정 페이지 내 비디오 요소에 대한 재생 설정
   * 버튼에서 직접 호출하는 형태의 전환 함수
   */
  switchToVideoJS() {
    // 현재 페이지에 생성 버튼 또는 인디케이터 추가
    const container = document.querySelector(".video-container");
    if (!container) return;

    let switchButton = document.getElementById("videojs-switch");

    if (!switchButton) {
      switchButton = document.createElement("button");
      switchButton.id = "videojs-switch";
      switchButton.className = "videojs-switch-btn";
      switchButton.textContent = "Video.js로 전환";
      switchButton.style.cssText = `
        display: block;
        margin: 10px auto;
        padding: 8px 15px;
        background-color: #2196F3;
        color: white;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        font-size: 14px;
      `;

      const videoElement = document.getElementById(this.videoElementId);
      if (videoElement) {
        container.insertBefore(switchButton, videoElement.nextSibling);
      } else {
        container.appendChild(switchButton);
      }

      // 클릭 이벤트 핸들러 추가
      switchButton.addEventListener("click", () => {
        this._performVideoJSSwitch(switchButton);
      });
    }
  }

  /**
   * Video.js로 전환 수행
   */
  _performVideoJSSwitch(button) {
    // 이미 전환된 경우
    if (this.adaptDone) return;

    // 사용자에게 로딩 피드백 표시
    button.textContent = "Video.js 로딩 중...";
    button.disabled = true;

    // 플레이어 생성 및 초기화
    this.createPlayer()
      .then(() => {
        // 기존 컨트롤 숨기기
        const customControls = document.getElementById("custom-audio-controls");
        if (customControls) {
          customControls.style.display = "none";
        }

        // 현재 재생 중인 비디오 소스 가져오기
        let currentSrc = "";
        let currentTime = 0;

        if (this.originalPlayer) {
          if (this.originalPlayer.video && this.originalPlayer.video.src) {
            currentSrc = this.originalPlayer.video.src;
          }

          if (typeof this.originalPlayer.getCurrentTime === "function") {
            currentTime = this.originalPlayer.getCurrentTime();
          }
        }

        // 현재 비디오가 있으면 Video.js에 설정
        if (currentSrc) {
          this.setSource(currentSrc)
            .then(() => {
              // 현재 시간 설정
              if (currentTime > 0) {
                this.vjsPlayer.currentTime(currentTime);
              }

              // 버튼 업데이트
              button.textContent = "Video.js 활성화됨";
              button.style.backgroundColor = "#4CAF50";
              this.adaptDone = true;

              // 자막 추출 및 추가
              if (this.subtitles) {
                setTimeout(() => {
                  this.subtitles.extractAndAddVisibleSubtitles();
                }, 800);
              }
            })
            .catch((err) => {
              this._debugLog(`비디오 소스 설정 중 오류: ${err.message}`);
              button.textContent = "Video.js 전환 실패";
              button.style.backgroundColor = "#F44336";
              button.disabled = false;
            });
        } else {
          // 비디오 소스가 없는 경우
          button.textContent = "Video.js 활성화됨";
          button.style.backgroundColor = "#4CAF50";
          this.adaptDone = true;
        }
      })
      .catch((err) => {
        this._debugLog(`Video.js 초기화 중 오류: ${err.message}`);
        button.textContent = "Video.js 전환 실패";
        button.style.backgroundColor = "#F44336";
        button.disabled = false;
      });
  }

  /**
   * 자원 해제 및 플레이어 파괴
   */
  dispose() {
    if (this.vjsPlayer) {
      this.vjsPlayer.dispose();
      this.vjsPlayer = null;
      this.initialized = false;
      this.adaptDone = false;
      this._debugLog("플레이어 자원 해제됨");
    }
  }

  /**
   * 디버그 로그
   */
  _debugLog(message) {
    if (this.isDebug) {
      console.log(`[VideoJSAdapter] ${message}`);
    }
  }
}

// 전역에 노출해서 다른 모듈에서 사용 가능하도록 함
window.VideoJSAdapter = VideoJSAdapter;

// 사용 편의성을 위한 전역 인스턴스 생성
window.videoJSAdapter = new VideoJSAdapter();
