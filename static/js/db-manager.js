// 데이터베이스 정보 HTML 생성 함수
function generateDatabaseInfoHTML(info) {
  if (!info || info.error) {
    return `
      <div class="text-center p-4 text-red-500">
        <p>오류: ${info?.error || '데이터베이스 정보를 가져올 수 없습니다.'}</p>
      </div>
    `;
  }
  
  return `
    <div class="space-y-4">
      <div class="flex items-center">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8 text-blue-500 mr-3" viewBox="0 0 20 20" fill="currentColor">
          <path d="M3 12v3c0 1.657 3.134 3 7 3s7-1.343 7-3v-3c0 1.657-3.134 3-7 3s-7-1.343-7-3z" />
          <path d="M3 7v3c0 1.657 3.134 3 7 3s7-1.343 7-3V7c0 1.657-3.134 3-7 3S3 8.657 3 7z" />
          <path d="M17 5c0 1.657-3.134 3-7 3S3 6.657 3 5s3.134-3 7-3 7 1.343 7 3z" />
        </svg>
        <div>
          <h3 class="font-semibold text-lg">SQLite ${info.version}</h3>
          <p class="text-sm text-gray-600">${info.path}</p>
        </div>
      </div>
      
      <div class="grid grid-cols-2 gap-4 mt-4">
        <div class="bg-gray-50 p-3 rounded-lg">
          <div class="text-2xl font-bold text-blue-600">${info.table_count}</div>
          <div class="text-sm text-gray-600">테이블</div>
        </div>
        <div class="bg-gray-50 p-3 rounded-lg">
          <div class="text-2xl font-bold text-green-600">${info.index_count}</div>
          <div class="text-sm text-gray-600">인덱스</div>
        </div>
      </div>
      
      <div class="border-t pt-4 mt-4">
        <div class="flex justify-between text-sm">
          <span class="text-gray-600">파일 크기:</span>
          <span class="font-medium">${info.size}</span>
        </div>
        ${info.last_modified ? `
        <div class="flex justify-between text-sm mt-2">
          <span class="text-gray-600">마지막 수정:</span>
          <span class="font-medium">${info.last_modified}</span>
        </div>
        ` : ''}
      </div>
    </div>
  `;
}

// 테이블 목록 HTML 생성 함수
function generateTableListHTML(tables) {
  if (!tables || tables.length === 0) {
    return `
      <div class="text-center p-4">
        <p class="text-gray-500">테이블이 없습니다</p>
      </div>
    `;
  }
  
  let html = '<div class="space-y-2">';
  
  tables.forEach(table => {
    html += `
      <div class="table-item p-3 border rounded-lg cursor-pointer hover:bg-gray-50 transition-colors" data-table="${table.name}">
        <div class="flex justify-between items-center">
          <div class="font-medium">${table.name}</div>
          <div class="text-sm text-gray-500">${table.type} 
            <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
              ${table.row_count} 행
            </span>
          </div>
        </div>
        <div class="text-xs text-gray-500 mt-1 truncate">${table.sql || ''}</div>
      </div>
    `;
  });
  
  html += '</div>';
  return html;
}

// 테이블 검색 기능
function setupTableSearch() {
  const searchInput = document.getElementById('table-search');
  if (!searchInput) return;
  
  searchInput.addEventListener('input', function() {
    const searchText = this.value.toLowerCase();
    const tableItems = document.querySelectorAll('.table-item');
    let visibleCount = 0;
    
    tableItems.forEach(item => {
      const tableName = item.dataset.table.toLowerCase();
      const tableType = item.querySelector('.text-gray-500').textContent.toLowerCase();
      const tableDesc = item.querySelector('.text-xs').textContent.toLowerCase();
      
      if (tableName.includes(searchText) || tableType.includes(searchText) || tableDesc.includes(searchText)) {
        item.style.display = '';
        visibleCount++;
      } else {
        item.style.display = 'none';
      }
    });
    
    // 검색 결과 없을 때 메시지 표시
    const noResultsMsg = document.getElementById('no-table-results');
    if (noResultsMsg) {
      if (visibleCount === 0 && searchText) {
        noResultsMsg.style.display = '';
      } else {
        noResultsMsg.style.display = 'none';
      }
    }
  });
}

// 로그 필터링 기능
function setupLogFilter() {
  const filterInput = document.getElementById('log-filter');
  if (!filterInput) return;
  
  filterInput.addEventListener('input', function() {
    const filterText = this.value.toLowerCase();
    const logContainer = document.querySelector('.log-container');
    if (!logContainer) return;
    
    const logEntries = logContainer.querySelectorAll('div');
    logEntries.forEach(entry => {
      const text = entry.textContent.toLowerCase();
      if (text.includes(filterText)) {
        entry.style.display = '';
      } else {
        entry.style.display = 'none';
      }
    });
  });
}

// 데이터베이스 정보 가져오기
function loadDatabaseInfo() {
  const dbInfoContainer = document.getElementById('db-info');
  if (!dbInfoContainer) return;
  
  // 로딩 표시
  dbInfoContainer.innerHTML = `
    <div class="text-center p-4">
      <div class="spinner"></div>
      <p class="mt-4 text-gray-500">데이터베이스 정보 로딩 중...</p>
    </div>
  `;
  
  // 데이터베이스 정보 가져오기
  fetch('/api/db/info')
    .then(response => response.json())
    .then(info => {
      dbInfoContainer.innerHTML = generateDatabaseInfoHTML(info);
    })
    .catch(error => {
      dbInfoContainer.innerHTML = `
        <div class="text-center p-4 text-red-500">
          <p>오류: ${error.message}</p>
        </div>
      `;
    });
}

// 테이블 목록 가져오기
function loadTableList() {
  const tableListContainer = document.getElementById('table-list');
  if (!tableListContainer) return;
  
  // 로딩 표시
  tableListContainer.innerHTML = `
    <div class="text-center p-4">
      <div class="spinner"></div>
      <p class="mt-4 text-gray-500">테이블 목록 로딩 중...</p>
    </div>
  `;
  
  // 테이블 목록 가져오기
  fetch('/api/db/tables')
    .then(response => response.json())
    .then(tables => {
      // 테이블 수 업데이트
      const tableCountElement = document.getElementById('table-count');
      if (tableCountElement) {
        tableCountElement.textContent = `${tables.length} 테이블`;
      }
      
      tableListContainer.innerHTML = generateTableListHTML(tables);
      
      // 테이블 클릭 이벤트 추가
      document.querySelectorAll('.table-item').forEach(item => {
        item.addEventListener('click', function() {
          const tableName = this.dataset.table;
          if (tableName) {
            console.log(`테이블 선택: ${tableName}`);
            loadTableData(tableName, 0);
            
            // 선택된 테이블 강조
            document.querySelectorAll('.table-item').forEach(el => {
              el.classList.remove('bg-blue-50', 'border-blue-500');
            });
            this.classList.add('bg-blue-50', 'border-blue-500');
          }
        });
      });
    })
    .catch(error => {
      tableListContainer.innerHTML = `
        <div class="text-center p-4 text-red-500">
          <p>오류: ${error.message}</p>
        </div>
      `;
    });
}

// 문서 로드 완료 시 실행
document.addEventListener('DOMContentLoaded', function() {
  // 로그 필터 설정
  setupLogFilter();
  
  // 테이블 검색 설정
  setupTableSearch();
  
  // 데이터베이스 정보 및 테이블 목록 가져오기
  loadDatabaseInfo();
  loadTableList();
  
  // 데이터베이스 새로고침 버튼 이벤트 설정
  const refreshButton = document.getElementById('refresh-db');
  if (refreshButton) {
    refreshButton.addEventListener('click', function() {
      loadDatabaseInfo();
      loadTableList();
    });
  }
  
  // HTMX 응답 처리
  document.body.addEventListener('htmx:afterSwap', function(evt) {
    // 인덱싱 상태 업데이트 후 로그 필터 다시 적용
    if (evt.detail.target.id === 'indexing-status') {
      setupLogFilter();
      
      // 로그 컨테이너 높이 제한 (5줄)
      const logContainer = document.querySelector('.log-container');
      if (logContainer) {
        logContainer.style.maxHeight = '150px'; // 약 5줄 높이
      }
    }
  });
});

// 테이블 데이터 로드 함수
function loadTableData(tableName, offset = 0) {
  if (!tableName) {
    console.error('테이블 이름이 지정되지 않았습니다.');
    return;
  }
  
  console.log(`테이블 데이터 로드: ${tableName}, 오프셋: ${offset}`);
  const currentLimit = 100;
  
  // 테이블 데이터 컨테이너 표시
  document.getElementById('table-data-container').classList.remove('hidden');
  
  // 테이블 이름 표시
  const tableNameElement = document.getElementById('selected-table-name');
  if (tableNameElement) {
    tableNameElement.textContent = tableName;
  }
  
  // 테이블 통계 정보 업데이트
  const tableStatsElement = document.getElementById('table-stats');
  if (tableStatsElement) {
    tableStatsElement.innerHTML = `<span class="bg-white bg-opacity-20 px-3 py-1 rounded-full">로딩 중...</span>`;
  }
  
  // 로딩 표시
  document.getElementById('table-data').innerHTML = `
    <div class="text-center p-4">
      <div class="spinner"></div>
      <p class="mt-4 text-gray-500">데이터 로딩 중...</p>
    </div>
  `;
  
  // 데이터 가져오기
  fetch(`/api/db/table/${tableName}?limit=${currentLimit}&offset=${offset}`)
    .then(response => response.json())
    .then(data => {
      if (data.error) {
        document.getElementById('table-data').innerHTML = `
          <div class="text-center p-4 text-red-500">
            <p>오류: ${data.error}</p>
          </div>
        `;
        return;
      }
      
      const totalRows = data.total_count;
      
      // 테이블 통계 업데이트
      if (tableStatsElement) {
        tableStatsElement.innerHTML = `
          <span class="bg-white bg-opacity-20 px-3 py-1 rounded-full">${totalRows} 행</span>
          <span class="bg-white bg-opacity-20 px-3 py-1 rounded-full">${data.columns ? data.columns.length : 0} 열</span>
        `;
      }
      
      updatePagination(offset, currentLimit, totalRows);
      renderTableData(data);
    })
    .catch(error => {
      document.getElementById('table-data').innerHTML = `
        <div class="text-center p-4 text-red-500">
          <p>오류: ${error.message}</p>
        </div>
      `;
    });
}

// 페이지네이션 업데이트
function updatePagination(offset, limit, totalRows) {
  const start = offset + 1;
  const end = Math.min(offset + limit, totalRows);
  document.getElementById('pagination-info').textContent = `${start}-${end} / ${totalRows}`;
  
  // 이전/다음 버튼 활성화 상태 설정
  document.getElementById('prev-page').disabled = offset <= 0;
  document.getElementById('next-page').disabled = offset + limit >= totalRows;
  
  // 현재 테이블 이름 가져오기
  const tableNameElement = document.getElementById('selected-table-name');
  const currentTableName = tableNameElement ? tableNameElement.textContent : '';
  
  // 이전/다음 버튼 이벤트 리스너 추가
  document.getElementById('prev-page').onclick = function() {
    if (offset > 0 && currentTableName) {
      const newOffset = Math.max(0, offset - limit);
      loadTableData(currentTableName, newOffset);
    }
  };
  
  document.getElementById('next-page').onclick = function() {
    if (offset + limit < totalRows && currentTableName) {
      loadTableData(currentTableName, offset + limit);
    }
  };
}

// 테이블 데이터 렌더링
function renderTableData(data) {
  const columns = data.columns;
  const rows = data.rows;
  
  if (columns.length === 0 || rows.length === 0) {
    document.getElementById('table-data').innerHTML = `
      <div class="text-center p-4">
        <p class="text-gray-500">데이터가 없습니다</p>
      </div>
    `;
    return;
  }
  
  // 테이블 생성
  let tableHtml = `
    <table class="min-w-full divide-y divide-gray-200">
      <thead class="bg-gray-50">
        <tr>
  `;
  
  // 헤더 생성
  columns.forEach(col => {
    tableHtml += `<th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">${col.name}</th>`;
  });
  
  tableHtml += `
        </tr>
      </thead>
      <tbody class="bg-white divide-y divide-gray-200">
  `;
  
  // 행 생성
  rows.forEach((row, index) => {
    const rowClass = index % 2 === 0 ? 'bg-white' : 'bg-gray-50';
    tableHtml += `<tr class="${rowClass}">`;
    
    columns.forEach(col => {
      const value = row[col.name] !== null ? row[col.name] : '';
      tableHtml += `<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${value}</td>`;
    });
    
    tableHtml += `</tr>`;
  });
  
  tableHtml += `
      </tbody>
    </table>
  `;
  
  document.getElementById('table-data').innerHTML = tableHtml;
}
