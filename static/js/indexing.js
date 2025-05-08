/**
 * 인덱싱 관련 자바스크립트 기능
 * htmx와 함께 사용되는 최소한의 JS 기능만 포함
 */

/**
 * htmx 이벤트 리스너 설정
 */
document.addEventListener("DOMContentLoaded", function () {
  // 토글 버튼 설정
  setupToggleButton();

  // htmx 이벤트: 인덱싱 작업 시작 시 트리거
  document.body.addEventListener("htmx:afterRequest", function (event) {
    // 인덱싱 API 호출 이후 이벤트 처리
    if (
      event.detail.path &&
      (event.detail.path === "/api/index" ||
        event.detail.path === "/api/stop_indexing" ||
        event.detail.path === "/api/pause_indexing" ||
        event.detail.path === "/api/resume_indexing")
    ) {
      console.log("인덱싱 요청 처리됨:", event.detail.path);

      // 인덱싱 상태 업데이트 영역이 있으면 HTMX를 통해 새로고침 트리거
      const statusElement = document.getElementById("indexing-status");
      if (statusElement) {
        // htmx를 통해 인덱싱 상태를 새로고침 (데이터 속성이 설정된 경우)
        if (statusElement.getAttribute("hx-get")) {
          htmx.trigger(statusElement, "load");
        }
      }

      // 토글 버튼 상태 업데이트
      updateToggleButton(event.detail.path);
    }
  });

  // 인덱싱 상태 영역 변경 감지
  document.body.addEventListener("htmx:afterSwap", function (event) {
    if (event.detail.target.id === "indexing-status") {
      // 상태 카드를 확인하여 현재 인덱싱 상태 파악
      const statusCard = event.detail.target.querySelector(
        ".indexing-status-card"
      );
      if (statusCard) {
        // 일시정지 상태인지 확인
        const isPaused = statusCard.classList.contains("status-paused");
        const isRunning = statusCard.classList.contains("status-running");

        // 인덱싱 상태에 따라 토글 버튼 업데이트
        updateToggleButtonState(isPaused, isRunning);
      }
    }
  });
});

/**
 * 토글 버튼 설정 및 이벤트 리스너 등록
 */
function setupToggleButton() {
  const toggleBtn = document.getElementById("toggle-indexing-btn");
  if (!toggleBtn) return;

  toggleBtn.addEventListener("click", function (event) {
    // 현재 상태 확인 (일시정지 또는 재개 상태)
    const isPaused =
      toggleBtn.classList.contains("bg-green-600") ||
      toggleBtn.classList.contains("bg-green-700");

    // 상태에 따라 API 엔드포인트 변경
    if (isPaused) {
      // 현재 일시정지 상태 -> 재개 API 호출
      toggleBtn.setAttribute("hx-post", "/api/resume_indexing");
    } else {
      // 현재 실행 중 -> 일시정지 API 호출
      toggleBtn.setAttribute("hx-post", "/api/pause_indexing");
    }
  });
}

/**
 * API 호출 이후 토글 버튼 업데이트
 * @param {string} path - API 엔드포인트 경로
 */
function updateToggleButton(path) {
  if (path === "/api/pause_indexing") {
    // 일시정지 API가 호출되었으면 재개 버튼으로 변경
    updateToggleButtonState(true, false);
  } else if (path === "/api/resume_indexing") {
    // 재개 API가 호출되었으면 일시정지 버튼으로 변경
    updateToggleButtonState(false, true);
  } else if (path === "/api/stop_indexing") {
    // 중지 API가 호출되었으면 비활성화
    updateToggleButtonState(false, false);
  }
}

/**
 * 토글 버튼 상태 업데이트
 * @param {boolean} isPaused - 일시정지 상태인지 여부
 * @param {boolean} isRunning - 실행 중인지 여부
 */
function updateToggleButtonState(isPaused, isRunning) {
  const toggleBtn = document.getElementById("toggle-indexing-btn");
  const toggleText = document.getElementById("toggle-indexing-text");
  const toggleIcon = document.getElementById("toggle-indexing-icon");

  if (!toggleBtn || !toggleText || !toggleIcon) return;

  // 버튼 비활성화/활성화
  toggleBtn.disabled = !isRunning && !isPaused;

  if (!isRunning && !isPaused) {
    // 인덱싱이 실행 중이지 않고 일시정지 상태도 아니면 버튼 비활성화
    toggleBtn.classList.add("opacity-50", "cursor-not-allowed");
    toggleBtn.classList.remove(
      "bg-yellow-500",
      "hover:bg-yellow-600",
      "bg-green-600",
      "hover:bg-green-700"
    );
    toggleBtn.classList.add("bg-gray-500");
    toggleText.textContent = "정지됨";
    return;
  } else {
    // 버튼 활성화
    toggleBtn.classList.remove(
      "opacity-50",
      "cursor-not-allowed",
      "bg-gray-500"
    );
  }

  if (isPaused) {
    // 일시정지 상태 -> 재개 버튼으로 표시
    toggleBtn.setAttribute("hx-post", "/api/resume_indexing");
    toggleText.textContent = toggleBtn.dataset.resumeText;
    toggleIcon.innerHTML = toggleBtn.dataset.resumeIcon;

    // 색상 변경
    toggleBtn.className = toggleBtn.className.replace(
      /bg-\w+-\d+ hover:bg-\w+-\d+/g,
      toggleBtn.dataset.resumeColor
    );
  } else {
    // 실행 중 -> 일시정지 버튼으로 표시
    toggleBtn.setAttribute("hx-post", "/api/pause_indexing");
    toggleText.textContent = toggleBtn.dataset.pauseText;
    toggleIcon.innerHTML = toggleBtn.dataset.pauseIcon;

    // 색상 변경
    toggleBtn.className = toggleBtn.className.replace(
      /bg-\w+-\d+ hover:bg-\w+-\d+/g,
      toggleBtn.dataset.pauseColor
    );
  }
}

/**
 * 페이지가 언로드(이탈)될 때 진행 중인 인덱싱이 있다면 경고 표시
 * (이 기능은 htmx로 대체하기 어려우므로 JS로 유지)
 */
window.addEventListener("beforeunload", function (e) {
  // 인덱싱 상태 확인
  const statusElement = document.getElementById("indexing-status");
  if (statusElement && statusElement.querySelector(".status-running")) {
    // 인덱싱 진행 중일 때 경고 표시
    const message =
      "인덱싱이 진행 중입니다. 페이지를 나가면 백그라운드에서 계속 실행됩니다.";
    e.returnValue = message;
    return message;
  }
});
