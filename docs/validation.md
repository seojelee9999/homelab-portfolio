# 검증 기록 — 2026-11-07

## 완료

- 기존 `~/schedule/deploy`, `~/homelab-argocd`의 ApplicationSet/Envoy Gateway/SecretStore/StorageClass 설정 확인.
- 최초 읽기 전용 SSH에서 Kubernetes 노드 3개 Ready, schedule Synced/Healthy, tunnel-gateway Programmed=True, `longhorn-database` Retain 확인. 이 조회 시점에 `/portfolio` HTTPRoute나 Argo Application은 없었습니다.
- upstream 문서 및 소스로 하위 경로 APP_URL, 쿠키 경로, 파일 접근 권한, 초기 관리자, Public 역할, 초기화 스크립트 순서 확인.
- `kubectl kustomize deploy`: 11개 리소스 렌더링 성공.
- `python3 scripts/validate.py`: 네임스페이스, 스토리지 보존, Secret 참조, 고정 이미지 태그, Gateway 및 하위 경로, 초기화 readiness 검사 통과.
- `python3 -m unittest discover -s scripts -p 'test_*.py' -v`: 총 10개 테스트 통과. Secret 생성/보존 보호 5개와 저장소 분리 검증 5개입니다. 저장소 분리 검증은 portfolio 소스 SHA 기준 배포 확인, 잘못된 소스·경로와 비정상 상태 거부, 미게시/수정 중인 소스 차단, 임시 Git 저장소에 등록 JSON 하나만 추가하고 기존 파일을 보존하는 패치 적용을 포함합니다.
- Python 스크립트 컴파일, bootstrap Bash 구문 검사 통과.
- `git -C ~/homelab-argocd apply --check ~/portfolio/gitops/homelab-argocd.patch`: 기존 저장소에 패치 적용 가능 확인. 실제 적용하지 않음.
- 저장소 분리: `gitops/apps/portfolio.json`과 생성 패치를 `homelab-portfolio`의 main `deploy/`를 읽도록 변경. 설치 스크립트도 homelab 저장소에 `apps/portfolio.json`만 반영하도록 변경.
- `.github/workflows/ci.yml` 추가: PR/main/수동 검증. 워크플로 YAML 및 각 Bash 실행 블록의 구문을 로컬 확인. GitHub에서 실제 실행하지는 않음.

## 실행하지 못한 항목

초기 조회 이후 추가 SSH 연결은 `socket: Operation not permitted`, GitHub clone은 네트워크 DNS 제한으로 실패했습니다. 기존 SSH 승인 접두사를 사용한 권한 확장 요청도 세션의 `sandbox_approval=false` 정책 때문에 자동 거절되었습니다. `~/homelab-argocd`는 현재 세션의 쓰기 허용 경로에 포함되어 있지 않습니다.

따라서 SSM 생성, GitOps 커밋·push, Kubernetes 리소스 생성, 이미지 pull, 앱/DB 실행은 수행하지 않았습니다. 로컬 PHP·Docker 실행 환경도 없어 PHP bootstrap 및 DB migration의 실제 런타임 검증은 하지 못했습니다.

portfolio 경로의 `.git`도 비어 있는 읽기 전용 디렉터리입니다. `homelab-portfolio` 원격 저장소의 생성/존재 확인·소스 게시, 새 GitHub Actions 실행, main 보호 규칙 설정은 수행하지 못했습니다. CI를 필수 검사로 지정하지 않으면 Argo CD는 main 변경을 CI 결과와 독립적으로 배포합니다.

배포 후 `scripts/smoke.py`로 외부 공개 읽기·로그인 폼·정적 파일·쿠키·관리 페이지 차단을 확인하도록 준비했습니다. 관리자 실제 로그인, 문서 생성·수정·검색, 이미지 업로드, 익명으로 해당 문서 읽기 및 수정 거부, 재시작 후 데이터 유지, 백업 복구는 아직 검증하지 않았습니다. 설치 완료 또는 운영 검증 완료로 해석하면 안 됩니다.
