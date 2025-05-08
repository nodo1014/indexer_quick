/**
 * Video.js 통합을 위한 초기화 파일
 * 1단계: Video.js 기본 설정 및 기존 플레이어와 병렬 운영
 */

class VideoJSPlayer {
  constructor(options = {}) {
    this.videoElement = document.getElementById("media-player");
    this.originalPlayer = null; // 기존 VideoPlayer 인스턴스 참조
    this.player = null; // Video.js 플레이어 인스턴스
    this.options = {
      fluid: true,
      controls: true,
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
          "fullscreenToggle",
        ],
      },
      ...options,
    };

    // 외부에서 참조할 디버그 모드 설정
    this.debugMode = true;

    // CDN으로부터 필요한 스크립트와 스타일 동적 로딩
    this._loadDependencies().then(() => {
      this._initPlayer();
    });
  }

  /**
   * Video.js 의존성 로드
   * @returns {Promise} 모든 의존성 로드 완료 시 resolve
   */
  _loadDependencies() {
    return new Promise((resolve, reject) => {
      // 이미 로드된 경우 바로 resolve
      if (window.videojs) {
        this.debugLog("Video.js가 이미 로드되어 있습니다.");
        resolve();
        return;
      }

      this.debugLog("Video.js 의존성 로드 중...");

      // CSS 로드
      const link = document.createElement("link");
      link.rel = "stylesheet";
      link.href =
        "https://cdn.jsdelivr.net/npm/video.js@8/dist/video-js.min.css";
      document.head.appendChild(link);

      // JS 로드
      const script = document.createElement("script");
      script.src = "https://cdn.jsdelivr.net/npm/video.js@8/dist/video.min.js";
      script.onload = () => {
        this.debugLog("Video.js 라이브러리 로드 완료");
        resolve();
      };
      script.onerror = (err) => {
        this.debugLog("Video.js 라이브러리 로드 실패");
        reject(err);
      };

      document.head.appendChild(script);
    });
  }

  /**
   * Video.js 플레이어 초기화
   */
  _initPlayer() {
    if (!window.videojs) {
      this.debugLog(
        "Video.js가 로드되지 않았습니다. 플레이어를 초기화할 수 없습니다."
      );
      return;
    }

    // 비디오 엘리먼트 설정 (클래스 추가)
    this.videoElement.classList.add("video-js", "vjs-big-play-centered");

    // Video.js 플레이어 초기화
    this.player = window.videojs(this.videoElement, this.options, () => {
      this.debugLog("Video.js 플레이어 초기화 완료");
      this._setupEventHandlers();

      // 처음에는 Video.js 컨트롤을 숨김 (기존 컨트롤 사용)
      this.player.controls(false);
    });
  }

  /**
   * 기본 이벤트 핸들러 설정
   */
  _setupEventHandlers() {
    if (!this.player) return;

    // 플레이어 에러 처리
    this.player.on("error", () => {
      const error = this.player.error();
      this.debugLog(`Video.js 에러: ${error?.code}. ${error?.message}`);
    });

    // 재생/일시정지 이벤트
    this.player.on("play", () => {
      this.debugLog("Video.js: 재생 시작");
    });

    this.player.on("pause", () => {
      this.debugLog("Video.js: 일시정지");
    });

    // 로딩 완료 이벤트
    this.player.on("loadeddata", () => {
      this.debugLog("Video.js: 미디어 데이터 로드 완료");
    });

    // 종료 이벤트
    this.player.on("ended", () => {
      this.debugLog("Video.js: 재생 종료");
    });
  }

  /**
   * 디버그 로그 출력
   * @param {string} message - 로그 메시지
   */
  debugLog(message) {
    if (this.debugMode) {
      console.log(`[VideoJSPlayer] ${message}`);
    }
  }

  /**
   * 지정된 시간에서 비디오 재생
   * @param {number} startTime - 시작 시간(초)
   * @param {number} endTime - 종료 시간(초)
   */
  playSegment(startTime, endTime) {
    if (!this.player) return;

    this.player.currentTime(startTime);

    // pause 먼저 호출하여 안정성 향상
    this.player.pause();

    // 약간의 지연 후 재생 시작 (안정성 향상)
    setTimeout(() => {
      this.player
        .play()
        .then(() => {
          this.debugLog(`${startTime}초에서 재생 시작`);

          // 종료 시간 이벤트 핸들러 설정
          if (endTime && endTime > startTime) {
            const timeUpdateHandler = () => {
              if (this.player.currentTime() >= endTime) {
                this.player.pause();
                // 종료 이벤트 발생
                this.player.trigger("segmentended");
                this.player.off("timeupdate", timeUpdateHandler);
              }
            };

            this.player.on("timeupdate", timeUpdateHandler);
          }
        })
        .catch((error) => {
          this.debugLog(`재생 에러 발생: ${error.message}`);

          if (error.name === "NotAllowedError") {
            this.debugLog(
              "자동 재생 정책으로 인한 문제. 음소거 상태로 재생 시도"
            );
            this.player.muted(true);
            this.player.play().catch((err) => {
              this.debugLog(`음소거 상태에서도 재생 실패: ${err.message}`);
            });
          }
        });
    }, 80);
  }

  /**
   * 기존 VideoPlayer와 연결
   * @param {VideoPlayer} originalPlayer - 기존 비디오 플레이어 인스턴스
   */
  connectOriginalPlayer(originalPlayer) {
    this.originalPlayer = originalPlayer;
    this.debugLog("기존 VideoPlayer 인스턴스와 연결됨");

    // 기존 플레이어의 video 엘리먼트 참조가 보존되도록 함
    if (originalPlayer && originalPlayer.video) {
      originalPlayer.video = this.videoElement;
    }
  }

  /**
   * 기존 플레이어에서 통합할 준비가 되었을 때 호출
   */
  enableVideoJS() {
    if (this.player) {
      // 기존 컨트롤을 숨기고 Video.js 컨트롤 표시
      document.getElementById("custom-audio-controls")?.classList.add("hidden");
      this.player.controls(true);
      this.debugLog("Video.js 컨트롤로 전환됨");
    }
  }

  /**
   * 플레이어 파괴 및 자원 해제
   */
  dispose() {
    if (this.player) {
      this.player.dispose();
      this.player = null;
      this.debugLog("Video.js 플레이어 인스턴스 파괴됨");
    }
  }
}

// 전역에 노출해서 다른 모듈에서 사용 가능하도록 함
window.VideoJSPlayer = VideoJSPlayer;

/**
 * Video.js 플레이어 초기화
 * 2단계: 기본 구성 및 플러그인 설정
 */

class VideoJSPlayerInit {
  constructor() {
    // Video.js 기본 설정
    this.defaultOptions = {
      controls: true,
      autoplay: false,
      preload: "auto",
      fluid: true,
      responsive: true,
      playbackRates: [0.5, 0.75, 1, 1.25, 1.5, 2],
      controlBar: {
        children: [
          "playToggle",
          "progressControl",
          "volumePanel",
          "currentTimeDisplay",
          "timeDivider",
          "durationDisplay",
          "customControlSpacer",
          "playbackRateMenuButton",
          "chaptersButton",
          "subtitlesButton",
          "fullscreenToggle",
        ],
      },
      html5: {
        nativeTextTracks: false,
        vhs: {
          overrideNative: true,
        },
      },
      plugins: {},
    };

    // CDN 링크
    this.cdnLinks = {
      css: "https://cdn.jsdelivr.net/npm/video.js@7.20.3/dist/video-js.min.css",
      js: "https://cdn.jsdelivr.net/npm/video.js@7.20.3/dist/video.min.js",
      languageJs:
        "https://cdn.jsdelivr.net/npm/video.js@7.20.3/dist/lang/ko.js",
      httpSrcJs:
        "https://cdn.jsdelivr.net/npm/@videojs/http-streaming@2.16.0/dist/videojs-http-streaming.min.js",
    };

    // 의존성 로드 상태
    this.loaded = {
      css: false,
      js: false,
      httpSrc: false,
      language: false,
    };

    this.initialized = false;
  }

  /**
   * Video.js 라이브러리 및 의존성 로드
   */
  loadDependencies() {
    return new Promise((resolve, reject) => {
      // CSS 로드
      if (!document.querySelector(`link[href="${this.cdnLinks.css}"]`)) {
        const cssLink = document.createElement("link");
        cssLink.rel = "stylesheet";
        cssLink.href = this.cdnLinks.css;
        cssLink.onload = () => {
          this.loaded.css = true;
          this._checkAllLoaded(resolve);
        };
        cssLink.onerror = () => reject(new Error("Video.js CSS 로드 실패"));
        document.head.appendChild(cssLink);
      } else {
        this.loaded.css = true;
      }

      // 메인 Video.js 로드
      if (typeof videojs === "undefined") {
        this._loadScript(this.cdnLinks.js)
          .then(() => {
            this.loaded.js = true;

            // Video.js가 로드되면 HTTP streaming 플러그인 로드
            return this._loadScript(this.cdnLinks.httpSrcJs);
          })
          .then(() => {
            this.loaded.httpSrc = true;

            // 언어 파일 로드
            return this._loadScript(this.cdnLinks.languageJs);
          })
          .then(() => {
            this.loaded.language = true;
            this._checkAllLoaded(resolve);
          })
          .catch((err) =>
            reject(new Error(`Script 로드 실패: ${err.message}`))
          );
      } else {
        this.loaded.js = true;
        this.loaded.httpSrc = true;
        this.loaded.language = true;
        this._checkAllLoaded(resolve);
      }
    });
  }

  /**
   * 모든 의존성이 로드되었는지 확인
   */
  _checkAllLoaded(resolveCallback) {
    if (
      this.loaded.css &&
      this.loaded.js &&
      this.loaded.httpSrc &&
      this.loaded.language
    ) {
      console.log("[VideoJSPlayerInit] 모든 의존성 로드 완료");
      resolveCallback();
    }
  }

  /**
   * 스크립트 동적 로드
   */
  _loadScript(src) {
    return new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = src;
      script.async = true;
      script.onload = () => resolve();
      script.onerror = () => reject(new Error(`Script 로드 실패: ${src}`));
      document.head.appendChild(script);
    });
  }

  /**
   * Video.js 플레이어 초기화
   * @param {string|HTMLElement} target - 비디오 요소 또는 선택자
   * @param {Object} options - Video.js 옵션
   */
  createPlayer(target, options = {}) {
    if (!target) {
      console.error("[VideoJSPlayerInit] 대상 요소가 필요합니다.");
      return null;
    }

    // 의존성이 로드되지 않은 경우 로드 후 재시도
    if (typeof videojs === "undefined") {
      console.log("[VideoJSPlayerInit] Video.js를 로드 중입니다.");

      return new Promise((resolve, reject) => {
        this.loadDependencies()
          .then(() => {
            const player = this._initializePlayer(target, options);
            resolve(player);
          })
          .catch((err) => {
            console.error("[VideoJSPlayerInit] 의존성 로드 실패:", err);
            reject(err);
          });
      });
    }

    // 이미 의존성이 로드된 경우 바로 초기화
    return this._initializePlayer(target, options);
  }

  /**
   * 실제 플레이어 초기화 로직
   */
  _initializePlayer(target, customOptions) {
    // 기존 플레이어가 있다면 제거
    if (
      typeof videojs !== "undefined" &&
      videojs.getPlayer &&
      videojs.getPlayers
    ) {
      const existingPlayer =
        typeof target === "string"
          ? videojs.getPlayer(target.replace(/^#/, ""))
          : videojs.getPlayer(target);

      if (existingPlayer) {
        existingPlayer.dispose();
      }
    }

    // 옵션 병합
    const mergedOptions = {
      ...this.defaultOptions,
      ...customOptions,
    };

    // 언어 설정 (기본: 한국어)
    mergedOptions.language = mergedOptions.language || "ko";

    try {
      // Video.js 플레이어 초기화
      const player = videojs(
        typeof target === "string" ? target.replace(/^#/, "") : target,
        mergedOptions
      );

      // 플레이어 준비 이벤트
      player.ready(() => {
        console.log("[VideoJSPlayerInit] Video.js 플레이어 초기화 완료");

        // 로그 설정
        player.on("error", (e) => {
          console.error("[VideoJS Error]", e.target.error);
        });

        this.initialized = true;

        // Player Ready 이벤트 발생
        if (typeof CustomEvent === "function") {
          const readyEvent = new CustomEvent("videojs:ready", {
            detail: { player },
          });
          document.dispatchEvent(readyEvent);
        }
      });

      return {
        player,
        videojs,
      };
    } catch (err) {
      console.error("[VideoJSPlayerInit] 플레이어 초기화 실패:", err);
      return null;
    }
  }

  /**
   * 비디오 소스 설정 및 재생
   * @param {Object} vjsPlayer - Video.js 플레이어 객체
   * @param {string} src - 비디오 소스 URL
   * @param {string} type - 비디오 타입 (예: 'video/mp4', 'application/x-mpegURL')
   */
  setSource(vjsPlayer, src, type) {
    if (!vjsPlayer || !vjsPlayer.player) {
      console.error("[VideoJSPlayerInit] 유효한 플레이어 객체가 필요합니다.");
      return;
    }

    const player = vjsPlayer.player;

    // 비디오 소스 확장자로 타입 추측 (제공되지 않은 경우)
    if (!type) {
      const extension = src.split(".").pop().toLowerCase();
      if (extension === "mp4") type = "video/mp4";
      else if (extension === "m3u8") type = "application/x-mpegURL";
      else if (extension === "webm") type = "video/webm";
      else type = "video/mp4"; // 기본값
    }

    try {
      player.src({
        src: src,
        type: type,
      });

      // 메타데이터 로드 후 처리
      player.one("loadedmetadata", () => {
        console.log(
          "[VideoJSPlayerInit] 비디오 메타데이터 로드 완료:",
          player.duration()
        );
      });

      // 에러 처리
      player.one("error", () => {
        const error = player.error();
        console.error(
          "[VideoJSPlayerInit] 비디오 로드 실패:",
          error && error.message
        );
      });
    } catch (err) {
      console.error("[VideoJSPlayerInit] 소스 설정 중 오류 발생:", err);
    }

    return vjsPlayer;
  }
}

// 전역에 노출해서 다른 모듈에서 사용 가능하도록 함
window.VideoJSPlayerInit = VideoJSPlayerInit;
