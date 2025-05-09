/**
 * 인덱싱 상태 표시 관련 자바스크립트
 * 인덱싱 상태 JSON 데이터를 포맷팅하여 보기 좋게 표시합니다.
 */

document.addEventListener("DOMContentLoaded", function() {
  // 인덱싱 상태 요소 찾기
  const indexingStatusElement = document.getElementById('indexing-status');
  
  if (indexingStatusElement) {
    // MutationObserver를 사용하여 요소 내용 변경 감지
    const observer = new MutationObserver(function(mutations) {
      mutations.forEach(function(mutation) {
        if (mutation.type === 'childList') {
          formatIndexingStatus();
        }
      });
    });
    
    // 옵저버 설정 및 시작
    observer.observe(indexingStatusElement, { childList: true });
    
    // 초기 포맷팅 실행
    formatIndexingStatus();
  }
});

/**
 * 인덱싱 상태 JSON 데이터를 파싱하여 보기 좋게 포맷팅합니다.
 */
function formatIndexingStatus() {
  const statusElement = document.getElementById('indexing-status');
  if (!statusElement) return;
  
  try {
    // 요소의 텍스트 콘텐츠에서 JSON 추출
    const content = statusElement.textContent.trim();
    if (!content || content.startsWith('<div')) return; // 이미 HTML이면 처리하지 않음
    
    // JSON 파싱
    const statusData = JSON.parse(content);
    
    // 인덱싱 완료 상태 확인
    if (statusData.status_message && statusData.status_message.includes('완료')) {
      // 인덱싱이 완료되면 통계 새로고침
      refreshStats();
    }
    
    // 상태 데이터 포맷팅
    let html = createStatusHTML(statusData);
    
    // HTML 적용
    statusElement.innerHTML = html;
    
    // 로그 필터링 적용 (indexing.js에 있는 함수 호출)
    if (typeof applyLogFilter === 'function') {
      applyLogFilter();
    }
  } catch (error) {
    console.error('인덱싱 상태 포맷팅 오류:', error);
  }
}

/**
 * 통계 정보를 새로고칩니다.
 */
function refreshStats() {
  // 통계 요소 찾기
  const statsElement = document.getElementById('stats');
  if (statsElement) {
    console.log('통계 새로고침 시도...');
    // htmx 트리거를 사용하여 통계 새로고침
    htmx.trigger(statsElement, 'load');
    // 추가로 body에도 이벤트 트리거
    htmx.trigger(document.body, 'stats-refresh');
  }
}

/**
 * 인덱싱 상태 데이터로부터 HTML을 생성합니다.
 * @param {Object} data - 인덱싱 상태 데이터
 * @returns {string} 포맷팅된 HTML
 */
function createStatusHTML(data) {
  // 상태 클래스 결정
  let statusClass = 'status-idle';
  let statusText = '대기 중';
  
  if (data.is_indexing) {
    statusClass = 'status-running';
    statusText = '실행 중';
    
    if (data.is_paused) {
      statusClass = 'status-paused';
      statusText = '일시 중지됨';
    }
  } else if (data.status_message && data.status_message.includes('완료')) {
    statusClass = 'status-completed';
    statusText = '완료됨';
  }
  
  // 진행률 계산
  const progress = data.progress || 0;
  const progressPercent = Math.min(100, Math.max(0, progress));
  
  // 로그 메시지 포맷팅
  const logMessages = formatLogMessages(data.log_messages || []);
  
  // HTML 생성
  return `
    <div class="space-y-4">
      <!-- 상태 카드 -->
      <div class="indexing-status-card ${statusClass} rounded-md shadow-sm border">
        <div class="flex justify-between items-center">
          <h3 class="text-lg font-semibold">${statusText}</h3>
          <span class="text-sm">${new Date(data.last_updated || Date.now()).toLocaleString()}</span>
        </div>
        
        <!-- 진행률 표시 -->
        <div class="mt-2">
          <div class="flex justify-between text-sm mb-1">
            <span>진행률: ${progressPercent}%</span>
            <span>${data.processed_files || 0} / ${data.total_files || 0} 파일</span>
          </div>
          <div class="progress-bar">
            <div class="progress-value" style="width: ${progressPercent}%"></div>
          </div>
        </div>
        
        <!-- 현재 처리 중인 파일 -->
        ${data.current_file ? `
        <div class="mt-2 text-sm">
          <p class="font-semibold">현재 파일:</p>
          <p class="text-gray-700 truncate">${data.current_file}</p>
        </div>
        ` : ''}
        
        <!-- 자막 수 -->
        <div class="mt-2 text-sm">
          <p>처리된 자막: <span class="font-semibold">${data.subtitle_count || 0}</span>개</p>
        </div>
      </div>
      
      <!-- 로그 메시지 -->
      <div class="log-container mt-4 bg-gray-900 text-gray-200 p-3 rounded-md shadow-sm overflow-y-auto">
        ${logMessages}
      </div>
    </div>
  `;
}

/**
 * 로그 메시지를 HTML로 포맷팅합니다.
 * @param {Array} logs - 로그 메시지 배열
 * @returns {string} 포맷팅된 HTML
 */
function formatLogMessages(logs) {
  if (!logs || logs.length === 0) {
    return '<div class="text-center p-4"><p class="text-gray-500">로그가 없습니다.</p></div>';
  }
  
  let html = '<div class="space-y-1">';
  
  logs.forEach((log, index) => {
    // 로그 레벨에 따른 스타일 적용 - 터미널 스타일
    let logClass = 'text-gray-300';  // 기본 스타일
    let levelColor = 'text-gray-400';
    
    if (log.includes('ERROR')) {
      logClass = 'text-red-400';
      levelColor = 'text-red-500';
    } else if (log.includes('WARNING')) {
      logClass = 'text-yellow-300';
      levelColor = 'text-yellow-400';
    } else if (log.includes('INFO')) {
      logClass = 'text-blue-300';
      levelColor = 'text-blue-400';
    } else if (log.includes('DEBUG')) {
      logClass = 'text-green-300';
      levelColor = 'text-green-400';
    }
    
    // 줄 번호
    const lineNumber = `${index + 1}`.padStart(2, '0');
    
    // 로그 항목 HTML 생성 - 터미널 스타일 유지
    html += `
      <div class="log-line ${logClass} text-sm py-1 font-mono">
        <div class="flex">
          <span class="text-gray-400 mr-2 text-xs">${lineNumber}</span>
          <span class="${levelColor} text-xs font-medium mr-2">${log.substring(9, 14).trim()}</span>
          <span>${log.substring(15)}</span>
        </div>
      </div>
    `;
  });
  
  html += '</div>';
  return html;
}
