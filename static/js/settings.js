/**
 * 설정 페이지 관련 자바스크립트 기능
 */

/**
 * 페이지 초기화 시 이벤트 리스너 설정
 */
document.addEventListener("DOMContentLoaded", function () {
  // 폼 제출 전에 체크박스 값을 hidden 필드에 설정
  document.querySelector("form").addEventListener("submit", function (e) {
    collectMediaExtensions();
  });

  // 모달 닫기 버튼 이벤트 설정
  const cancelBtn = document.getElementById("cancel-modal-btn");
  if (cancelBtn) {
    cancelBtn.addEventListener("click", function () {
      document
        .getElementById("directory-browser-modal")
        .classList.add("hidden");
    });
  }

  // 디렉토리 브라우저 모달 초기화
  initDirectoryBrowser();

  // 디렉토리 브라우저 모달 컨텐츠에 이벤트 위임 설정
  const modalContent = document.getElementById(
    "directory-browser-modal-content"
  );
  if (modalContent) {
    modalContent.addEventListener("click", function (e) {
      // 디렉토리 항목 클릭 처리 - 항목 자체 또는 그 내부 요소를 클릭했을 때도 동작하도록 수정
      const directoryItem = e.target.closest(".directory-item");
      if (directoryItem) {
        const path = directoryItem.dataset.path;
        if (path) {
          loadDirectoryContents(path);
          return; // 이벤트 처리 완료
        }
      }

      // 상위 디렉토리 버튼 클릭 처리 - 버튼 자체 또는 그 내부 요소를 클릭했을 때도 동작하도록 수정
      const parentDirBtn = e.target.closest(".parent-dir-btn");
      if (parentDirBtn) {
        const path = parentDirBtn.dataset.parent;
        if (path) {
          loadDirectoryContents(path);
          return; // 이벤트 처리 완료
        }
      }

      // 라디오 버튼 변경 시 선택된 경로 저장
      if (
        e.target &&
        e.target.type === "radio" &&
        e.target.name === "selected_directory"
      ) {
        // 선택된 디렉토리 경로를 임시 저장
        window.selectedDirectoryPath = e.target.value;
      }
    });
  }

  // 찾아보기 버튼 클릭 시 디렉토리 브라우저 모달 표시 및 내용 로드
  const browseButton = document.getElementById("browse-button");
  if (browseButton) {
    browseButton.addEventListener("click", function (e) {
      // HTMX가 로드하기 전에 수동으로 로드 시작
      loadDirectoryContents();
    });
  }

  // DB 초기화 모달 이벤트 설정
  setupDBResetModal();

  // 루트 디렉토리 변경 감지 모달 초기화
  setupDirChangeModal();
});

/**
 * DB 초기화 모달 설정
 */
function setupDBResetModal() {
  const confirmResetBtn = document.getElementById("confirm-reset-btn");
  const cancelResetBtn = document.getElementById("cancel-reset-btn");
  const resetModal = document.getElementById("reset-db-modal");

  if (confirmResetBtn && cancelResetBtn && resetModal) {
    // 확인 버튼 클릭 시 API 호출
    confirmResetBtn.addEventListener("click", function () {
      // 모달 닫기
      resetModal.classList.add("hidden");

      // DB 초기화 및 재인덱싱 API 호출
      fetch("/api/index", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          incremental: false,
          reset_db: true,
        }),
      })
        .then((response) => {
          if (!response.ok) {
            throw new Error("API 요청 실패");
          }
          return response.json();
        })
        .then((data) => {
          // 성공 시 인덱싱 프로세스 페이지로 이동
          window.location.href = "/indexing-process";
        })
        .catch((error) => {
          console.error("Error:", error);
          alert("DB 초기화 및 인덱싱 시작 중 오류가 발생했습니다.");
        });
    });

    // 취소 버튼 클릭 시 모달 닫기
    cancelResetBtn.addEventListener("click", function () {
      resetModal.classList.add("hidden");
    });
  }
}

/**
 * 루트 디렉토리 변경 감지 모달 설정
 */
function setupDirChangeModal() {
  const dirChangeModal = document.getElementById("root-dir-change-modal");
  if (dirChangeModal && !dirChangeModal.classList.contains("hidden")) {
    // 모달이 이미 표시되고 있으므로 아무 작업도 하지 않음
  }
}

/**
 * DB 초기화 확인 모달 표시
 */
function confirmResetDatabase() {
  const resetModal = document.getElementById("reset-db-modal");
  if (resetModal) {
    resetModal.classList.remove("hidden");
  }
}

/**
 * 디렉토리 브라우저 초기화
 */
function initDirectoryBrowser() {
  // 디렉토리 선택 버튼 클릭 이벤트
  const browseBtn = document.getElementById("browse-button");
  if (browseBtn) {
    // HTMX 속성으로 처리되는 클릭 이벤트 외에 추가 처리
    browseBtn.addEventListener("click", function () {
      // 모달 표시
      document
        .getElementById("directory-browser-modal")
        .classList.remove("hidden");
    });
  }

  // 사용 중인 경로 버튼 클릭 이벤트
  const useCurrentDirBtn = document.getElementById("use-current-dir-btn");
  if (useCurrentDirBtn) {
    useCurrentDirBtn.addEventListener("click", saveSelectedDirectory);
  }
}

/**
 * 디렉토리 내용 로드
 * @param {string} path - 로드할 디렉토리 경로 (없으면 루트 디렉토리 로드)
 */
function loadDirectoryContents(path = null) {
  // 로딩 상태 표시
  const content = document.getElementById("directory-browser-modal-content");
  if (content) {
    content.innerHTML =
      '<div class="text-center py-4"><div class="spinner"></div><p class="mt-2 text-gray-500">디렉토리 로딩 중...</p></div>';
  }

  // API 요청 경로 생성
  let url = "/api/browse";
  if (path) {
    url += `?path=${encodeURIComponent(path)}`;
  }

  // 디렉토리 내용 로드
  fetch(url)
    .then((response) => {
      if (!response.ok) {
        throw new Error("Directory loading failed");
      }
      return response.text();
    })
    .then((html) => {
      if (content) {
        content.innerHTML = html;

        // 로드 후 라디오 버튼에 이벤트 리스너 추가
        const radioButtons = content.querySelectorAll(
          'input[name="selected_directory"]'
        );
        radioButtons.forEach((radio) => {
          radio.addEventListener("change", function () {
            window.selectedDirectoryPath = this.value;
          });
        });
      }
    })
    .catch((error) => {
      console.error("Error loading directory contents:", error);
      if (content) {
        content.innerHTML =
          '<div class="text-red-500 p-4">디렉토리 로딩 중 오류가 발생했습니다.</div>';
      }
    });
}

/**
 * 체크된 미디어 확장자를 수집하여 hidden 필드에 설정
 */
function collectMediaExtensions() {
  // 체크된 모든 확장자 체크박스 수집
  const checkboxes = document.querySelectorAll(
    'input[name="media_extensions"]:checked'
  );
  const extensions = Array.from(checkboxes).map((cb) => cb.value);

  // hidden 필드에 값 설정
  document.getElementById("media_extensions_hidden").value =
    extensions.join(",");
}

/**
 * 설정을 기본값으로 복원
 */
function resetSettings() {
  if (confirm("모든 설정을 기본값으로 복원하시겠습니까?")) {
    fetch("/api/reset-settings", {
      method: "POST",
    })
      .then((response) => response.json())
      .then((data) => {
        alert("설정이 기본값으로 복원되었습니다. 페이지를 새로고침합니다.");
        window.location.reload();
      })
      .catch((error) => {
        console.error("Error:", error);
        alert("설정 복원 중 오류가 발생했습니다.");
      });
  }
}

/**
 * 디렉토리 선택 모달에서 선택한 디렉토리를 입력 필드에 설정
 */
function saveSelectedDirectory() {
  // 선택된 라디오 버튼 찾기
  const selectedDir = document.querySelector(
    'input[name="selected_directory"]:checked'
  );

  // 글로벌 변수에 저장된 경로 또는 라디오 버튼에서 선택된 경로 사용
  if (selectedDir || window.selectedDirectoryPath) {
    const pathToUse =
      window.selectedDirectoryPath || (selectedDir ? selectedDir.value : null);

    if (pathToUse) {
      document.getElementById("root_dir").value = pathToUse;
      document
        .getElementById("directory-browser-modal")
        .classList.add("hidden");
      return;
    }
  }

  // 경로 선택이 안되었을 때 현재 표시된 경로에서 처리
  const currentPathElement = document.querySelector(".current-path");
  if (currentPathElement) {
    const currentPath = currentPathElement.dataset.path;
    if (currentPath) {
      document.getElementById("root_dir").value = currentPath;
      document
        .getElementById("directory-browser-modal")
        .classList.add("hidden");
      return;
    }
  }

  // 그 외 경우 알림 표시
  alert("디렉토리를 선택해주세요.");
}

/**
 * 설정 저장 후 바로 인덱싱 시작
 */
function saveAndStartIndexing() {
  // 미디어 확장자 수집
  collectMediaExtensions();

  // 폼 데이터 수집
  const formData = new FormData(document.querySelector("form"));

  // 설정 저장 요청
  fetch("/settings", {
    method: "POST",
    body: formData,
  })
    .then((response) => {
      if (response.ok) {
        // 설정 저장 성공 후 인덱싱 시작
        startFullIndexing();
      } else {
        alert("설정 저장에 실패했습니다.");
      }
    })
    .catch((error) => {
      console.error("Error:", error);
      alert("설정 저장 중 오류가 발생했습니다.");
    });
}

/**
 * 전체 인덱싱 시작
 */
function startFullIndexing() {
  if (confirm("기존 인덱싱이 초기화됩니다. 전체 인덱싱을 시작하시겠습니까?")) {
    // 전체 인덱싱 API 호출
    fetch("/api/index", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ incremental: false }),
    })
      .then((response) => response.json())
      .then((data) => {
        // 성공 시 인덱싱 프로세스 페이지로 이동
        window.location.href = "/indexing-process";
      })
      .catch((error) => {
        console.error("Error:", error);
        alert("인덱싱 시작 중 오류가 발생했습니다.");
      });
  }
}
