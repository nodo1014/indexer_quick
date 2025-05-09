/**
 * 대시보드 통계 모듈
 *
 * 대시보드 페이지에서 통계 데이터를 로드하고 차트를 렌더링하는 기능을 제공합니다.
 */

// Chart.js 설정
Chart.defaults.font.family =
  "Pretendard, -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif";
Chart.defaults.color = "#555";

// 차트 인스턴스 저장 객체
const charts = {
  lengthDistribution: null,
  dailyIndexing: null,
  extensions: null,
  subtitleRatio: null,
};

/**
 * 대시보드 초기화
 */
function initDashboard() {
  // 기본 통계 로드
  loadStats();

  // 데이터베이스 통계 로드
  loadDbStats();

  // 차트 데이터 로드
  loadLengthDistribution();
  loadDailyStats();
  loadMediaStats();

  // 30초마다 자동 새로고침
  setInterval(function () {
    loadStats();
    loadDbStats();
    loadLengthDistribution();
    loadDailyStats();
    loadMediaStats();
  }, 30000);

  // htmx 이벤트 처리
  document.body.addEventListener("htmx:afterRequest", function (evt) {
    // 통계 갱신
    if (
      evt.detail.elt.getAttribute("hx-trigger") &&
      evt.detail.elt.getAttribute("hx-trigger").includes("stats-refresh")
    ) {
      loadStats();
      loadDbStats();
      loadLengthDistribution();
      loadDailyStats();
      loadMediaStats();
    }
  });
}

/**
 * 기본 통계 로드
 */
function loadStats() {
  fetch("/api/stats")
    .then((response) => response.text())
    .then((html) => {
      document.getElementById("stats-content").innerHTML = html;
    })
    .catch((error) => {
      console.error("기본 통계 로드 중 오류:", error);
      document.getElementById("stats-content").innerHTML = `
        <div class="text-center p-4">
          <p class="text-red-500">오류: 통계 데이터를 불러올 수 없습니다.</p>
        </div>
      `;
    });
}

/**
 * 데이터베이스 통계 로드
 */
function loadDbStats() {
  fetch("/api/db/stats")
    .then((response) => response.json())
    .then((data) => {
      if (data.error) {
        document.getElementById("db-stats-content").innerHTML = `
          <div class="text-center p-4">
            <p class="text-red-500">오류: ${data.error}</p>
          </div>
        `;
        return;
      }

      // FTS 인덱스 상태
      const ftsStatus = data.fts_status;
      const ftsStatusClass = ftsStatus.is_synced
        ? "text-green-600"
        : "text-yellow-600";
      const ftsStatusText = ftsStatus.is_synced ? "완료" : "불일치";

      // 테이블 통계 표시
      let tableStatsHtml = "";
      data.table_stats.forEach((table) => {
        tableStatsHtml += `
          <div class="flex justify-between items-center text-sm py-1 border-b border-gray-100">
            <span class="font-medium">${table.name}</span>
            <div class="flex items-center space-x-2">
              <span class="text-gray-500">${table.row_count} 행</span>
              <span class="text-xs text-gray-400">(~${table.estimated_size})</span>
            </div>
          </div>
        `;
      });

      // 자막 유무 비율 계산
      const withSubtitlePercent =
        data.media_count > 0
          ? Math.round((data.media_with_subtitles / data.media_count) * 100)
          : 0;
      const withoutSubtitlePercent = 100 - withSubtitlePercent;

      // HTML 생성
      const html = `
        <div class="space-y-4">
          <div class="flex justify-between items-center">
            <div>
              <div class="text-sm text-gray-600">자막 총 개수</div>
              <div class="text-2xl font-bold">${data.subtitle_count.toLocaleString()}</div>
            </div>
            <div>
              <div class="text-sm text-gray-600">미디어 파일 총 개수</div>
              <div class="text-2xl font-bold">${data.media_count.toLocaleString()}</div>
            </div>
          </div>
          
          <div class="mt-4">
            <div class="text-sm text-gray-600 mb-1">자막 유무 비율</div>
            <div class="flex h-4 rounded-full overflow-hidden bg-gray-200">
              <div class="bg-blue-500 h-full" style="width: ${withSubtitlePercent}%"></div>
              <div class="bg-gray-400 h-full" style="width: ${withoutSubtitlePercent}%"></div>
            </div>
            <div class="flex justify-between text-xs mt-1">
              <span>자막 있음: ${data.media_with_subtitles.toLocaleString()} (${withSubtitlePercent}%)</span>
              <span>자막 없음: ${data.media_without_subtitles.toLocaleString()} (${withoutSubtitlePercent}%)</span>
            </div>
          </div>
          
          <div class="mt-4">
            <div class="flex justify-between items-center mb-2">
              <div class="text-sm text-gray-600">FTS 인덱스 상태</div>
              <div class="text-xs ${ftsStatusClass} font-medium">${ftsStatusText}</div>
            </div>
            <div class="flex h-2 rounded-full overflow-hidden bg-gray-200">
              <div class="bg-blue-500 h-full" style="width: ${
                ftsStatus.sync_percentage
              }%"></div>
            </div>
            <div class="text-xs text-gray-500 mt-1">
              ${ftsStatus.indexed_count.toLocaleString()} / ${ftsStatus.total_count.toLocaleString()} 자막 인덱싱됨 (${
        ftsStatus.sync_percentage
      }%)
            </div>
          </div>
          
          <div class="mt-4">
            <div class="text-sm text-gray-600 mb-2">테이블 통계</div>
            ${tableStatsHtml}
          </div>
        </div>
      `;

      document.getElementById("db-stats-content").innerHTML = html;
    })
    .catch((error) => {
      console.error("데이터베이스 통계 로드 중 오류:", error);
      document.getElementById("db-stats-content").innerHTML = `
        <div class="text-center p-4">
          <p class="text-red-500">오류: 데이터베이스 통계를 불러올 수 없습니다.</p>
        </div>
      `;
    });
}

/**
 * 자막 길이 분포 차트 로드
 */
function loadLengthDistribution() {
  fetch("/api/stats/length-distribution")
    .then((response) => response.json())
    .then((data) => {
      const ctx = document
        .getElementById("lengthDistributionChart")
        .getContext("2d");

      // 기존 차트 제거
      if (charts.lengthDistribution) {
        charts.lengthDistribution.destroy();
      }

      // 차트 데이터
      const chartData = {
        labels: data.labels,
        datasets: [
          {
            label: "자막 개수",
            data: data.data,
            backgroundColor: [
              "rgba(54, 162, 235, 0.7)",
              "rgba(75, 192, 192, 0.7)",
              "rgba(153, 102, 255, 0.7)",
              "rgba(255, 159, 64, 0.7)",
              "rgba(255, 99, 132, 0.7)",
            ],
            borderColor: [
              "rgba(54, 162, 235, 1)",
              "rgba(75, 192, 192, 1)",
              "rgba(153, 102, 255, 1)",
              "rgba(255, 159, 64, 1)",
              "rgba(255, 99, 132, 1)",
            ],
            borderWidth: 1,
          },
        ],
      };

      // 차트 옵션
      const options = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false,
          },
          tooltip: {
            callbacks: {
              label: function (context) {
                return `${context.label}: ${context.raw.toLocaleString()} 개`;
              },
            },
          },
        },
      };

      // 차트 생성
      charts.lengthDistribution = new Chart(ctx, {
        type: "bar",
        data: chartData,
        options: options,
      });
    })
    .catch((error) => {
      console.error("자막 길이 분포 차트 로드 중 오류:", error);
      document.getElementById(
        "lengthDistributionChart"
      ).parentElement.innerHTML = `
        <div class="text-center p-4">
          <p class="text-red-500">오류: 자막 길이 분포 데이터를 불러올 수 없습니다.</p>
        </div>
      `;
    });
}

/**
 * 일일 인덱싱 통계 차트 로드
 */
function loadDailyStats() {
  fetch("/api/stats/daily")
    .then((response) => response.json())
    .then((data) => {
      const ctx = document
        .getElementById("dailyIndexingChart")
        .getContext("2d");

      // 기존 차트 제거
      if (charts.dailyIndexing) {
        charts.dailyIndexing.destroy();
      }

      // 차트 데이터
      const chartData = {
        labels: data.dates,
        datasets: [
          {
            label: "인덱싱된 파일 수",
            data: data.counts,
            backgroundColor: "rgba(75, 192, 192, 0.7)",
            borderColor: "rgba(75, 192, 192, 1)",
            borderWidth: 1,
          },
        ],
      };

      // 차트 옵션
      const options = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false,
          },
          tooltip: {
            callbacks: {
              label: function (context) {
                return `${context.raw.toLocaleString()} 파일`;
              },
            },
          },
        },
        scales: {
          y: {
            beginAtZero: true,
          },
        },
      };

      // 차트 생성
      charts.dailyIndexing = new Chart(ctx, {
        type: "bar",
        data: chartData,
        options: options,
      });
    })
    .catch((error) => {
      console.error("일일 인덱싱 통계 차트 로드 중 오류:", error);
      document.getElementById("dailyIndexingChart").parentElement.innerHTML = `
        <div class="text-center p-4">
          <p class="text-red-500">오류: 일일 인덱싱 통계를 불러올 수 없습니다.</p>
        </div>
      `;
    });
}

/**
 * 미디어 통계 차트 로드 (확장자 및 자막 비율)
 */
function loadMediaStats() {
  fetch("/api/stats/json")
    .then((response) => response.json())
    .then((data) => {
      // 확장자 차트
      loadExtensionsChart(data.file_stats.extensions);

      // 자막 비율 차트
      loadSubtitleRatioChart(data.media_stats);
    })
    .catch((error) => {
      console.error("미디어 통계 차트 로드 중 오류:", error);

      // 확장자 차트 오류 표시
      document.getElementById("extensionsChart").parentElement.innerHTML = `
        <div class="text-center p-4">
          <p class="text-red-500">오류: 확장자 통계를 불러올 수 없습니다.</p>
        </div>
      `;

      // 자막 비율 차트 오류 표시
      document.getElementById("subtitleRatioChart").parentElement.innerHTML = `
        <div class="text-center p-4">
          <p class="text-red-500">오류: 자막 비율 통계를 불러올 수 없습니다.</p>
        </div>
      `;
    });
}

/**
 * 확장자 차트 로드
 */
function loadExtensionsChart(extensions) {
  const ctx = document.getElementById("extensionsChart").getContext("2d");

  // 기존 차트 제거
  if (charts.extensions) {
    charts.extensions.destroy();
  }

  // 데이터 준비
  const labels = [];
  const data = [];
  const colors = [
    "rgba(54, 162, 235, 0.7)",
    "rgba(75, 192, 192, 0.7)",
    "rgba(153, 102, 255, 0.7)",
    "rgba(255, 159, 64, 0.7)",
    "rgba(255, 99, 132, 0.7)",
    "rgba(255, 205, 86, 0.7)",
    "rgba(201, 203, 207, 0.7)",
  ];

  // 확장자별 파일 수 정렬
  const sortedExtensions = Object.entries(extensions)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 7); // 상위 7개만 표시

  // 차트 데이터 구성
  sortedExtensions.forEach(([ext, count], index) => {
    labels.push(ext);
    data.push(count);
  });

  // 차트 데이터
  const chartData = {
    labels: labels,
    datasets: [
      {
        data: data,
        backgroundColor: colors.slice(0, labels.length),
        borderColor: colors.map((color) => color.replace("0.7", "1")),
        borderWidth: 1,
      },
    ],
  };

  // 차트 옵션
  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: "right",
        labels: {
          boxWidth: 15,
          padding: 10,
        },
      },
      tooltip: {
        callbacks: {
          label: function (context) {
            const label = context.label || "";
            const value = context.raw || 0;
            const total = context.chart.data.datasets[0].data.reduce(
              (a, b) => a + b,
              0
            );
            const percentage = Math.round((value / total) * 100);
            return `${label}: ${value.toLocaleString()} (${percentage}%)`;
          },
        },
      },
    },
  };

  // 차트 생성
  charts.extensions = new Chart(ctx, {
    type: "pie",
    data: chartData,
    options: options,
  });
}

/**
 * 자막 비율 차트 로드
 */
function loadSubtitleRatioChart(mediaStats) {
  const ctx = document.getElementById("subtitleRatioChart").getContext("2d");

  // 기존 차트 제거
  if (charts.subtitleRatio) {
    charts.subtitleRatio.destroy();
  }

  // 데이터 준비
  const withSubtitles = mediaStats.with_subtitles || 0;
  const withoutSubtitles = mediaStats.without_subtitles || 0;

  // 차트 데이터
  const chartData = {
    labels: ["자막 있음", "자막 없음"],
    datasets: [
      {
        data: [withSubtitles, withoutSubtitles],
        backgroundColor: ["rgba(54, 162, 235, 0.7)", "rgba(255, 99, 132, 0.7)"],
        borderColor: ["rgba(54, 162, 235, 1)", "rgba(255, 99, 132, 1)"],
        borderWidth: 1,
      },
    ],
  };

  // 차트 옵션
  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: "right",
        labels: {
          boxWidth: 15,
          padding: 10,
        },
      },
      tooltip: {
        callbacks: {
          label: function (context) {
            const label = context.label || "";
            const value = context.raw || 0;
            const total = context.chart.data.datasets[0].data.reduce(
              (a, b) => a + b,
              0
            );
            const percentage = Math.round((value / total) * 100);
            return `${label}: ${value.toLocaleString()} (${percentage}%)`;
          },
        },
      },
    },
  };

  // 차트 생성
  charts.subtitleRatio = new Chart(ctx, {
    type: "doughnut",
    data: chartData,
    options: options,
  });
}

// 문서 로드 완료 시 대시보드 초기화
document.addEventListener("DOMContentLoaded", initDashboard);
