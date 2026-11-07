# 검증 기록 — 2026-11-07

## 기존 운영 상태

이번 작업 시작 시 BookStack/MariaDB Pod는 각각 Running/Ready, PVC 두 개는 Bound였으며 Argo CD portfolio는 `466422d`에서 Synced/Healthy였습니다. 이전 문서의 미설치 상태는 더 이상 현재 상태가 아니어서 수정했습니다.

## 작성 공간 변경 검증

- `python3 scripts/validate.py`: 13개 리소스의 실제 Kustomize 렌더링, 초기 양식·테마 ConfigMap/볼륨 및 그림 편집 설정, readiness, 라우팅, Secret 참조 및 PVC 보호 검사 통과.
- 기존 Python 테스트 10개, Python 컴파일, Bash 구문, Git diff 공백 검사 통과.
- `python3 scripts/check_authoring.py`: 실행 중인 고정 BookStack 이미지에서 PHP 구문과 실제 MariaDB 통합 검증 통과. 8개 책·28개 챕터, 챕터별 기본 양식과 28개 초안 자동 입력, Markdown 저장·수정, 변경 이력과 검색용 본문, 하위 경로 작성 링크, 반복 실행 시 사용자 양식·홈 설정 보존, 익명 읽기 허용·쓰기 거부를 확인했습니다. 작업 노트 용어와 기존 시작 안내의 그림·사진 설명 갱신도 확인했습니다. 전체 DB 변경은 롤백하고 기존 문서 수·초기화 표시·홈페이지 설정 복원을 확인했습니다.
- `python3 scripts/smoke.py`: 운영 주소의 공개 읽기, 로그인/CSRF 폼, 쿠키 보안·경로, 앱 정적 파일, 익명 관리·작성 접근 차단, 공개 가입 차단 검사 통과. 실제 응답에 맞춰 Cloudflare 분석 beacon을 앱 정적 파일 검사에서 제외하고, BookStack 공개 모드의 권한 거부 홈 리다이렉트를 검사하도록 수정했습니다.
- CI에는 새 통합 검증 PHP 파일의 구문 검사를 추가했습니다. 실제 DB 통합 검사는 명시적으로 실행하며 CI에서 운영 클러스터에 접속하지 않습니다.

## 검증 범위

실제 브라우저의 관리자 로그인·이미지/파일 업로드·시각적 배치, 백업 복구는 이번 자동 검증에 포함하지 않았습니다. Markdown 작성 로직은 운영 런타임의 DB 트랜잭션에서 검증했습니다. 자동 백업은 별도 구성 사항입니다. 초기화는 앱 내부 repository API를 사용하므로 BookStack 이미지 버전을 바꿀 때 통합 검증을 다시 실행해야 합니다.
