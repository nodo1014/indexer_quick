/**
 * TagManager - 자막 태그 관리 모듈
 * 자막에 태그를 추가, 삭제, 편집하는 기능을 제공합니다.
 */

export class TagManager {
  constructor() {
    this.activeEditorElement = null;
    this.debugMode = true;
    this.debug("TagManager 인스턴스 생성됨");
  }

  /**
   * 초기화 함수
   */
  init() {
    this.debug("TagManager 초기화됨");
    return this;
  }

  /**
   * 페이지 내 태그 버튼에 이벤트 핸들러 설정
   */
  setupTagButtons() {
    const tagButtons = document.querySelectorAll(".tag-btn");
    this.debug(`태그 버튼 설정: ${tagButtons.length}개 발견`);

    tagButtons.forEach((button) => {
      button.addEventListener("click", async (e) => {
        e.stopPropagation(); // 자막 클릭 이벤트 전파 방지

        const subtitleElement = button.closest(".subtitle-pair");
        if (!subtitleElement) return;

        const mediaPath = subtitleElement.dataset.mediaPath;
        const startTime = subtitleElement.dataset.startTime;

        try {
          // 현재 태그 가져오기
          const tags = await window.fetchTags(mediaPath, startTime) || [];
          
          // 태그 편집 다이얼로그 표시
          this.showTagEditor(mediaPath, startTime, tags, subtitleElement);
        } catch (error) {
          console.error("태그 정보 가져오기 오류:", error);
        }
      });
    });
  }

  /**
   * 태그 편집 다이얼로그 표시
   * @param {string} mediaPath - 미디어 파일 경로
   * @param {number} startTime - 자막 시작 시간
   * @param {Array} currentTags - 현재 태그 목록
   * @param {HTMLElement} subtitleElement - 자막 DOM 요소
   */
  showTagEditor(mediaPath, startTime, currentTags, subtitleElement) {
    this.debug(`태그 편집기 표시: ${mediaPath} - ${startTime}, 현재 태그: ${currentTags.join(', ')}`);
    
    // 이미 다이얼로그가 있으면 제거
    this.closeTagEditor();

    // 활성 요소 기억
    this.activeEditorElement = subtitleElement;

    // 태그 편집 다이얼로그 생성
    const dialog = document.createElement("div");
    dialog.id = "tag-editor-dialog";
    dialog.className = "fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-white p-4 rounded-lg shadow-lg z-50 w-80";

    const tagsStr = Array.isArray(currentTags) ? currentTags.join(", ") : "";

    dialog.innerHTML = `
      <div class="flex flex-col gap-3">
        <h3 class="text-lg font-medium">태그 편집</h3>
        <p class="text-sm text-gray-600">태그는 쉼표(,)로 구분합니다.</p>
        <input type="text" id="tag-input" value="${tagsStr}" placeholder="태그 입력..." class="border border-gray-300 rounded px-3 py-2">
        <div class="flex justify-end gap-2 mt-2">
          <button id="save-tags-btn" class="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600">저장</button>
          <button id="cancel-tags-btn" class="bg-gray-200 text-gray-800 px-4 py-2 rounded hover:bg-gray-300">취소</button>
        </div>
      </div>
    `;

    // 배경 오버레이 생성
    const overlay = document.createElement("div");
    overlay.id = "tag-editor-overlay";
    overlay.className = "fixed inset-0 bg-black bg-opacity-50 z-40";

    // 문서에 추가
    document.body.appendChild(overlay);
    document.body.appendChild(dialog);

    // 입력 필드 포커스
    document.getElementById("tag-input").focus();

    // 이벤트 핸들러 바인딩을 위해 현재 객체 참조 저장
    const self = this;

    // 저장 버튼 이벤트
    document.getElementById("save-tags-btn").addEventListener("click", async () => {
      const tagInput = document.getElementById("tag-input");
      const newTagsStr = tagInput.value;
      const newTags = newTagsStr
        .split(",")
        .map((t) => t.trim())
        .filter((t) => t !== "");

      // 기존 태그와 새 태그 비교
      const tagsToAdd = newTags.filter(tag => !currentTags.includes(tag));
      const tagsToRemove = currentTags.filter(tag => !newTags.includes(tag));

      try {
        // 태그 제거
        for (const tag of tagsToRemove) {
          await window.deleteTagFromDB(mediaPath, startTime, tag);
        }
        
        // 태그 추가
        for (const tag of tagsToAdd) {
          await window.addTagToDB(mediaPath, startTime, tag);
        }
        
        self.debug(`태그 업데이트 완료: ${newTags.join(", ")}`);
        
        // 태그 UI 업데이트 (태그 컨테이너 갱신)
        if (self.activeEditorElement) {
          const tagsContainer = self.activeEditorElement.querySelector('.tags-container') || 
                               document.createElement('div');
          
          if (!self.activeEditorElement.querySelector('.tags-container')) {
            tagsContainer.className = 'tags-container mt-1';
            // 자막 텍스트 다음에 추가
            const koText = self.activeEditorElement.querySelector('.subtitle-text-ko');
            if (koText) {
              koText.insertAdjacentElement('afterend', tagsContainer);
            }
          }
          
          // 태그 요소 생성
          if (newTags.length > 0) {
            tagsContainer.innerHTML = newTags.map(tag => 
              `<span class="tag px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded">${tag}</span>`
            ).join(' ');
          } else {
            tagsContainer.innerHTML = '';
          }
        }
        
        // 다이얼로그 닫기
        self.closeTagEditor();
      } catch (error) {
        console.error("태그 업데이트 오류:", error);
      }
    });

    // 취소 버튼 이벤트
    document.getElementById("cancel-tags-btn").addEventListener("click", () => self.closeTagEditor());

    // 배경 클릭 시 닫기
    overlay.addEventListener("click", () => self.closeTagEditor());
  }

  /**
   * 태그 편집 다이얼로그 닫기
   */
  closeTagEditor() {
    const dialog = document.getElementById("tag-editor-dialog");
    const overlay = document.getElementById("tag-editor-overlay");

    if (dialog) dialog.remove();
    if (overlay) overlay.remove();
    
    this.activeEditorElement = null;
  }

  /**
   * 디버그 로그 출력
   * @param {string} message - 로그 메시지
   */
  debug(message) {
    if (this.debugMode) {
      console.log(`[TagManager] ${message}`);
    }
  }
} 