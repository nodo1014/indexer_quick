// Video Player Component
class VideoPlayer {
  constructor() {
    this.video = document.getElementById("media-player");
    if (!this.video) return;

    // Playback mode state
    this.playbackMode = "search-results"; // 기본값: 검색 결과만 연속 재생
    this.currentSubtitleIndex = -1;
    this.playbackHistory = [];
    this.isPlaybackHandlerActive = false;
    this.isRepeating = false; // 반복 재생 상태 추적
    this.repeatHandler = null; // 반복 재생 핸들러 저장
    this.pendingPlayNext = false; // 다음 자막 재생 보류 상태 추적
    this.isMediaLoading = false; // 미디어 로딩 상태 추적
    this.processedEndEvent = false; // 'ended' 이벤트 처리 중복 방지
    this.hasAudioTrack = true; // 오디오 트랙 존재 여부

    // 기본 비디오 속성 설정
    this.video.crossOrigin = "anonymous"; // CORS 이슈 방지
    this.video.playsInline = true; // 모바일 인라인 재생 지원
    this.video.preload = "metadata"; // 메타데이터 미리 로드

    // 오디오 음소거 상태 복원 (localStorage에서)
    const savedMuted = localStorage.getItem("videoPlayerMuted");
    if (savedMuted !== null) {
      this.video.muted = savedMuted === "true";
    }

    // 오디오 볼륨 설정 복원
    const savedVolume = localStorage.getItem("videoPlayerVolume");
    if (savedVolume !== null) {
      this.video.volume = parseFloat(savedVolume);
    }

    // Initialize event listeners
    this._initEventListeners();

    // 디버그 로깅을 위한 코드
    this.debugMode = true;
    this.debugLog("비디오 플레이어 인스턴스 생성됨");

    // Video.js 어댑터 참조 (초기화는 init()에서 수행)
    this.videoJSAdapter = null;
  }

  // 디버그 로깅 함수
  debugLog(message) {
    if (this.debugMode) {
      console.log(`[VideoPlayer] ${message}`);
    }
  }

  _initEventListeners() {
    // Play/Pause toggle (click)
    this.video.addEventListener("click", () => {
      if (this.video.paused) this.video.play();
      else this.video.pause();
    });

    // Playback mode selection event listener
    const playbackModeSelect = document.getElementById("playback-mode");
    if (playbackModeSelect) {
      playbackModeSelect.addEventListener("change", (event) => {
        // 모드 변경 시 기존 반복 재생 중지
        if (this.isRepeating) {
          this._stopRepeat();
        }

        this.playbackMode = event.target.value;
        this.setupPlaybackHandler();

        console.log(`재생 모드가 '${this.playbackMode}'로 설정되었습니다.`);
      });
    }

    // Previous/Next video buttons
    document.getElementById("prev-video-btn")?.addEventListener("click", () => {
      // 현재 검색 결과에서 이전 비디오로 이동
      this.navigateToAdjacentVideo(-1);
    });

    document.getElementById("next-video-btn")?.addEventListener("click", () => {
      // 현재 검색 결과에서 다음 비디오로 이동
      this.navigateToAdjacentVideo(1);
    });

    // Previous/Next line buttons
    document.getElementById("prev-line-btn")?.addEventListener("click", () => {
      // 반복 재생 중이면 중지
      if (this.isRepeating) {
        this._stopRepeat();
      }
      this.jumpToSubtitle(-1);
    });

    document.getElementById("next-line-btn")?.addEventListener("click", () => {
      // 반복 재생 중이면 중지
      if (this.isRepeating) {
        this._stopRepeat();
      }
      this.jumpToSubtitle(1);
    });

    // Repeat line button
    document
      .getElementById("repeat-line-btn")
      ?.addEventListener("click", () => {
        // 이미 반복 중이면 중지
        if (this.isRepeating) {
          this._stopRepeat();
          console.log("문장 반복 중지");
        } else {
          this.repeatCurrentLine();
          console.log("문장 반복 시작");
        }
      });

    // 오디오 관련 이벤트 추가
    this.video.addEventListener("volumechange", () => {
      // 볼륨 변경 시 저장
      localStorage.setItem("videoPlayerMuted", this.video.muted.toString());
      localStorage.setItem("videoPlayerVolume", this.video.volume.toString());
    });

    // 오디오 트랙 감지
    this.video.addEventListener("loadedmetadata", () => {
      this._detectAudioTrack();
    });
  }

  // 오디오 트랙 감지 메서드
  _detectAudioTrack() {
    try {
      // 더 단순한 방식으로 오디오 있는지 확인 - muted 속성을 활용
      const videoEl = this.video;

      // 원래 음소거 상태 저장
      const wasMuted = videoEl.muted;

      // 임시로 음소거 해제
      videoEl.muted = false;

      // 볼륨 확인 (볼륨이 0이면 조정)
      if (videoEl.volume <= 0) {
        videoEl.volume = 0.5;
        this.debugLog("볼륨이 0이어서 0.5로 조정");
      }

      // 미디어 요소가 오디오 트랙을 가지고 있는지 확인하는 간단한 방법
      const hasAudioTrack = !videoEl.muted && videoEl.volume > 0;

      this.debugLog(
        `오디오 감지 확인: 음소거=${videoEl.muted}, 볼륨=${videoEl.volume}`
      );

      // 오디오가 없거나 문제가 있는 경우 알림
      setTimeout(() => {
        // 재생 중인 경우에만 확인
        if (!videoEl.paused) {
          // 볼륨이 0보다 크고 음소거가 아닌데 오디오가 들리지 않는 경우 사용자에게 알림
          if (!videoEl.muted && videoEl.volume > 0) {
            this.debugLog("오디오 설정은 정상적이지만 오디오가 없을 수 있음");
            // 사용자에게 알림 표시 (재생 후 2초 지연)
            setTimeout(() => {
              // 여전히 재생 중인지 확인
              if (!videoEl.paused) {
                this._showAudioTroubleshootingNotice();
              }
            }, 2000);
          }
        }
      }, 500);

      return hasAudioTrack;
    } catch (e) {
      this.debugLog(`오디오 감지 중 오류: ${e.message}`);
      return true; // 오류 발생 시 기본적으로 오디오가 있다고 가정
    }
  }

  // 오디오 문제 해결 안내 표시
  _showAudioTroubleshootingNotice() {
    // 이미 알림이 표시되어 있으면 중복 표시 방지
    if (document.getElementById("audio-troubleshooting")) return;

    const noticeEl = document.createElement("div");
    noticeEl.id = "audio-troubleshooting";
    noticeEl.className = "audio-troubleshooting";
    noticeEl.innerHTML = `
      <div class="audio-troubleshooting-content">
        <p>🔊 소리가 들리지 않나요?</p>
        <div class="troubleshooting-options">
          <button class="unmute-btn">음소거 해제</button>
          <button class="volume-up-btn">볼륨 높이기</button>
          <button class="troubleshooting-close">닫기</button>
        </div>
      </div>
    `;

    // 스타일 추가
    noticeEl.style.cssText = `
      position: absolute; top: 10px; left: 50%; transform: translateX(-50%);
      background: rgba(0,0,0,0.8); color: white; padding: 12px 15px;
      border-radius: 5px; z-index: 1000; max-width: 90%; text-align: center;
    `;

    // 버튼 스타일
    const buttons = noticeEl.querySelectorAll("button");
    buttons.forEach((btn) => {
      btn.style.cssText = `
        background: rgba(255,255,255,0.2); border: none; color: white;
        padding: 5px 10px; margin: 5px; border-radius: 4px; cursor: pointer;
      `;
    });

    // 플레이어 컨테이너에 추가
    const container = this.video.parentElement;
    if (container) {
      container.style.position = "relative";
      container.appendChild(noticeEl);

      // 음소거 해제 버튼
      noticeEl.querySelector(".unmute-btn").addEventListener("click", () => {
        this.video.muted = false;
        this.debugLog("사용자가 음소거 해제 버튼 클릭");
        noticeEl.remove();
      });

      // 볼륨 높이기 버튼
      noticeEl.querySelector(".volume-up-btn").addEventListener("click", () => {
        this.video.volume = Math.min(1, this.video.volume + 0.2);
        this.debugLog(
          `사용자가 볼륨 높이기 버튼 클릭, 현재 볼륨: ${this.video.volume}`
        );
        noticeEl.remove();
      });

      // 닫기 버튼
      noticeEl
        .querySelector(".troubleshooting-close")
        .addEventListener("click", () => {
          noticeEl.remove();
        });

      // 10초 후 자동 제거
      setTimeout(() => {
        if (document.getElementById("audio-troubleshooting")) {
          noticeEl.remove();
        }
      }, 10000);
    }
  }

  // 비디오 간 이동 (이전/다음 비디오)
  navigateToAdjacentVideo(direction) {
    // 현재 표시된 모든 비디오 경로 수집
    const allVideos = new Set();
    const allSubtitles = this.getVisibleSubtitles();

    allSubtitles.forEach((el) => {
      allVideos.add(el.dataset.mediaPath);
    });

    // 중복 없는 비디오 경로 배열로 변환
    const videoArray = Array.from(allVideos);

    if (videoArray.length <= 1) {
      alert("현재 검색 결과에서 이동 가능한 다른 영상이 없습니다.");
      return;
    }

    // 현재 재생 중인 비디오 경로 확인
    const currentVideoPath = this.video.src
      ? allSubtitles.find((el) => el.classList.contains("highlight"))?.dataset
          .mediaPath || videoArray[0]
      : videoArray[0];

    // 현재 비디오 인덱스 찾기
    let currentIndex = videoArray.indexOf(currentVideoPath);
    if (currentIndex === -1) currentIndex = 0;

    // 새 인덱스 계산 (순환)
    let newIndex = currentIndex + direction;
    if (newIndex < 0) newIndex = videoArray.length - 1;
    if (newIndex >= videoArray.length) newIndex = 0;

    // 선택된 비디오의 첫 번째 자막 찾기
    const targetVideoPath = videoArray[newIndex];
    const firstSubtitleOfTarget = allSubtitles.find(
      (el) => el.dataset.mediaPath === targetVideoPath
    );

    if (firstSubtitleOfTarget) {
      // 반복 재생 중이면 중지
      if (this.isRepeating) {
        this._stopRepeat();
      }

      // 새 비디오의 자막으로 이동
      const index = allSubtitles.indexOf(firstSubtitleOfTarget);
      this.currentSubtitleIndex = index;
      this.playSingleSubtitle(firstSubtitleOfTarget);
      console.log(
        `${direction > 0 ? "다음" : "이전"} 영상으로 이동: ${targetVideoPath}`
      );
    } else {
      alert("선택한 영상의 자막을 찾을 수 없습니다.");
    }
  }

  // 반복 재생 중지
  _stopRepeat() {
    if (this.repeatHandler) {
      this.video.removeEventListener("timeupdate", this.repeatHandler);
      this.repeatHandler = null;
    }
    this.isRepeating = false;

    // 반복 버튼 시각적으로 비활성화
    const repeatBtn = document.getElementById("repeat-line-btn");
    if (repeatBtn) {
      repeatBtn.classList.remove("bg-blue-200");
      repeatBtn.classList.add("bg-gray-200");
    }
  }

  // Setup playback mode handler
  setupPlaybackHandler() {
    // Remove existing handlers if active
    if (this.isPlaybackHandlerActive) {
      this.video.removeEventListener("ended", this.handleVideoEnded);
    }

    // Always add the handler - the handler itself will determine what to do based on mode
    this.handleVideoEnded = this.handleVideoEnded.bind(this);
    this.video.addEventListener("ended", this.handleVideoEnded);
    this.isPlaybackHandlerActive = true;

    // 미디어 로드 이벤트 추가
    this.handleMediaLoaded = this.handleMediaLoaded.bind(this);
    this.video.addEventListener("loadeddata", this.handleMediaLoaded);

    // 에러 처리
    this.video.addEventListener("error", (e) => {
      this.debugLog(
        `비디오 에러 발생: ${this.video.error?.message || "알 수 없는 에러"}`
      );
    });

    this.debugLog(`재생 모드가 '${this.playbackMode}'로 설정됨`);
  }

  // 미디어 로드 완료 처리
  handleMediaLoaded() {
    this.debugLog("미디어 로드 완료");
    this.isMediaLoading = false;

    // 보류 중인 다음 재생이 있으면 처리
    if (this.pendingPlayNext) {
      this.pendingPlayNext = false;
      this.debugLog("보류 중이던 다음 자막 재생 시작");
      // 직접 다음 자막 재생 로직 호출 (ended 이벤트 트리거 대신)
      // 약간의 지연을 주어 모든 리소스가 준비되도록 함
      setTimeout(() => {
        this.processNextSubtitle();
      }, 100);
    }
  }

  // Handle video ended event based on playback mode
  handleVideoEnded() {
    // 이벤트 중복 처리 방지
    if (this.processedEndEvent) {
      this.debugLog("이미 처리 중인 ended 이벤트가 있어 무시함");
      return;
    }

    // 이벤트 처리 상태 표시
    this.processedEndEvent = true;
    setTimeout(() => {
      this.processedEndEvent = false;
    }, 300);

    // 반복 재생 중이면 처리하지 않음
    if (this.isRepeating) {
      this.debugLog("반복 재생 중이므로 종료 이벤트 무시");
      return;
    }

    // 미디어 로딩 중인 경우 처리 보류
    if (this.isMediaLoading) {
      this.debugLog("미디어 로딩 중이므로 다음 자막 재생을 보류");
      this.pendingPlayNext = true;
      return;
    }

    this.debugLog(`비디오 종료 이벤트 처리 (재생 모드: ${this.playbackMode})`);
    this.processNextSubtitle();
  }

  // 다음 자막으로 이동하는 로직 (재생 모드에 따라 처리)
  processNextSubtitle() {
    const visibleSubtitles = this.getVisibleSubtitles();

    if (!visibleSubtitles || !visibleSubtitles.length) {
      this.debugLog("표시된 자막이 없음");
      return;
    }

    this.debugLog(
      `현재 재생 모드: ${this.playbackMode}, 총 자막 수: ${visibleSubtitles.length}, 현재 인덱스: ${this.currentSubtitleIndex}`
    );

    switch (this.playbackMode) {
      case "search-results":
        this.playNextSearchResult(visibleSubtitles);
        break;
      case "sequential":
        this.playSequential(visibleSubtitles);
        break;
      case "random":
        this.playRandom(visibleSubtitles);
        break;
      case "repeat-one":
        // 현재 자막 다시 재생
        if (
          this.currentSubtitleIndex >= 0 &&
          this.currentSubtitleIndex < visibleSubtitles.length
        ) {
          this.playSingleSubtitle(visibleSubtitles[this.currentSubtitleIndex]);
        }
        break;
    }
  }

  // Helper: get all visible subtitle elements
  getVisibleSubtitles() {
    return Array.from(document.querySelectorAll(".subtitle-pair")).filter(
      (el) => el.style.display !== "none"
    );
  }

  // Play the next search result
  playNextSearchResult(visibleSubtitles) {
    if (!visibleSubtitles.length) return;

    // If we're at the end, loop back to the beginning
    if (
      this.currentSubtitleIndex >= visibleSubtitles.length - 1 ||
      this.currentSubtitleIndex < 0
    ) {
      this.currentSubtitleIndex = 0;
    } else {
      this.currentSubtitleIndex++;
    }

    this.debugLog(
      `다음 검색 결과 재생: ${this.currentSubtitleIndex + 1}/${
        visibleSubtitles.length
      }`
    );
    this.playSingleSubtitle(visibleSubtitles[this.currentSubtitleIndex]);
  }

  // Play sequentially through all subtitles
  playSequential(visibleSubtitles) {
    this.currentSubtitleIndex++;
    if (this.currentSubtitleIndex >= visibleSubtitles.length) {
      this.currentSubtitleIndex = 0; // Loop back to start
    }
    this.playSingleSubtitle(visibleSubtitles[this.currentSubtitleIndex]);
  }

  // Play a random subtitle
  playRandom(visibleSubtitles) {
    let randomIndex;
    // Avoid playing the same subtitle twice in a row if possible
    do {
      randomIndex = Math.floor(Math.random() * visibleSubtitles.length);
    } while (
      randomIndex === this.currentSubtitleIndex &&
      visibleSubtitles.length > 1
    );

    this.currentSubtitleIndex = randomIndex;
    this.playSingleSubtitle(visibleSubtitles[this.currentSubtitleIndex]);
  }

  // Highlight the currently playing subtitle
  highlightCurrentSubtitle(subtitleElement) {
    // Remove highlight from all subtitles
    document.querySelectorAll(".subtitle-pair").forEach((el) => {
      el.classList.remove("highlight");
    });

    // Add highlight to current subtitle
    subtitleElement.classList.add("highlight");

    // 현재 자막 표시 영역 업데이트
    this.updateCurrentSubtitleDisplay(subtitleElement);
  }

  // 현재 자막 표시 영역 업데이트
  updateCurrentSubtitleDisplay(subtitleElement) {
    const subtitleDisplay = document.getElementById("current-subtitle-display");
    const enElement = document.getElementById("current-subtitle-en");
    const koElement = document.getElementById("current-subtitle-ko");

    if (!subtitleDisplay || !enElement || !koElement) return;

    // 자막 텍스트 가져오기
    const enText = subtitleElement.querySelector(".en")?.textContent || "";
    const koText = subtitleElement.querySelector(".ko")?.textContent || "";

    // 애니메이션 효과를 위해 순차적으로 업데이트
    subtitleDisplay.classList.remove("active");

    setTimeout(() => {
      enElement.textContent = enText;
      koElement.textContent = koText;
      subtitleDisplay.classList.add("active");

      // 자막이 길면 스크롤 가능하도록 설정
      if (enText.length > 100 || koText.length > 100) {
        enElement.style.maxHeight = "60px";
        koElement.style.maxHeight = "60px";
        enElement.style.overflowY = "auto";
        koElement.style.overflowY = "auto";
      } else {
        enElement.style.maxHeight = "";
        koElement.style.maxHeight = "";
        enElement.style.overflowY = "";
        koElement.style.overflowY = "";
      }
    }, 200);
  }

  // Play a single subtitle
  playSingleSubtitle(subtitleElement) {
    if (!subtitleElement) {
      this.debugLog("재생할 자막 요소가 없음");
      return;
    }

    try {
      this.highlightCurrentSubtitle(subtitleElement);
      const mediaPath = subtitleElement.dataset.mediaPath;
      const streamingUrl = subtitleElement.dataset.streamingUrl;
      const startTime = parseFloat(subtitleElement.dataset.startTime) || 0;

      if (!streamingUrl) {
        this.debugLog("스트리밍 URL이 없어 재생 불가");
        return;
      }

      // Find next subtitle to determine end time
      let endTime;
      const allSubtitles = this.getVisibleSubtitles();
      const currentIndex = allSubtitles.indexOf(subtitleElement);

      if (currentIndex < allSubtitles.length - 1) {
        // 다음 자막이 같은 비디오인 경우에만 해당 시간을 종료 시간으로 설정
        const nextSubtitle = allSubtitles[currentIndex + 1];
        if (nextSubtitle.dataset.mediaPath === mediaPath) {
          endTime = parseFloat(nextSubtitle.dataset.startTime) - 0.05;
        } else {
          // 다른 비디오라면 이 비디오의 끝까지 재생 (또는 적절한 기본값)
          endTime = this.video.duration || startTime + 30; // 기본값 startTime + 30초
        }
      } else {
        // If this is the last subtitle, play until the end of the video (or reasonable default)
        endTime = this.video.duration || startTime + 30; // 기본값 startTime + 30초
      }

      this.debugLog(
        `자막 재생 시작 - Path: ${mediaPath}, Time: ${startTime} ~ ${endTime}`
      );

      // 미디어 URL 변경 검사 (다른 비디오로 전환 필요한지)
      const isSameVideo =
        this.video.src === new URL(streamingUrl, window.location.href).href;

      if (!isSameVideo) {
        this.debugLog(`새 비디오로 전환: ${streamingUrl}`);
        this.isMediaLoading = true; // 미디어 로딩 상태 설정
        this.hasAudioTrack = true; // 오디오 트랙 상태 초기화

        // 현재 재생 중인 모든 이벤트 핸들러 제거
        if (this.currentTimeUpdateHandler) {
          this.video.removeEventListener(
            "timeupdate",
            this.currentTimeUpdateHandler
          );
          this.currentTimeUpdateHandler = null;
        }

        // 새 소스 설정 전에 현재 음소거/볼륨 상태 기억
        const currentMuted = this.video.muted;
        const currentVolume = this.video.volume;

        // 새 소스 설정
        this.video.src = streamingUrl;

        // 이전 음소거/볼륨 상태 복원
        this.video.muted = currentMuted;
        this.video.volume = currentVolume;

        // 메타데이터 로드 완료 후 시간 설정 및 재생
        const metadataLoaded = () => {
          this.debugLog(
            `메타데이터 로드 완료 - 영상 길이: ${this.video.duration}초`
          );

          // 시작 시간 설정 및 구간 재생 설정
          this.video.currentTime = startTime;
          this.setupSegmentPlayback(startTime, endTime);

          // 오디오 준비 상태 확인
          this._ensureAudioEnabled();

          // 재생 시작 - 자동재생 정책 대응 (음소거 상태로 우선 시작)
          this.video.muted = true; // 일단 음소거로 시작
          this.video
            .play()
            .then(() => {
              // 자동 재생 성공 - 이제 오디오 복원 시도
              this.debugLog("음소거 상태로 재생 시작 성공");

              // 사용자가 이전에 음소거를 하지 않았다면 음소거 해제
              if (!currentMuted) {
                setTimeout(() => {
                  this.video.muted = false;
                  this.debugLog("음소거 해제 시도");

                  // 볼륨도 복원
                  if (currentVolume > 0) {
                    this.video.volume = currentVolume;
                  } else {
                    this.video.volume = 0.5; // 기본 볼륨
                  }
                }, 100);
              }

              // 오디오 트랙 감지 및 문제 확인
              setTimeout(() => this._detectAudioTrack(), 1000);
            })
            .catch((error) => {
              this.debugLog(
                `재생 시작 실패: ${error.message} - 사용자 상호작용이 필요할 수 있음`
              );
              this._showPlaybackErrorNotice();
            });

          // 이벤트 핸들러는 한 번만 실행
          this.video.removeEventListener("loadedmetadata", metadataLoaded);
        };

        this.video.addEventListener("loadedmetadata", metadataLoaded);
      } else {
        // 같은 비디오면 바로 시간 이동 및 재생
        this.debugLog(`같은 영상 내 시간 이동: ${startTime}초`);
        this.video.currentTime = startTime;
        this.setupSegmentPlayback(startTime, endTime);

        // 오디오 준비 상태 확인
        this._ensureAudioEnabled();

        this.video
          .play()
          .then(() => {
            this.debugLog("재생 시작됨");

            // 동일 비디오 내에서도 오디오 상태 확인
            setTimeout(() => this._detectAudioTrack(), 500);
          })
          .catch((error) => {
            this.debugLog(`재생 시작 실패: ${error.message}`);
            this._showPlaybackErrorNotice();
          });
      }

      // Update filename display
      const filename = mediaPath ? mediaPath.split("/").pop() : "";
      this.updateCurrentFilename(filename);

      // Scroll subtitle into view (부드럽게)
      subtitleElement.scrollIntoView({ behavior: "smooth", block: "center" });
    } catch (error) {
      this.debugLog(`자막 재생 중 오류: ${error.message}`);
    }
  }

  // 오디오가 활성화되어 있는지 확인하고 조치
  _ensureAudioEnabled() {
    // 볼륨이 0이면 기본값으로 설정
    if (this.video.volume <= 0) {
      this.video.volume = 0.5;
      this.debugLog("볼륨이 0이어서 기본값 0.5로 설정");
    }

    // localStorage에서 사용자 설정 확인
    const userWantsAudio = localStorage.getItem("videoPlayerMuted") !== "true";

    if (userWantsAudio) {
      // 사용자가 음소거를 원하지 않는다면 음소거 해제 시도
      if (this.video.muted) {
        // 바로 해제하면 자동재생 정책 때문에 문제가 생길 수 있으므로
        // 약간의 지연 후에 시도
        setTimeout(() => {
          this.video.muted = false;
          this.debugLog("사용자 설정에 따라 음소거 해제 시도");
        }, 100);
      }
    }
  }

  // 재생 실패 시 알림
  _showPlaybackErrorNotice() {
    // 이미 알림이 표시되어 있으면 중복 표시 방지
    if (document.getElementById("playback-error-notice")) return;

    const noticeEl = document.createElement("div");
    noticeEl.id = "playback-error-notice";
    noticeEl.className = "playback-error-notice";
    noticeEl.innerHTML = `
      <div class="error-notice-content">
        <p>⚠️ 비디오 재생을 시작할 수 없습니다.</p>
        <p class="small-text">브라우저의 자동 재생 정책으로 인한 문제일 수 있습니다.</p>
        <button class="start-playback-btn">수동으로 재생 시작</button>
        <button class="error-notice-close">닫기</button>
      </div>
    `;

    // 스타일 추가
    noticeEl.style.cssText = `
      position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
      background: rgba(0,0,0,0.8); color: white; padding: 15px 20px;
      border-radius: 5px; z-index: 1000; max-width: 90%; text-align: center;
    `;

    // 작은 텍스트 스타일
    const smallText = noticeEl.querySelector(".small-text");
    if (smallText) {
      smallText.style.cssText = `
        font-size: 0.8em; opacity: 0.8; margin-top: 5px;
      `;
    }

    // 버튼 스타일
    const buttons = noticeEl.querySelectorAll("button");
    buttons.forEach((btn) => {
      btn.style.cssText = `
        background: rgba(255,255,255,0.2); border: none; color: white;
        padding: 8px 12px; margin: 8px; border-radius: 4px; cursor: pointer;
      `;
    });

    noticeEl.querySelector(".start-playback-btn").style.backgroundColor =
      "#3182ce";

    // 플레이어 컨테이너에 추가
    const container = this.video.parentElement;
    if (container) {
      container.style.position = "relative";
      container.appendChild(noticeEl);

      // 재생 시작 버튼
      noticeEl
        .querySelector(".start-playback-btn")
        .addEventListener("click", () => {
          // 사용자 상호작용으로 재생 시도
          this.video
            .play()
            .then(() => {
              this.debugLog("사용자 상호작용으로 재생 시작됨");
              // 음소거 해제 시도
              setTimeout(() => {
                this.video.muted = false;
                this.debugLog("음소거 해제 시도");
              }, 100);
            })
            .catch((err) => {
              this.debugLog(`사용자 상호작용 후에도 재생 실패: ${err.message}`);
            });
          noticeEl.remove();
        });

      // 닫기 버튼
      noticeEl
        .querySelector(".error-notice-close")
        .addEventListener("click", () => {
          noticeEl.remove();
        });
    }
  }

  // Highlight the currently playing subtitle
  highlightCurrentSubtitle(subtitleElement) {
    // Remove highlight from all subtitles
    document.querySelectorAll(".subtitle-pair").forEach((el) => {
      el.classList.remove("highlight");
    });

    // Add highlight to current subtitle
    subtitleElement.classList.add("highlight");

    // 현재 자막 표시 영역 업데이트
    this.updateCurrentSubtitleDisplay(subtitleElement);
  }

  // 현재 자막 표시 영역 업데이트
  updateCurrentSubtitleDisplay(subtitleElement) {
    const subtitleDisplay = document.getElementById("current-subtitle-display");
    const enElement = document.getElementById("current-subtitle-en");
    const koElement = document.getElementById("current-subtitle-ko");

    if (!subtitleDisplay || !enElement || !koElement) return;

    // 자막 텍스트 가져오기
    const enText = subtitleElement.querySelector(".en")?.textContent || "";
    const koText = subtitleElement.querySelector(".ko")?.textContent || "";

    // 애니메이션 효과를 위해 순차적으로 업데이트
    subtitleDisplay.classList.remove("active");

    setTimeout(() => {
      enElement.textContent = enText;
      koElement.textContent = koText;
      subtitleDisplay.classList.add("active");

      // 자막이 길면 스크롤 가능하도록 설정
      if (enText.length > 100 || koText.length > 100) {
        enElement.style.maxHeight = "60px";
        koElement.style.maxHeight = "60px";
        enElement.style.overflowY = "auto";
        koElement.style.overflowY = "auto";
      } else {
        enElement.style.maxHeight = "";
        koElement.style.maxHeight = "";
        enElement.style.overflowY = "";
        koElement.style.overflowY = "";
      }
    }, 200);
  }

  // Setup handlers for subtitle clicks
  setupSubtitleClickHandlers() {
    document.querySelectorAll(".subtitle-pair").forEach((el, index) => {
      el.addEventListener("click", () => {
        // 클릭 시 반복 재생 중지
        if (this.isRepeating) {
          this._stopRepeat();
        }

        const mediaPath = el.dataset.mediaPath;
        const streamingUrl = el.dataset.streamingUrl;
        const startTime = parseFloat(el.dataset.startTime);

        this.currentSubtitleIndex = this.getVisibleSubtitles().indexOf(el); // 보이는 자막 중 인덱스로 업데이트

        if (streamingUrl && this.video.src !== streamingUrl) {
          this.video.src = streamingUrl;
        }
        this.video.currentTime = startTime;
        this.video.play();

        // 파일명만 추출 (경로 제외)
        const filename = mediaPath ? mediaPath.split("/").pop() : "";
        this.updateCurrentFilename(filename);

        // Add highlighting
        this.highlightCurrentSubtitle(el);
      });
    });
  }

  // 시간 업데이트에 따른 자막 업데이트 기능 추가
  setupSegmentPlayback(startTime, endTime) {
    // 기존 시간 업데이트 핸들러가 있다면 제거
    if (this.currentTimeUpdateHandler) {
      this.video.removeEventListener(
        "timeupdate",
        this.currentTimeUpdateHandler
      );
    }

    // 구간 재생 시간 업데이트 핸들러 추가
    this.currentTimeUpdateHandler = () => {
      if (this.video.currentTime >= endTime) {
        if (this.isRepeating) return; // 반복 재생 중이면 종료 처리 안 함

        this.video.pause();
        this.video.dispatchEvent(new Event("ended")); // 구간 종료 이벤트 발생
      }

      // 자막 시간과 일치하는 항목 강조 표시
      this.updateHighlightByCurrentTime();
    };

    this.video.addEventListener("timeupdate", this.currentTimeUpdateHandler);
  }

  // 현재 시간에 맞는 자막 항목 강조 표시
  updateHighlightByCurrentTime() {
    if (!this.video) return;

    const currentTime = this.video.currentTime;
    const currentVideoSrc = this.video.src;

    if (!currentVideoSrc) return;

    // 현재 미디어의 자막 찾기
    const allSubtitles = this.getVisibleSubtitles().filter((el) => {
      return (
        el.dataset.streamingUrl &&
        new URL(el.dataset.streamingUrl, window.location.href).href ===
          currentVideoSrc
      );
    });

    if (!allSubtitles.length) return;

    // 현재 시간과 가장 가까운 자막 찾기
    let closestSubtitle = null;
    let minTimeDiff = Infinity;

    for (let i = 0; i < allSubtitles.length; i++) {
      const subtitle = allSubtitles[i];
      const startTime = parseFloat(subtitle.dataset.startTime);
      const timeDiff = currentTime - startTime;

      // 현재 시간보다 이전이면서 가장 가까운 자막 찾기
      if (timeDiff >= 0 && timeDiff < minTimeDiff) {
        minTimeDiff = timeDiff;
        closestSubtitle = subtitle;
      }
    }

    // 다음 대사가 시작되기 전까지만 현재 자막으로 표시
    if (closestSubtitle) {
      const subtitleIndex = allSubtitles.indexOf(closestSubtitle);
      const nextSubtitle = allSubtitles[subtitleIndex + 1];

      // 다음 자막이 있고, 현재 시간이 다음 자막 시작 시간 이후라면 현재 자막으로 표시하지 않음
      if (nextSubtitle) {
        const nextStartTime = parseFloat(nextSubtitle.dataset.startTime);
        if (currentTime >= nextStartTime) {
          return;
        }
      }

      // 자막 강조 표시 (이미 강조된 자막이 아닐 때만)
      if (!closestSubtitle.classList.contains("highlight")) {
        this.highlightCurrentSubtitle(closestSubtitle);
      }
    }
  }

  // Initialize the video player component
  init() {
    // 오디오 컨트롤 추가
    this.addAudioControls();

    // Initialize subtitle click handlers
    this.setupSubtitleClickHandlers();

    // Initialize playback handler
    this.setupPlaybackHandler();

    // 빈 자막 표시 영역 초기화
    this.clearCurrentSubtitleDisplay();

    // Video.js 어댑터 초기화 (1단계 통합)
    this._initVideoJSAdapter();

    this.debugLog("비디오 플레이어 초기화 완료");
    return this;
  }

  // Video.js 어댑터 초기화
  _initVideoJSAdapter() {
    try {
      // VideoJSAdapter 클래스가 로드되어 있는지 확인
      if (window.VideoJSAdapter) {
        // 비디오JS 어댑터 설정
        this.videoJSAdapter = new VideoJSAdapter();
        // 초기화 및 기존 플레이어(this)와 연결
        this.videoJSAdapter.init().connectOriginalPlayer(this);
        this.debugLog("Video.js 어댑터 초기화 완료");
      } else {
        // Video.js 어댑터 스크립트 동적 로드
        this.debugLog("Video.js 어댑터 스크립트 로드 중...");

        // video-js 디렉토리에서 필요한 스크립트 로드
        this._loadScript("/static/js/components/video-js/video-player-init.js")
          .then(() =>
            this._loadScript("/static/js/components/video-js/video-adapter.js")
          )
          .then(() => {
            if (window.VideoJSAdapter) {
              this.videoJSAdapter = new VideoJSAdapter();
              this.videoJSAdapter.init().connectOriginalPlayer(this);
              this.debugLog("Video.js 어댑터 지연 초기화 완료");
            } else {
              this.debugLog("Video.js 어댑터 스크립트 로드 실패");
            }
          })
          .catch((err) => {
            this.debugLog(`Video.js 어댑터 초기화 오류: ${err.message}`);
          });
      }
    } catch (err) {
      this.debugLog(`Video.js 어댑터 초기화 중 예외 발생: ${err.message}`);
    }
  }

  // 스크립트 동적 로드 유틸리티
  _loadScript(src) {
    return new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = src;
      script.onload = () => resolve();
      script.onerror = (err) =>
        reject(new Error(`Failed to load script: ${src}`));
      document.head.appendChild(script);
    });
  }

  // 자막 표시 영역 초기화
  clearCurrentSubtitleDisplay() {
    const subtitleDisplay = document.getElementById("current-subtitle-display");
    const enElement = document.getElementById("current-subtitle-en");
    const koElement = document.getElementById("current-subtitle-ko");

    if (!subtitleDisplay || !enElement || !koElement) return;

    enElement.textContent = "재생을 시작하면 자막이 표시됩니다...";
    koElement.textContent = "";
    subtitleDisplay.classList.remove("active");
  }

  // Repeat current line N times
  repeatCurrentLine() {
    // 이미 반복 중이면 중지하고 리턴
    if (this.isRepeating) {
      this._stopRepeat();
      return;
    }

    const idx = this.getCurrentSubtitleIndex();
    const pairs = this.getVisibleSubtitles();
    const el = pairs[idx];
    if (!el) return;

    const start = parseFloat(el.dataset.startTime);
    const end =
      idx + 1 < pairs.length &&
      pairs[idx + 1].dataset.mediaPath === el.dataset.mediaPath
        ? parseFloat(pairs[idx + 1].dataset.startTime) - 0.05
        : start + 30; // 같은 비디오의 다음 자막이 없으면 기본 30초

    const repeatCount =
      parseInt(document.getElementById("repeat-count").value) || 2;
    let count = 0;

    // 반복 재생 버튼 활성화 표시
    const repeatBtn = document.getElementById("repeat-line-btn");
    if (repeatBtn) {
      repeatBtn.classList.remove("bg-gray-200");
      repeatBtn.classList.add("bg-blue-200");
    }

    this.isRepeating = true;

    // 먼저 재생 시작
    this.video.currentTime = start;
    this.video.play();
    this.highlightCurrentSubtitle(el);

    // 반복 재생 핸들러 설정
    this.repeatHandler = () => {
      if (this.video.currentTime >= end) {
        this.video.pause();
        count++;
        console.log(`문장 반복 ${count}/${repeatCount}`);

        if (count < repeatCount) {
          this.video.currentTime = start;
          this.video.play();
        } else {
          // 반복 횟수 채우면 반복 모드 종료
          this._stopRepeat();
        }
      }
    };

    this.video.addEventListener("timeupdate", this.repeatHandler);
  }

  // Update current filename display
  updateCurrentFilename(filename) {
    const el = document.getElementById("current-filename");
    if (el) el.textContent = filename ? `현재 파일: ${filename}` : "";
  }

  // 오디오 컨트롤 UI 추가
  addAudioControls() {
    // 기존 컨트롤 있으면 제거
    const existingControls = document.getElementById("custom-audio-controls");
    if (existingControls) existingControls.remove();

    // 비디오 요소가 있는지 확인
    if (!this.video) return;

    // 컨트롤 컨테이너 생성
    const controlsContainer = document.createElement("div");
    controlsContainer.id = "custom-audio-controls";
    controlsContainer.style.cssText = `
      display: flex; align-items: center; margin-top: 5px;
      padding: 8px; background: #f0f0f0; border-radius: 4px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    `;

    // 음소거 버튼
    const muteBtn = document.createElement("button");
    muteBtn.innerHTML = this.video.muted ? "🔇" : "🔊";
    muteBtn.title = this.video.muted ? "음소거 해제" : "음소거";
    muteBtn.style.cssText = `
      background: none; border: none; font-size: 20px; cursor: pointer;
      margin-right: 10px; padding: 5px; width: 36px; height: 36px;
      display: flex; align-items: center; justify-content: center;
      border-radius: 50%; transition: background-color 0.2s;
    `;

    // 호버 효과
    muteBtn.onmouseover = () => {
      muteBtn.style.backgroundColor = "#e0e0e0";
    };

    muteBtn.onmouseout = () => {
      muteBtn.style.backgroundColor = "transparent";
    };

    muteBtn.onclick = () => {
      this.video.muted = !this.video.muted;
      muteBtn.innerHTML = this.video.muted ? "🔇" : "🔊";
      muteBtn.title = this.video.muted ? "음소거 해제" : "음소거";

      // 음소거 해제 시 볼륨 확인하여 필요하면 조정
      if (!this.video.muted && this.video.volume <= 0) {
        this.video.volume = 0.5;
        this.debugLog("음소거 해제 시 볼륨이 0이어서 0.5로 조정");
      }

      // 사용자 설정 저장
      localStorage.setItem("videoPlayerMuted", this.video.muted.toString());
    };

    // 볼륨 슬라이더
    const volumeSlider = document.createElement("input");
    volumeSlider.type = "range";
    volumeSlider.min = "0";
    volumeSlider.max = "1";
    volumeSlider.step = "0.1";
    volumeSlider.value = this.video.volume;
    volumeSlider.style.cssText = `
      width: 120px; margin: 0 10px;
      accent-color: #3182ce;
    `;

    volumeSlider.oninput = () => {
      this.video.volume = volumeSlider.value;
      if (parseFloat(volumeSlider.value) > 0 && this.video.muted) {
        this.video.muted = false;
        muteBtn.innerHTML = "🔊";
        muteBtn.title = "음소거";
      } else if (parseFloat(volumeSlider.value) === 0) {
        this.video.muted = true;
        muteBtn.innerHTML = "🔇";
        muteBtn.title = "음소거 해제";
      }

      // 사용자 설정 저장
      localStorage.setItem("videoPlayerVolume", this.video.volume.toString());
      localStorage.setItem("videoPlayerMuted", this.video.muted.toString());
    };

    // 현재 볼륨 표시
    const volumeDisplay = document.createElement("span");
    volumeDisplay.textContent = Math.round(this.video.volume * 100) + "%";
    volumeDisplay.style.cssText = `
      font-size: 12px; color: #555; width: 40px;
    `;

    volumeSlider.addEventListener("input", () => {
      volumeDisplay.textContent = Math.round(volumeSlider.value * 100) + "%";
    });

    // 볼륨 변경 시 업데이트
    this.video.addEventListener("volumechange", () => {
      volumeSlider.value = this.video.volume;
      volumeDisplay.textContent = Math.round(this.video.volume * 100) + "%";
      muteBtn.innerHTML = this.video.muted ? "🔇" : "🔊";
      muteBtn.title = this.video.muted ? "음소거 해제" : "음소거";
    });

    // 문제 해결 버튼 (도움말)
    const helpBtn = document.createElement("button");
    helpBtn.innerHTML = "?";
    helpBtn.title = "오디오 문제 해결";
    helpBtn.style.cssText = `
      background: #f0f0f0; border: 1px solid #ddd; border-radius: 50%;
      width: 24px; height: 24px; font-size: 14px; font-weight: bold;
      display: flex; align-items: center; justify-content: center;
      margin-left: 10px; cursor: pointer;
    `;

    helpBtn.onclick = () => {
      this._showAudioTroubleshootingGuide();
    };

    // 요소를 컨테이너에 추가
    controlsContainer.appendChild(muteBtn);
    controlsContainer.appendChild(volumeSlider);
    controlsContainer.appendChild(volumeDisplay);
    controlsContainer.appendChild(helpBtn);

    // 비디오 플레이어 아래에 컨트롤 추가
    const playerContainer = this.video.parentElement;
    if (playerContainer) {
      playerContainer.insertBefore(controlsContainer, this.video.nextSibling);
    }
  }

  // 오디오 문제 해결 가이드 표시
  _showAudioTroubleshootingGuide() {
    // 이미 가이드가 표시되어 있으면 중복 표시 방지
    if (document.getElementById("audio-guide")) return;

    const guideEl = document.createElement("div");
    guideEl.id = "audio-guide";
    guideEl.className = "audio-guide";
    guideEl.innerHTML = `
      <div class="guide-content">
        <h3>🔊 오디오 문제 해결</h3>
        <hr>
        <ol>
          <li>브라우저 볼륨이 음소거 상태가 아닌지 확인하세요.</li>
          <li>시스템 볼륨이 켜져 있는지 확인하세요.</li>
          <li>일부 미디어 파일은 오디오 트랙이 없거나 특별한 코덱을 사용할 수 있습니다.</li>
          <li>브라우저 캐시를 지우고 페이지를 새로고침 해보세요.</li>
          <li>다른 미디어 파일을 재생해보고 오디오가 작동하는지 확인하세요.</li>
        </ol>
        <div class="buttons">
          <button class="check-media-btn">미디어 정보 확인</button>
          <button class="close-guide-btn">닫기</button>
        </div>
      </div>
    `;

    // 스타일 추가
    guideEl.style.cssText = `
      position: fixed; top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(0,0,0,0.7); z-index: 2000;
      display: flex; align-items: center; justify-content: center;
    `;

    const content = guideEl.querySelector(".guide-content");
    content.style.cssText = `
      background: white; padding: 20px;
      border-radius: 8px; max-width: 500px; width: 90%;
      box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    `;

    const h3 = guideEl.querySelector("h3");
    h3.style.cssText = `
      font-size: 18px; margin: 0 0 10px 0; color: #333;
    `;

    const hr = guideEl.querySelector("hr");
    hr.style.cssText = `
      border: 0; border-top: 1px solid #eee; margin: 15px 0;
    `;

    const ol = guideEl.querySelector("ol");
    ol.style.cssText = `
      margin: 15px 0; padding-left: 20px;
    `;

    const li = guideEl.querySelectorAll("li");
    li.forEach((item) => {
      item.style.cssText = `
        margin-bottom: 10px; color: #555;
      `;
    });

    const buttons = guideEl.querySelector(".buttons");
    buttons.style.cssText = `
      display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px;
    `;

    const checkBtn = guideEl.querySelector(".check-media-btn");
    checkBtn.style.cssText = `
      background: #3182ce; color: white; border: none;
      padding: 8px 15px; border-radius: 4px; cursor: pointer;
    `;

    const closeBtn = guideEl.querySelector(".close-guide-btn");
    closeBtn.style.cssText = `
      background: #e2e8f0; color: #4a5568; border: none;
      padding: 8px 15px; border-radius: 4px; cursor: pointer;
    `;

    // 문서에 추가
    document.body.appendChild(guideEl);

    // 미디어 정보 확인 버튼
    checkBtn.addEventListener("click", () => {
      this._showMediaInfo();
      guideEl.remove();
    });

    // 닫기 버튼
    closeBtn.addEventListener("click", () => {
      guideEl.remove();
    });

    // 배경 클릭 시 닫기
    guideEl.addEventListener("click", (e) => {
      if (e.target === guideEl) {
        guideEl.remove();
      }
    });
  }

  // 미디어 정보 표시
  _showMediaInfo() {
    if (!this.video || !this.video.src) {
      alert("현재 재생 중인 미디어가 없습니다.");
      return;
    }

    const videoInfo = {
      src: this.video.src,
      currentTime: this.video.currentTime.toFixed(2) + "초",
      duration: this.video.duration
        ? this.video.duration.toFixed(2) + "초"
        : "알 수 없음",
      muted: this.video.muted ? "음소거 됨" : "음소거 아님",
      volume: Math.round(this.video.volume * 100) + "%",
      paused: this.video.paused ? "일시 정지됨" : "재생 중",
      readyState: this.video.readyState,
      videoWidth: this.video.videoWidth + "px",
      videoHeight: this.video.videoHeight + "px",
    };

    let infoText = "미디어 정보:\n\n";
    for (const [key, value] of Object.entries(videoInfo)) {
      infoText += `${key}: ${value}\n`;
    }

    alert(infoText);
  }
}

// Export the VideoPlayer class
window.VideoPlayer = VideoPlayer;
