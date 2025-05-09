document.addEventListener("DOMContentLoaded", async function () {
  console.log("search.js: DOM 로드됨");

  // 전역 변수
  let searchCache = [];
  let initializationAttempts = 0;
  const MAX_ATTEMPTS = 3;

  // 모듈 인스턴스
  let videoPlayer = null;
  let tagManager = null;
  let bookmarkManager = null;
  let searchResultsView = null;

  // 초기화 함수 정의
  async function initializePage() {
    try {
      initializationAttempts++;
      console.log(
        `페이지 초기화 시도 ${initializationAttempts}/${MAX_ATTEMPTS}`
      );

      // Ensure the search-page class is applied - 여러 곳에서 적용하도록 함
      if (!document.body.classList.contains("search-page")) {
        document.body.classList.add("search-page");
        console.log("search-page 클래스 추가됨 (initializePage)");
      }

      // 모듈 로드
      try {
        await Promise.all([loadModules(), initVideoPlayer()]);
        console.log("모든 모듈 로드 및 초기화 완료");
      } catch (moduleError) {
        console.error("모듈 로드 중 오류:", moduleError);
        throw new Error(`모듈 로드 실패: ${moduleError.message}`);
      }

      // UI 요소 초기화 - 사이드바 관련 코드 제거
      if (window.setupUIElements) window.setupUIElements();
      if (window.setupLayoutElements) window.setupLayoutElements();

      // 페이지 기능 초기화
      initializeSearchFeatures();

      // 결과 렌더링 이벤트 핸들러 등록
      document.addEventListener(
        "searchResultsRendered",
        handleSearchResultsRendered
      );

      // 초기화 완료 후 콘텐츠 표시 - 항상 호출되도록 수정
      if (window.showContent) {
        console.log("초기화 완료, 콘텐츠 표시 함수 호출");
        window.showContent();
      } else {
        console.warn("showContent 함수를 찾을 수 없습니다.");
        // showContent 함수가 없어도 로딩 화면은 숨기기
        const loadingElement = document.getElementById("content-loading");
        if (loadingElement) {
          loadingElement.classList.add("hidden");
          setTimeout(() => {
            loadingElement.style.display = "none";
          }, 500);
        }
      }

      return true; // 성공적으로 초기화됨
    } catch (error) {
      console.error(
        `페이지 초기화 중 오류 발생(시도 ${initializationAttempts}/${MAX_ATTEMPTS}):`,
        error
      );

      // 최대 시도 횟수에 도달하면 로딩 화면 제거하고 오류 메시지 표시
      if (initializationAttempts >= MAX_ATTEMPTS) {
        console.error(
          "최대 초기화 시도 횟수에 도달했습니다. 사용자에게 오류 표시"
        );

        // 로딩 화면 숨기기
        const loadingElement = document.getElementById("content-loading");
        if (loadingElement) {
          loadingElement.classList.add("hidden");
          setTimeout(() => {
            loadingElement.style.display = "none";
          }, 500);
        }

        // 오류 메시지 표시 - 더 자세한 오류 정보 포함
        const contentElement = document.getElementById("search-fullscreen");
        if (contentElement) {
          contentElement.classList.add("initialized");
          contentElement.innerHTML = `
            <div class="text-center p-8">
              <div class="text-red-500 mb-4 text-xl">초기화 중 오류가 발생했습니다</div>
              <div class="text-gray-600 mb-4">오류 내용: ${error.message}</div>
              <pre class="text-xs text-left bg-gray-100 p-2 rounded overflow-auto max-h-40">${
                error.stack || "스택 정보 없음"
              }</pre>
              <button onclick="location.reload()" class="mt-4 px-4 py-2 bg-blue-500 text-white rounded">새로고침</button>
            </div>
          `;
        }

        return false; // 초기화 실패
      }

      // 재시도
      console.log(`${1000 * initializationAttempts}ms 후 다시 시도합니다...`);
      setTimeout(initializePage, 1000 * initializationAttempts);
      return false;
    }
  }

  // 초기화 시작
  await initializePage();

  /**
   * 컴포넌트 모듈 로드 및 초기화
   */
  async function loadModules() {
    try {
      console.log("컴포넌트 모듈 로드 시작");

      // 상대 경로로 모듈 임포트 (절대 경로에서 수정)
      const TagManagerModule = await import(
        "./components/tag-manager.js"
      ).catch((e) => {
        console.error("TagManager 모듈 로드 실패:", e);
        throw e;
      });

      const BookmarkManagerModule = await import(
        "./components/bookmark-manager.js"
      ).catch((e) => {
        console.error("BookmarkManager 모듈 로드 실패:", e);
        throw e;
      });

      const SearchResultsViewModule = await import(
        "./components/search-results-view.js"
      ).catch((e) => {
        console.error("SearchResultsView 모듈 로드 실패:", e);
        throw e;
      });

      console.log("모듈 로드 완료, 인스턴스 초기화");

      // 모듈 인스턴스 생성 및 초기화
      try {
        tagManager = new TagManagerModule.TagManager();
        bookmarkManager = new BookmarkManagerModule.BookmarkManager();
        searchResultsView = new SearchResultsViewModule.SearchResultsView();

        // 모듈 초기화
        tagManager.init();
        bookmarkManager.init();
        searchResultsView.init();

        console.log("모듈 초기화 완료");
      } catch (initError) {
        console.error("모듈 인스턴스 초기화 오류:", initError);
        throw initError;
      }
    } catch (error) {
      console.error("모듈 로드 오류:", error);
      throw error;
    }
  }

  /**
   * 검색 결과 렌더링 완료 이벤트 핸들러
   */
  function handleSearchResultsRendered(event) {
    console.log("검색 결과 렌더링 완료됨:", event.detail);

    // 모듈의 이벤트 핸들러 설정
    if (tagManager) tagManager.setupTagButtons();
    if (bookmarkManager) bookmarkManager.setupBookmarkButtons();

    // 자막 클릭 이벤트 재설정
    if (videoPlayer) videoPlayer.setupSubtitleClickHandlers();
  }

  /**
   * UI 요소 업데이트 함수
   * 화면 변경 또는 상태 변경 시 호출
   */
  function updateUIElements() {
    console.log("UI 요소 업데이트");

    // 자막 클릭 이벤트 핸들러 재설정
    if (videoPlayer) {
      console.log("자막 클릭 핸들러 재설정");
      videoPlayer.setupSubtitleClickHandlers();
    }

    // 태그와 북마크 버튼 이벤트 재설정
    if (tagManager) tagManager.setupTagButtons();
    if (bookmarkManager) bookmarkManager.setupBookmarkButtons();
  }

  /**
   * 비디오 플레이어 초기화 함수
   */
  async function initVideoPlayer() {
    try {
      console.log("비디오 플레이어 초기화 시작");

      // Video.js가 이미 로드되어 있는지 확인
      if (!window.videojs) {
        console.warn("Video.js가 로드되지 않았습니다. 동적으로 로드합니다.");
        // Video.js 라이브러리 로드
        if (window.loadVideoJSLibraries) {
          await window.loadVideoJSLibraries();
        } else {
          // 기본 로드 방식
          await new Promise((resolve) => {
            console.log("기본 방식으로 Video.js 로드 중...");
            // 이미 로드되어 있는지 확인
            if (document.querySelector('script[src*="video.js"]')) {
              console.log("Video.js 스크립트가 이미 로드되어 있습니다.");
              resolve();
              return;
            }

            const script = document.createElement("script");
            script.src =
              "https://cdn.jsdelivr.net/npm/video.js@8/dist/video.min.js";
            script.onload = () => {
              console.log("Video.js 라이브러리 로드 완료");
              resolve();
            };
            script.onerror = (err) => {
              console.error("Video.js 라이브러리 로드 실패:", err);
              resolve(); // 실패해도 진행
            };
            document.head.appendChild(script);
          });
        }
      } else {
        console.log("Video.js가 이미 로드되어 있습니다.");
      }

      // VideoPlayer 모듈 임포트 - 상대 경로로 수정
      try {
        const VideoPlayerModule = await import(
          "./components/video-components/video-player.js"
        );
        const VideoPlayer =
          VideoPlayerModule.default || VideoPlayerModule.VideoPlayer;

        // 비디오 플레이어 초기화
        videoPlayer = new VideoPlayer();
        await videoPlayer.init();
        console.log("비디오 플레이어 초기화 완료");

        // 전역 변수에도 설정 (기존 코드 호환성)
        window.videoPlayer = videoPlayer;

        // 자막 클릭 핸들러 설정
        videoPlayer.setupSubtitleClickHandlers();
      } catch (importError) {
        console.error("VideoPlayer 모듈 임포트 또는 초기화 오류:", importError);
        throw importError;
      }
    } catch (error) {
      console.error("비디오 플레이어 초기화 오류:", error);
      throw error;
    }
  }

  /**
   * 검색 기능 초기화
   */
  function initializeSearchFeatures() {
  // 검색 폼 제출 이벤트 처리
    const searchForm = document.getElementById("search-form");
    if (searchForm) {
      searchForm.addEventListener("submit", function (e) {
      e.preventDefault();

        const query = document.getElementById("search-input").value.trim();
      if (query === "") {
        return;
      }

        console.log("검색 폼 제출:", query);

      // 검색어에서 언어 감지
        const languageSelector =
          document.querySelector('input[name="search_lang"]:checked')?.value ||
          "en";

        // 검색 방식(LIKE 또는 FTS) 확인
        const searchMethod =
          document.querySelector('input[name="search-method"]:checked')
            ?.value || "like";

      // 정규식 검색 여부 확인
        const useRegex = document.getElementById("use-regex")?.checked || false;

      // 정확히 일치 여부 확인
        const exactMatch =
          document.getElementById("exact-match")?.checked || false;

      // 태그 검색 여부 확인
        const searchInTags =
          document.getElementById("search-tags")?.checked || false;

      // 검색 실행
      searchSubtitles(
        query,
        languageSelector,
        useRegex,
        exactMatch,
          searchInTags,
          searchMethod
      );
    });
    } else {
      console.warn("검색 폼을 찾을 수 없습니다.");
  }

  // 자막 검색 함수
  function searchSubtitles(
    query,
    languageSelector,
    useRegex,
    exactMatch,
      searchInTags,
      searchMethod
    ) {
      // 검색 UI 업데이트
      if (searchResultsView) {
        searchResultsView.updateUIForLoading(true);
      }

    // 검색 파라미터 구성
      const params = new URLSearchParams();
      params.append("query", query);

      if (languageSelector) {
        params.append("lang", languageSelector);
      }

      // 검색 방식 파라미터 추가
      if (searchMethod) {
        params.append("search_method", searchMethod);
      }

      // 미디어 유형 필터 추가
      const mediaFilter = document.getElementById("media-filter")?.value;
      if (mediaFilter && mediaFilter !== "all") {
        params.append("media_type", mediaFilter);
      }

      // 정렬 필터 추가
      const sortFilter = document.getElementById("sort-filter")?.value;
      if (sortFilter && sortFilter !== "relevance") {
        params.append("sort", sortFilter);
      }

      // 정규식 및 정확히 일치 옵션 추가
      if (useRegex) params.append("regex", "true");
      if (exactMatch) params.append("exact", "true");
      if (searchInTags) params.append("search_tags", "true");

      // 검색 API 호출 - SearchAPI 사용
      try {
        if (window.SearchAPI && typeof window.SearchAPI.search === "function") {
          // search-api.js의 SearchAPI 객체 사용
          console.log("검색 API 호출: SearchAPI.search 사용");

          // 파라미터를 객체로 변환
          const searchOptions = {};
          params.forEach((value, key) => {
            searchOptions[key] = value;
          });

          window.SearchAPI.search(query, searchOptions)
          .then((data) => {
              // 검색 결과 캐시 및 표시
              searchCache = data.results || [];

              // 검색 UI 업데이트
              if (searchResultsView) {
                searchResultsView.updateUIForLoading(false);
                searchResultsView.displayResults(searchCache);
            }
          })
          .catch((error) => {
              console.error("검색 API 호출 오류:", error);
              if (searchResultsView) {
                searchResultsView.updateUIForLoading(false);
                searchResultsView.displayError(error.message);
              }
            });
        } else {
          // SearchAPI가 없을 경우 기본 fetch 사용 (폴백)
          console.warn("SearchAPI를 찾을 수 없습니다. 기본 fetch 사용");

          fetch(`/api/search?${params.toString()}`)
            .then((response) => {
              if (!response.ok) {
                throw new Error(
                  `검색 요청 실패: ${response.status} ${response.statusText}`
                );
              }
          return response.json();
        })
        .then((data) => {
              if (!data.success) {
                throw new Error(
                  data.error || "검색 처리 중 오류가 발생했습니다."
                );
              }

              // 검색 결과 캐시 및 표시
              searchCache = data.results || [];

              // 검색 UI 업데이트
              if (searchResultsView) {
                searchResultsView.updateUIForLoading(false);
                searchResultsView.displayResults(searchCache);
          }
        })
        .catch((error) => {
              console.error("검색 API 호출 오류:", error);
              if (searchResultsView) {
                searchResultsView.updateUIForLoading(false);
                searchResultsView.displayError(error.message);
              }
            });
        }
      } catch (error) {
        console.error("검색 실행 중 예외 발생:", error);
        if (searchResultsView) {
          searchResultsView.updateUIForLoading(false);
          searchResultsView.displayError(
            `검색 중 예외가 발생했습니다: ${error.message}`
          );
        }
      }
    }

    // 제출 버튼이 페이지 입장시 포커스 받지 않도록 함
    document.querySelector('#search-form button[type="submit"]')?.blur();
  }
});
