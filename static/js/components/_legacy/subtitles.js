/**
 * Video.js 자막 기능 확장
 * 2단계: 기존 자막 시스템을 Video.js와 통합
 */

class VideoJSSubtitles {
  constructor(vjsPlayer) {
    this.vjsPlayer = vjsPlayer; // VideoJS 플레이어 인스턴스
    this.player = vjsPlayer?.player; // Video.js 플레이어

    this.currentSubtitleId = null; // 현재 활성 자막 ID
    this.activeSubtitles = []; // 활성화된 자막 목록
    this.subtitleNodes = new Map(); // 자막 노드 맵 (ID -> DOM 요소)

    this.settingsApplied = false; // 자막 스타일 설정 적용 여부

    // 기본 자막 스타일
    this.subtitleStyle = {
      fontSize: localStorage.getItem("subtitleFontSize") || "1.8em",
      fontColor: localStorage.getItem("subtitleFontColor") || "#FFFFFF",
      backgroundColor:
        localStorage.getItem("subtitleBgColor") || "rgba(0, 0, 0, 0.5)",
      fontFamily:
        localStorage.getItem("subtitleFontFamily") || "Arial, sans-serif",
    };

    // 초기화
    if (this.player) {
      this._setupSubtitleSystem();
      this._initTextTrackDisplayStyles();
    }
  }

  /**
   * 자막 시스템 초기화
   */
  _setupSubtitleSystem() {
    // TextTrack 디스플레이 커스터마이징을 위한 이벤트 리스너
    this.player.on("loadedmetadata", () => {
      this.applySubtitleStyles();
    });

    // 자막 변경 감지
    this.player.on("texttrackchange", () => {
      this._updateActiveSubtitles();
    });

    // 자막 활성화 여부 전환
    this.player.on("useractive", () => {
      this._checkSubtitleVisibility();
    });

    this.player.on("userinactive", () => {
      this._checkSubtitleVisibility();
    });

    // 커스텀 이벤트: 특정 구간 재생 완료 시 처리
    this.player.on("segmentended", () => {
      this._clearSubtitleDisplay();
    });
  }

  /**
   * 자막 스타일 적용
   */
  applySubtitleStyles() {
    if (this.settingsApplied) return;

    const textTrackDisplay = this.player.getChild("textTrackDisplay");
    if (!textTrackDisplay) return;

    const textTrackEl = textTrackDisplay.el();
    if (!textTrackEl) return;

    // 자막 컨테이너에 스타일 적용
    const captionsDisplay = textTrackEl.querySelector(
      ".vjs-text-track-display"
    );
    if (captionsDisplay) {
      captionsDisplay.style.fontSize = this.subtitleStyle.fontSize;
      captionsDisplay.style.fontFamily = this.subtitleStyle.fontFamily;

      // 동적 스타일 시트 추가
      const styleId = "vjs-custom-caption-styles";
      let styleEl = document.getElementById(styleId);

      if (!styleEl) {
        styleEl = document.createElement("style");
        styleEl.id = styleId;
        document.head.appendChild(styleEl);
      }

      // 자막 스타일 CSS 규칙 설정
      styleEl.textContent = `
        .video-js .vjs-text-track-cue > div {
          background-color: ${this.subtitleStyle.backgroundColor} !important;
          color: ${this.subtitleStyle.fontColor} !important;
          font-family: ${this.subtitleStyle.fontFamily} !important;
          padding: 0.2em 0.5em !important;
          border-radius: 2px !important;
        }
      `;

      this.settingsApplied = true;
    }
  }

  /**
   * TextTrack 디스플레이 스타일 초기화
   */
  _initTextTrackDisplayStyles() {
    // TextTrackDisplay 스타일 초기화는 플레이어가 준비된 후에 실행
    if (!this.player.textTracks) return;

    // 스타일 조정을 위한 기다림
    setTimeout(() => {
      this.applySubtitleStyles();
    }, 500);
  }

  /**
   * 자막 가시성 확인 및 조정
   */
  _checkSubtitleVisibility() {
    const textTrackDisplay = this.player.getChild("textTrackDisplay");
    if (!textTrackDisplay) return;

    // 사용자가 비디오와 상호작용 중이 아닐 때도 자막은 계속 표시되도록 설정
    textTrackDisplay.show();
  }

  /**
   * 현재 활성화된 자막 목록 업데이트
   */
  _updateActiveSubtitles() {
    if (!this.player.textTracks) return;

    const activeTracks = [];
    const textTracks = this.player.textTracks();

    // 모든 텍스트 트랙을 순회하며 활성화된 것 찾기
    for (let i = 0; i < textTracks.length; i++) {
      const track = textTracks[i];
      if (track.mode === "showing") {
        activeTracks.push(track);
      }
    }

    this.activeSubtitles = activeTracks;
  }

  /**
   * 자막 표시 영역 초기화
   */
  _clearSubtitleDisplay() {
    this.currentSubtitleId = null;

    // 가상 자막 클리어 이벤트 발생 (자체 이벤트)
    if (this.player) {
      this.player.trigger("subtitlesclear");
    }
  }

  /**
   * 외부 자막 (VTT, SRT 등) 추가
   * @param {string} url - 자막 파일 URL
   * @param {string} label - 자막 라벨 (예: "한국어", "영어")
   * @param {string} language - 자막 언어 코드 (예: "ko", "en")
   * @param {boolean} [isDefault=false] - 기본 자막으로 설정 여부
   */
  addExternalSubtitle(url, label, language, isDefault = false) {
    if (!this.player || !url) return;

    const existingTracks = this.player.remoteTextTracks();

    // 이미 존재하는 같은 언어의 자막이 있는지 확인
    for (let i = 0; i < existingTracks.length; i++) {
      if (existingTracks[i].language === language) {
        // 기존 자막 제거
        this.player.removeRemoteTextTrack(existingTracks[i]);
        break;
      }
    }

    // 새 자막 트랙 추가
    const track = {
      kind: "subtitles",
      src: url,
      srclang: language,
      label: label,
      default: isDefault,
    };

    const addedTrack = this.player.addRemoteTextTrack(track, true);

    // 기본 자막인 경우 자동 활성화
    if (isDefault) {
      setTimeout(() => {
        addedTrack.track.mode = "showing";
      }, 100);
    }

    return addedTrack;
  }

  /**
   * 내부 자막 데이터를 WebVTT로 변환하여 추가
   * @param {Array} subtitleData - 자막 데이터 [{start, end, text}]
   * @param {string} label - 자막 라벨
   * @param {string} language - 자막 언어 코드
   * @param {boolean} [isDefault=false] - 기본 자막으로 설정 여부
   */
  addInlineSubtitles(subtitleData, label, language, isDefault = false) {
    if (!this.player || !Array.isArray(subtitleData) || !subtitleData.length)
      return;

    // WebVTT 형식으로 변환
    const vttContent = this._convertToWebVTT(subtitleData);

    // Blob URL 생성
    const blob = new Blob([vttContent], { type: "text/vtt" });
    const vttUrl = URL.createObjectURL(blob);

    // 외부 자막 추가 함수 호출
    return this.addExternalSubtitle(vttUrl, label, language, isDefault);
  }

  /**
   * 자막 데이터 WebVTT 형식으로 변환
   * @param {Array} subtitleData - 자막 데이터 배열
   * @returns {string} WebVTT 형식 문자열
   */
  _convertToWebVTT(subtitleData) {
    // WebVTT 헤더
    let vtt = "WEBVTT\n\n";

    // 각 자막 항목 처리
    subtitleData.forEach((sub, index) => {
      // 시작/종료 시간 포맷팅 (hh:mm:ss.ms)
      const startTime = this._formatVttTime(sub.start);
      const endTime = this._formatVttTime(sub.end);

      vtt += `${index + 1}\n`;
      vtt += `${startTime} --> ${endTime}\n`;
      vtt += `${sub.text}\n\n`;
    });

    return vtt;
  }

  /**
   * 초 단위 시간을 WebVTT 시간 형식으로 변환
   * @param {number} seconds - 초 단위 시간
   * @returns {string} WebVTT 형식 시간 문자열 (hh:mm:ss.ms)
   */
  _formatVttTime(seconds) {
    const date = new Date(seconds * 1000);
    const hours = date.getUTCHours().toString().padStart(2, "0");
    const minutes = date.getUTCMinutes().toString().padStart(2, "0");
    const secs = date.getUTCSeconds().toString().padStart(2, "0");
    const ms = date.getUTCMilliseconds().toString().padStart(3, "0");

    return `${hours}:${minutes}:${secs}.${ms}`;
  }

  /**
   * 검색된 자막들을 자동으로 추출하여 Video.js에 추가
   * 페이지에 표시된 자막 요소들을 분석하여 자막 트랙 생성
   */
  extractAndAddVisibleSubtitles() {
    if (!this.player) return;

    // 페이지에 표시된 모든 자막 요소 수집
    const subtitleElements = Array.from(
      document.querySelectorAll(".subtitle-pair")
    ).filter((el) => el.style.display !== "none");

    if (!subtitleElements.length) return;

    // 비디오별로 자막 그룹화
    const subtitlesByVideo = {};

    subtitleElements.forEach((el) => {
      const mediaPath = el.dataset.mediaPath;
      const streamingUrl = el.dataset.streamingUrl;

      // 스트리밍 URL이 없으면 건너뛰기
      if (!streamingUrl) return;

      // 비디오 키 생성 (mediaPath 또는 streamingUrl)
      const videoKey = mediaPath || streamingUrl;

      if (!subtitlesByVideo[videoKey]) {
        subtitlesByVideo[videoKey] = {
          streamingUrl,
          subtitles: [],
        };
      }

      // 자막 텍스트 및 시간 추출
      const enText = el.querySelector(".en")?.textContent?.trim() || "";
      const koText = el.querySelector(".ko")?.textContent?.trim() || "";
      const startTime = parseFloat(el.dataset.startTime) || 0;
      const endTime = parseFloat(el.dataset.endTime) || startTime + 5; // 기본값 5초

      // 유효한 자막만 추가
      if ((enText || koText) && startTime < endTime) {
        subtitlesByVideo[videoKey].subtitles.push({
          start: startTime,
          end: endTime,
          enText,
          koText,
        });
      }
    });

    // 현재 재생 중인 비디오 URL
    const currentVideoUrl = this.player.src();

    // 현재 비디오에 해당하는 자막만 추출
    for (const [key, data] of Object.entries(subtitlesByVideo)) {
      if (
        new URL(data.streamingUrl, window.location.href).href ===
          currentVideoUrl &&
        data.subtitles.length > 0
      ) {
        console.log(
          `[VideoJSSubtitles] 현재 비디오(${key})에 대한 자막 ${data.subtitles.length}개 추가`
        );

        // 영어 자막 추가 (있는 경우)
        const enSubtitles = data.subtitles
          .filter((sub) => sub.enText)
          .map((sub) => ({
            start: sub.start,
            end: sub.end,
            text: sub.enText,
          }));

        if (enSubtitles.length > 0) {
          this.addInlineSubtitles(enSubtitles, "English", "en", true);
        }

        // 한국어 자막 추가 (있는 경우)
        const koSubtitles = data.subtitles
          .filter((sub) => sub.koText)
          .map((sub) => ({
            start: sub.start,
            end: sub.end,
            text: sub.koText,
          }));

        if (koSubtitles.length > 0) {
          this.addInlineSubtitles(koSubtitles, "한국어", "ko", false);
        }

        break; // 현재 비디오에 대한 자막만 추출
      }
    }
  }

  /**
   * 자막 스타일 설정
   * @param {Object} style - 자막 스타일 객체
   */
  setSubtitleStyle(style = {}) {
    // 스타일 업데이트
    this.subtitleStyle = {
      ...this.subtitleStyle,
      ...style,
    };

    // localStorage에 저장
    for (const [key, value] of Object.entries(this.subtitleStyle)) {
      localStorage.setItem(
        `subtitle${key.charAt(0).toUpperCase() + key.slice(1)}`,
        value
      );
    }

    // 스타일 재적용
    this.settingsApplied = false;
    this.applySubtitleStyles();

    return this.subtitleStyle;
  }

  /**
   * 자막 활성화/비활성화 (모든 자막)
   * @param {boolean} enable - 활성화 여부
   */
  toggleSubtitles(enable) {
    if (!this.player || !this.player.textTracks) return;

    const tracks = this.player.textTracks();
    for (let i = 0; i < tracks.length; i++) {
      tracks[i].mode = enable ? "showing" : "disabled";
    }
  }

  /**
   * 특정 언어의 자막만 활성화
   * @param {string} language - 언어 코드 (예: "en", "ko")
   */
  enableLanguage(language) {
    if (!this.player || !this.player.textTracks) return;

    const tracks = this.player.textTracks();
    for (let i = 0; i < tracks.length; i++) {
      if (tracks[i].language === language) {
        tracks[i].mode = "showing";
      } else {
        tracks[i].mode = "disabled";
      }
    }
  }

  /**
   * 자막 컨트롤 UI 추가
   */
  addSubtitleControls() {
    // 이미 자막 컨트롤이 있는지 확인
    const existingControls = document.getElementById("vjs-subtitle-controls");
    if (existingControls) return;

    // 컨트롤 바가 있는지 확인
    const playerContainer = this.player?.el();
    if (!playerContainer) return;

    // 컨트롤 컨테이너 생성
    const controlsContainer = document.createElement("div");
    controlsContainer.id = "vjs-subtitle-controls";
    controlsContainer.classList.add("vjs-subtitle-controls");
    controlsContainer.style.cssText = `
      display: flex; align-items: center; margin: 10px 0;
      padding: 8px; background: #f0f0f0; border-radius: 4px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    `;

    // 자막 켜기/끄기 버튼
    const toggleBtn = document.createElement("button");
    toggleBtn.innerHTML = "자막 켜기";
    toggleBtn.className = "vjs-subtitle-toggle-btn";
    toggleBtn.style.cssText = `
      background: #e2e8f0; color: #4a5568; border: none;
      padding: 6px 12px; border-radius: 4px; cursor: pointer;
      margin-right: 10px;
    `;

    // 언어 선택 드롭다운
    const langSelect = document.createElement("select");
    langSelect.className = "vjs-subtitle-language-select";
    langSelect.style.cssText = `
      background: white; color: #4a5568; border: 1px solid #cbd5e0;
      padding: 5px 8px; border-radius: 4px; cursor: pointer;
      margin-right: 10px;
    `;

    // 기본 옵션
    langSelect.innerHTML = `
      <option value="">언어 선택</option>
      <option value="en">English</option>
      <option value="ko">한국어</option>
    `;

    // 자막 크기 조절 버튼
    const fontSizeContainer = document.createElement("div");
    fontSizeContainer.style.cssText = `
      display: flex; align-items: center; margin-left: 10px;
    `;

    const fontSizeLabel = document.createElement("span");
    fontSizeLabel.textContent = "자막 크기:";
    fontSizeLabel.style.marginRight = "5px";

    const decreaseBtn = document.createElement("button");
    decreaseBtn.innerHTML = "작게";
    decreaseBtn.className = "vjs-subtitle-size-btn";
    decreaseBtn.style.cssText = `
      background: #e2e8f0; color: #4a5568; border: none;
      padding: 4px 8px; border-radius: 4px; cursor: pointer;
      margin-right: 5px; font-size: 12px;
    `;

    const increaseBtn = document.createElement("button");
    increaseBtn.innerHTML = "크게";
    increaseBtn.className = "vjs-subtitle-size-btn";
    increaseBtn.style.cssText = `
      background: #e2e8f0; color: #4a5568; border: none;
      padding: 4px 8px; border-radius: 4px; cursor: pointer;
      font-size: 12px;
    `;

    // 요소 추가
    fontSizeContainer.appendChild(fontSizeLabel);
    fontSizeContainer.appendChild(decreaseBtn);
    fontSizeContainer.appendChild(increaseBtn);

    controlsContainer.appendChild(toggleBtn);
    controlsContainer.appendChild(langSelect);
    controlsContainer.appendChild(fontSizeContainer);

    // 이벤트 핸들러 추가
    let subtitlesEnabled = true; // 기본적으로 자막 켜짐

    toggleBtn.addEventListener("click", () => {
      subtitlesEnabled = !subtitlesEnabled;
      this.toggleSubtitles(subtitlesEnabled);
      toggleBtn.innerHTML = subtitlesEnabled ? "자막 끄기" : "자막 켜기";
    });

    langSelect.addEventListener("change", () => {
      if (langSelect.value) {
        subtitlesEnabled = true;
        this.enableLanguage(langSelect.value);
        toggleBtn.innerHTML = "자막 끄기";
      }
    });

    decreaseBtn.addEventListener("click", () => {
      // 현재 폰트 크기 추출
      let currentSize = parseFloat(this.subtitleStyle.fontSize);
      const unit = this.subtitleStyle.fontSize.replace(/[0-9.]/g, "");

      // 폰트 크기 감소 (최소 0.5em)
      currentSize = Math.max(0.5, currentSize - 0.2);

      this.setSubtitleStyle({
        fontSize: `${currentSize}${unit}`,
      });
    });

    increaseBtn.addEventListener("click", () => {
      // 현재 폰트 크기 추출
      let currentSize = parseFloat(this.subtitleStyle.fontSize);
      const unit = this.subtitleStyle.fontSize.replace(/[0-9.]/g, "");

      // 폰트 크기 증가 (최대 3em)
      currentSize = Math.min(3, currentSize + 0.2);

      this.setSubtitleStyle({
        fontSize: `${currentSize}${unit}`,
      });
    });

    // 비디오 플레이어 아래에 컨트롤 추가
    const videoContainer =
      this.player.el().closest(".video-container") ||
      playerContainer.parentElement;

    if (videoContainer) {
      const afterElement =
        document.getElementById("videojs-switch") || this.player.el();
      videoContainer.insertBefore(controlsContainer, afterElement.nextSibling);
    }

    // TextTrack 변경 이벤트 구독
    this.player.on("texttrackchange", () => {
      this._updateSubtitleControlsState(toggleBtn, langSelect);
    });

    // 초기 상태 설정
    this._updateSubtitleControlsState(toggleBtn, langSelect);
  }

  /**
   * 자막 컨트롤 UI 상태 업데이트
   */
  _updateSubtitleControlsState(toggleBtn, langSelect) {
    if (!this.player || !this.player.textTracks) return;

    let anyTrackShowing = false;
    let currentLanguage = "";

    const tracks = this.player.textTracks();
    for (let i = 0; i < tracks.length; i++) {
      if (tracks[i].mode === "showing") {
        anyTrackShowing = true;
        currentLanguage = tracks[i].language;
        break;
      }
    }

    // 토글 버튼 상태 업데이트
    if (toggleBtn) {
      toggleBtn.innerHTML = anyTrackShowing ? "자막 끄기" : "자막 켜기";
    }

    // 언어 선택 드롭다운 상태 업데이트
    if (langSelect && currentLanguage) {
      langSelect.value = currentLanguage;
    }
  }
}

// 전역에 노출해서 다른 모듈에서 사용 가능하도록 함
window.VideoJSSubtitles = VideoJSSubtitles;
