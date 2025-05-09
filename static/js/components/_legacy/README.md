# 레거시 비디오 플레이어 코드

이 디렉토리는 이전 버전의 비디오 플레이어 관련 코드를 포함하고 있습니다. 이 파일들은 참조용으로만 보관되어 있으며, 현재 사용되지 않습니다.

## 현재 사용 중인 비디오 플레이어 구현

현재 애플리케이션은 `/static/js/components/video-components/` 디렉토리에 있는 모듈화된 비디오 플레이어를 사용합니다:

- `video-player.js`: 메인 VideoPlayer 클래스
- `subtitle-controller.js`: 자막 표시 및 제어 기능
- `playback-manager.js`: 재생 모드 및 재생 제어 기능
- `bookmark-manager.js`: 북마크 및 태그 관리 기능

## 레거시 파일 설명

- `video-player.js`: 초기 단일 파일 비디오 플레이어 구현
- `video-adapter.js`: Video.js 라이브러리 어댑터 초기 구현
- `subtitles.js`: 자막 처리 관련 유틸리티
- `video-player-init.js`: 비디오 플레이어 초기화 코드

## 참고

이 파일들은 필요할 경우 참조용으로 보관되었으며, 이후 새로운 기능을 위한 코드 참조로 사용할 수 있습니다. 단, 실제 구현은 `video-components` 디렉토리의 최신 코드를 사용하세요. 