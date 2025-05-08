/**
 * search-api.js
 * 검색 API 호출 관련 함수들
 */

// 전역 API 객체 생성
window.SearchAPI = {
  /**
   * 검색 API 호출 - 미디어가 있는 자막만 검색 대상으로 함
   * @param {string} query - 검색어
   * @param {Object} options - 검색 옵션
   * @returns {Promise<Object>} 검색 결과 객체
   */
  search: async function(query, options = {}) {
    try {
      const url = new URL('/api/search', window.location.origin);
      
      // 쿼리 파라미터 추가
      url.searchParams.append('query', query);
      
      // 미디어가 있는 자막만 검색하도록 파라미터 추가 (기본값)
      if (!options.hasOwnProperty('media_only')) {
        url.searchParams.append('media_only', 'true'); // 미디어가 있는 자막만 검색
      }
      
      // 옵션 파라미터 추가
      Object.keys(options).forEach(key => {
        if (options[key] !== undefined && options[key] !== null) {
          url.searchParams.append(key, options[key]);
        }
      });
      
      console.log(`검색 API 요청: ${url.toString()}`);
      
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`검색 API 오류: ${response.status} ${response.statusText}`);
      }
      
      const data = await response.json();
      console.log(`검색 결과: ${data?.results?.length || 0}개 항목`);
      
      // 검색 결과 디버깅을 위해 자세히 출력
      if (data?.results?.length > 0) {
        console.log('검색 결과 첫 번째 항목:', data.results[0]);
      } else {
        console.warn('검색 결과가 없습니다.');
      }
      
      return data;
    } catch (error) {
      console.error('검색 API 호출 중 오류 발생:', error);
      throw error;
    }
  },
  
  // 태그 API 호출
  getTags: async function(mediaPath) {
    try {
      const response = await fetch(`/api/tags/${encodeURIComponent(mediaPath)}`);
      if (!response.ok) {
        throw new Error(`태그 API 오류: ${response.status} ${response.statusText}`);
      }
      
      const data = await response.json();
      return data.tags || [];
    } catch (error) {
      console.error('태그 API 호출 중 오류 발생:', error);
      return [];
    }
  },
  
  // 태그 추가 API 호출
  addTag: async function(mediaPath, startTime, tag) {
    try {
      const response = await fetch('/api/tags', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          media_path: mediaPath,
          start_time: parseFloat(startTime),
          tag: tag
        })
      });
      
      if (!response.ok) {
        throw new Error(`태그 추가 API 오류: ${response.status} ${response.statusText}`);
      }
      
      const data = await response.json();
      return data;
    } catch (error) {
      console.error('태그 추가 API 호출 중 오류 발생:', error);
      throw error;
    }
  },
  
  // 태그 삭제 API 호출
  removeTag: async function(mediaPath, startTime, tag) {
    try {
      const response = await fetch('/api/tags', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          media_path: mediaPath,
          start_time: parseFloat(startTime),
          tag: tag
        })
      });
      
      if (!response.ok) {
        throw new Error(`태그 삭제 API 오류: ${response.status} ${response.statusText}`);
      }
      
      const data = await response.json();
      return data;
    } catch (error) {
      console.error('태그 삭제 API 호출 중 오류 발생:', error);
      throw error;
    }
  },
  
  // 북마크 상태 변경 API 호출
  toggleBookmark: async function(mediaPath, startTime, bookmarked) {
    try {
      const response = await fetch('/api/bookmarks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          media_path: mediaPath,
          start_time: parseFloat(startTime),
          bookmarked: bookmarked
        })
      });
      
      if (!response.ok) {
        throw new Error(`북마크 API 오류: ${response.status} ${response.statusText}`);
      }
      
      const data = await response.json();
      return data;
    } catch (error) {
      console.error('북마크 API 호출 중 오류 발생:', error);
      throw error;
    }
  },
  
  // 북마크 상태 확인 API 호출
  getBookmarkStatus: async function(mediaPath, startTime) {
    try {
      const response = await fetch(`/api/bookmarks/status?media_path=${encodeURIComponent(mediaPath)}&start_time=${startTime}`);
      
      if (!response.ok) {
        throw new Error(`북마크 상태 API 오류: ${response.status} ${response.statusText}`);
      }
      
      const data = await response.json();
      return data.bookmarked || false;
    } catch (error) {
      console.error('북마크 상태 API 호출 중 오류 발생:', error);
      return false;
    }
  }
};
