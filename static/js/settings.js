/**
 * 설정 페이지 관련 자바스크립트 기능
 */

/**
 * 페이지 초기화 시 이벤트 리스너 설정
 */
document.addEventListener("DOMContentLoaded", function () {
  // 폼 제출 전에 체크박스 값을 hidden 필드에 설정
  const settingsForm = document.querySelector("form");
  if (settingsForm) {
    settingsForm.addEventListener("submit", function (e) {
      console.log("폼 제출 이벤트 발생");
      // 폼 제출 전에 미디어 확장자 수집
      collectMediaExtensions();
      console.log("미디어 확장자 수집 완료:", document.getElementById("media_extensions_hidden").value);
      
      // 폼 데이터 로깅
      const formData = new FormData(this);
      for (let [key, value] of formData.entries()) {
        console.log(`${key}: ${value}`);
      }
      
      // 폼 제출을 명시적으로 허용
      return true;
    });
  } else {
    console.error("설정 폼을 찾을 수 없습니다.");
  }

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
  
  // 설정 저장 버튼에 명시적 이벤트 리스너 추가
  const saveSettingsBtn = document.getElementById('save-settings-btn');
  if (saveSettingsBtn) {
    saveSettingsBtn.addEventListener('click', function(e) {
      console.log('설정 저장 버튼 클릭됨');
      // 버튼 클릭 시 폼 제출이 자동으로 트리거되므로 추가 코드 필요 없음
    });
  }

  // 메뉴 관리 기능 초기화
  initMenuManagement();
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

  // 선택 버튼 클릭 이벤트
  const selectDirBtn = document.getElementById("select-dir-btn");
  if (selectDirBtn) {
    selectDirBtn.addEventListener("click", saveSelectedDirectory);
  }

  // 취소 버튼 클릭 이벤트
  const cancelModalBtn = document.getElementById("cancel-modal-btn");
  if (cancelModalBtn) {
    cancelModalBtn.addEventListener("click", function () {
      document
        .getElementById("directory-browser-modal")
        .classList.add("hidden");
    });
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
    // 현재 경로 저장
    window.currentDirectoryPath = path;
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

        // 현재 경로 정보 가져오기
        const currentPathElement = content.querySelector(".current-path");
        if (currentPathElement && currentPathElement.dataset.path) {
          window.currentDirectoryPath = currentPathElement.dataset.path;
        }
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

  console.log("수집된 미디어 확장자:", extensions);
  
  // hidden 필드에 값 설정
  const hiddenField = document.getElementById("media_extensions_hidden");
  if (hiddenField) {
    hiddenField.value = extensions.join(",");
    console.log("hidden 필드 값 설정됨:", hiddenField.value);
  } else {
    console.error("media_extensions_hidden 필드를 찾을 수 없습니다");
  }
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
 * 선택된 디렉토리 경로 저장
 */
function saveSelectedDirectory() {
  // 1. 라디오 버튼에서 선택된 경로 확인
  let path = window.selectedDirectoryPath;

  // 2. 라디오 버튼 선택이 없으면 현재 표시된 디렉토리 사용
  if (!path) {
    path = window.currentDirectoryPath;
  }

  // 3. 그래도 없으면 현재 페이지에 표시된 경로 찾기
  if (!path) {
    const modalContent = document.getElementById(
      "directory-browser-modal-content"
    );
    if (modalContent) {
      const currentPathElement = modalContent.querySelector(".current-path");
      if (currentPathElement && currentPathElement.dataset.path) {
        path = currentPathElement.dataset.path;
      }

      // 선택된 라디오 버튼 확인
      const selectedRadio = modalContent.querySelector(
        'input[name="selected_directory"]:checked'
      );
      if (selectedRadio) {
        path = selectedRadio.value;
      }
    }
  }

  // 4. 선택된 경로가 있으면 입력 필드에 설정
  if (path) {
    // 모달 제목을 확인하여 어떤 필드를 업데이트할지 결정
    const modalTitleElement = document.getElementById(
      "directory-browser-modal-title"
    );
    const isDBPathSelection =
      modalTitleElement &&
      modalTitleElement.textContent.includes("DB 파일 경로 선택");

    if (isDBPathSelection) {
      // DB 파일 경로 선택인 경우
      const dbPathInput = document.getElementById("db_path");
      if (dbPathInput) {
        dbPathInput.value = path;
      }
    } else {
      // 일반 디렉토리 선택인 경우
      const mediaDirInput = document.getElementById("media_dir");
      if (mediaDirInput) {
        mediaDirInput.value = path;
      }
    }

    // 모달 닫기
    const modal = document.getElementById("directory-browser-modal");
    if (modal) {
      modal.classList.add("hidden");
    }

    // 설정값 자동 저장을 위해 폼 제출 (선택적)
    const saveBtn = document.querySelector('button[type="submit"]');
    if (saveBtn) {
      // 저장 버튼 강조 효과
      saveBtn.classList.add("animate-pulse");
      setTimeout(() => {
        saveBtn.classList.remove("animate-pulse");
      }, 2000);
    }

    return true;
  }

  // 경로를 찾지 못한 경우 안내 메시지
  alert("디렉토리를 선택해주세요.");
  return false;
}

/**
 * 설정 저장 및 인덱싱 시작
 */
function saveAndStartIndexing() {
  // 폼 데이터 수집
  const form = document.querySelector("form");
  const formData = new FormData(form);
  const directory = formData.get("media_dir");

  // 폼 제출하여 설정 저장
  fetch("/settings", {
    method: "POST",
    body: formData,
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error("설정 저장에 실패했습니다.");
      }

      // 설정 저장 성공 후 인덱싱 시작
      return fetch("/api/index", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          incremental: true,
        }),
      });
    })
    .then((response) => {
      if (!response.ok) {
        throw new Error("인덱싱 시작에 실패했습니다.");
      }
      return response.json();
    })
    .then((data) => {
      // 인덱싱 진행 페이지로 이동
      window.location.href = "/indexing-process";
    })
    .catch((error) => {
      console.error("Error:", error);
      alert("설정 저장 및 인덱싱 시작 중 오류가 발생했습니다.");
    });
}

/**
 * 설정 저장 없이 전체 인덱싱 시작
 */
function startFullIndexing() {
  fetch("/api/index", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      incremental: false,
    }),
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error("인덱싱 시작에 실패했습니다.");
      }
      return response.json();
    })
    .then((data) => {
      window.location.href = "/indexing-process";
    })
    .catch((error) => {
      console.error("Error:", error);
      alert("인덱싱 시작 중 오류가 발생했습니다.");
    });
}

/**
 * 현재 메뉴 설정을 JSON 형태로 수집
 * @returns {Object} 메뉴 설정 객체
 */
function collectMenuSettings() {
  const menuSettings = {
    categories: {},
    items: {}
  };
  
  // 카테고리 설정 수집
  document.querySelectorAll('.menu-category-toggle').forEach(toggle => {
    const categoryId = toggle.id.replace('menu_category_', '');
    menuSettings.categories[categoryId] = {
      visible: toggle.checked,
      order: Array.from(document.querySelectorAll('.menu-category-toggle')).indexOf(toggle)
    };
  });
  
  // 메뉴 아이템 설정 수집
  const menuContainers = document.querySelectorAll('.menu-items');
  menuContainers.forEach((container, categoryIndex) => {
    const categoryId = document.querySelectorAll('.menu-category-toggle')[categoryIndex].id.replace('menu_category_', '');
    
    container.querySelectorAll('input[type="checkbox"][name="menu_items"]').forEach((checkbox, itemIndex) => {
      const menuId = checkbox.id.replace('menu_', '');
      menuSettings.items[menuId] = {
        visible: checkbox.checked,
        category: categoryId,
        order: itemIndex
      };
    });
  });
  
  return menuSettings;
}

/**
 * 메뉴 설정 저장 함수
 */
function saveMenuSettings() {
  const menuSettings = collectMenuSettings();
  const hiddenInput = document.getElementById('menu_settings_json');
  if (hiddenInput) {
    hiddenInput.value = JSON.stringify(menuSettings);
  }
  
  // 서버에 메뉴 설정 저장 API 호출
  fetch('/api/settings/menu', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(menuSettings),
  })
  .then(response => response.json())
  .then(data => {
    const messageEl = document.getElementById('menu-settings-message');
    if (!messageEl) return;
    
    if (data.success) {
      messageEl.textContent = '메뉴 설정이 저장되었습니다.';
      messageEl.classList.remove('hidden', 'text-red-500');
      messageEl.classList.add('text-green-500');
      
      // 3초 후 메시지 숨기기
      setTimeout(() => {
        messageEl.classList.add('hidden');
      }, 3000);
      
      // 저장 성공 시 사이드바 메뉴 자동 갱신 (필요한 경우)
      if (data.reload) {
        setTimeout(() => {
          window.location.reload();
        }, 1000);
      }
    } else {
      messageEl.textContent = data.message || '메뉴 설정 저장 중 오류가 발생했습니다.';
      messageEl.classList.remove('hidden', 'text-green-500');
      messageEl.classList.add('text-red-500');
    }
  })
  .catch(error => {
    console.error('Error:', error);
    const messageEl = document.getElementById('menu-settings-message');
    if (!messageEl) return;
    
    messageEl.textContent = '메뉴 설정 저장 중 오류가 발생했습니다.';
    messageEl.classList.remove('hidden', 'text-green-500');
    messageEl.classList.add('text-red-500');
  });
}

/**
 * 메뉴 설정 불러오기 함수
 */
function loadMenuSettings() {
  fetch('/api/settings/menu')
  .then(response => response.json())
  .then(data => {
    if (data.settings) {
      applyMenuSettings(data.settings);
    }
  })
  .catch(error => {
    console.error('메뉴 설정을 불러오는 중 오류가 발생했습니다:', error);
  });
}

/**
 * 메뉴 설정 적용 함수
 * @param {Object} settings - 적용할 메뉴 설정 객체
 */
function applyMenuSettings(settings) {
  // 카테고리 설정 적용
  if (settings.categories) {
    Object.keys(settings.categories).forEach(categoryId => {
      const toggle = document.getElementById(`menu_category_${categoryId}`);
      if (toggle) {
        toggle.checked = settings.categories[categoryId].visible;
        
        // 카테고리 상태에 따라 하위 메뉴 활성화/비활성화
        const menuItems = toggle.closest('div.border').querySelector('.menu-items');
        const checkboxes = menuItems.querySelectorAll('input[type="checkbox"]');
        const buttons = menuItems.querySelectorAll('button');
        
        checkboxes.forEach(checkbox => {
          checkbox.disabled = !toggle.checked;
        });
        
        buttons.forEach(button => {
          if (!toggle.checked) {
            button.disabled = true;
            button.classList.add('opacity-50', 'cursor-not-allowed');
          }
        });
      }
    });
  }
  
  // 메뉴 아이템 설정 적용
  if (settings.items) {
    Object.keys(settings.items).forEach(menuId => {
      const checkbox = document.getElementById(`menu_${menuId}`);
      if (checkbox) {
        checkbox.checked = settings.items[menuId].visible;
      }
    });
  }
}

/**
 * 메뉴 설정 기본값으로 복원 함수
 */
function resetMenuSettings() {
  // 모든 카테고리 체크
  document.querySelectorAll('.menu-category-toggle').forEach(toggle => {
    toggle.checked = true;
  });
  
  // 모든 메뉴 아이템 체크
  document.querySelectorAll('input[type="checkbox"][name="menu_items"]').forEach(checkbox => {
    checkbox.checked = true;
    checkbox.disabled = false;
  });
  
  // 모든 버튼 활성화
  document.querySelectorAll('.menu-move-up, .menu-move-down').forEach(button => {
    button.disabled = false;
    button.classList.remove('opacity-50', 'cursor-not-allowed');
  });
  
  // 서버에 기본값 복원 요청
  fetch('/api/settings/menu/reset', {
    method: 'POST',
  })
  .then(response => response.json())
  .then(data => {
    const messageEl = document.getElementById('menu-settings-message');
    if (data.success) {
      messageEl.textContent = '메뉴 설정이 기본값으로 복원되었습니다.';
      messageEl.classList.remove('hidden', 'text-red-500');
      messageEl.classList.add('text-green-500');
      
      // 3초 후 메시지 숨기기
      setTimeout(() => {
        messageEl.classList.add('hidden');
      }, 3000);
    } else {
      messageEl.textContent = data.message || '메뉴 설정 초기화 중 오류가 발생했습니다.';
      messageEl.classList.remove('hidden', 'text-green-500');
      messageEl.classList.add('text-red-500');
    }
  })
  .catch(error => {
    console.error('Error:', error);
    const messageEl = document.getElementById('menu-settings-message');
    messageEl.textContent = '메뉴 설정 초기화 중 오류가 발생했습니다.';
    messageEl.classList.remove('hidden', 'text-green-500');
    messageEl.classList.add('text-red-500');
  });
}

/**
 * 메뉴 관리 기능 초기화
 */
function initMenuManagement() {
  // 메뉴 카테고리 토글 이벤트 - 카테고리 체크박스 상태에 따라 하위 메뉴 활성화/비활성화
  const categoryToggles = document.querySelectorAll('.menu-category-toggle');
  if (categoryToggles.length > 0) {
    categoryToggles.forEach(toggle => {
      toggle.addEventListener('change', function() {
        const menuItems = this.closest('div.border').querySelector('.menu-items');
        const checkboxes = menuItems.querySelectorAll('input[type="checkbox"]');
        
        checkboxes.forEach(checkbox => {
          checkbox.disabled = !this.checked;
          if (!this.checked) {
            checkbox.checked = false;
          }
        });
        
        const buttons = menuItems.querySelectorAll('button');
        buttons.forEach(button => {
          if (!this.checked) {
            button.disabled = true;
            button.classList.add('opacity-50', 'cursor-not-allowed');
          } else {
            button.disabled = false;
            button.classList.remove('opacity-50', 'cursor-not-allowed');
          }
        });
      });
    });
  }
  
  // 메뉴 아이템 위로 이동 버튼
  const moveUpButtons = document.querySelectorAll('.menu-move-up');
  if (moveUpButtons.length > 0) {
    moveUpButtons.forEach(button => {
      button.addEventListener('click', function() {
        const menuItem = this.closest('.flex.items-center.justify-between');
        const prevMenuItem = menuItem.previousElementSibling;
        
        if (prevMenuItem) {
          menuItem.parentNode.insertBefore(menuItem, prevMenuItem);
        }
      });
    });
  }
  
  // 메뉴 아이템 아래로 이동 버튼
  const moveDownButtons = document.querySelectorAll('.menu-move-down');
  if (moveDownButtons.length > 0) {
    moveDownButtons.forEach(button => {
      button.addEventListener('click', function() {
        const menuItem = this.closest('.flex.items-center.justify-between');
        const nextMenuItem = menuItem.nextElementSibling;
        
        if (nextMenuItem) {
          menuItem.parentNode.insertBefore(nextMenuItem, menuItem);
        }
      });
    });
  }
  
  // 메뉴 설정 저장 버튼
  const saveMenuBtn = document.getElementById('save-menu-btn');
  if (saveMenuBtn) {
    saveMenuBtn.addEventListener('click', function() {
      saveMenuSettings();
    });
  }
  
  // 메뉴 기본값 복원 버튼
  const resetMenuBtn = document.getElementById('reset-menu-btn');
  if (resetMenuBtn) {
    resetMenuBtn.addEventListener('click', function() {
      if (confirm('메뉴 설정을 기본값으로 복원하시겠습니까?')) {
        resetMenuSettings();
      }
    });
  }
  
  // 초기 메뉴 설정 불러오기
  loadMenuSettings();
}
