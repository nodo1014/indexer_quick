// 검색 페이지 전용 클래스 추가
document.body.classList.add("search-page");

// 콘텐츠 표시 함수 - 간소화된 버전
window.showContent = function () {
  // 로딩 화면 숨기기
  const loadingElement = document.getElementById("content-loading");
  if (loadingElement) {
    loadingElement.classList.add("hidden");
    setTimeout(() => {
      loadingElement.style.display = "none";
    }, 500);
  }

  // 검색 페이지 클래스가 없으면 추가
  if (!document.body.classList.contains("search-page")) {
    document.body.classList.add("search-page");
  }

  // 기본 검색 방식 로드
  loadDefaultSearchMethod();

  console.log("콘텐츠 표시 완료");
};

// 기본 검색 방식 로드 함수
function loadDefaultSearchMethod() {
  // 서버에서 기본 검색 방식 설정 가져오기
  fetch("/api/config?key=default_search_method")
    .then((response) => {
      if (!response.ok) {
        throw new Error("설정 로드 실패");
      }
      return response.json();
    })
    .then((data) => {
      // 검색 방식 라디오 버튼에 적용
      const method = data.value || "like";
      const radioButton = document.querySelector(
        `input[name="search-method"][value="${method}"]`
      );
      if (radioButton) {
        radioButton.checked = true;
        console.log(`기본 검색 방식 설정: ${method}`);
      }
    })
    .catch((error) => {
      console.warn("기본 검색 방식 로드 실패:", error);
      // 오류 시 기본값 'like' 적용
      const likeRadio = document.querySelector(
        'input[name="search-method"][value="like"]'
      );
      if (likeRadio) likeRadio.checked = true;
    });
}

// Video.js 동적 로드 함수
window.loadVideoJSLibraries = function () {
  return new Promise((resolve) => {
    if (window.videojs) {
      resolve();
      return;
    }
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = "https://cdn.jsdelivr.net/npm/video.js@8/dist/video-js.min.css";
    document.head.appendChild(link);

    const script = document.createElement("script");
    script.src = "https://cdn.jsdelivr.net/npm/video.js@8/dist/video.min.js";
    script.onload = () => resolve();
    script.onerror = () => resolve();
    document.head.appendChild(script);
  });
};

// UI 요소 초기화
window.setupUIElements = function () {
  document
    .getElementById("close-tooltip")
    ?.addEventListener("click", function () {
      document.getElementById("feature-tooltip").style.display = "none";
      localStorage.setItem("hideFeatureTooltip", "true");
    });
  if (localStorage.getItem("hideFeatureTooltip") === "true") {
    const tooltip = document.getElementById("feature-tooltip");
    if (tooltip) tooltip.style.display = "none";
  }
};

// UI 요소 추가 초기화 함수
window.setupLayoutElements = function () {
  // 화면 크기 변경 시 처리할 함수
  window.handleResize = function () {
    // 화면 크기에 따른 레이아웃 조정
    console.log("화면 크기 변경 감지");
  };

  // 화면 크기 변경 이벤트 리스너
  window.addEventListener("resize", window.handleResize);
};

// 검색 결과 이벤트 발생 함수
function dispatchSearchResultsEvent(results) {
  const event = new CustomEvent("searchResultsRendered", {
    detail: { count: results.length },
  });
  document.dispatchEvent(event);
  console.log(`검색 결과 렌더링 이벤트 발생: 결과 ${results.length}개`);
}
