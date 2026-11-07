# Homelab Notes — BookStack

학습·트러블슈팅 기록을 위한 BookStack 배포 구성입니다. 대상 주소는 **https://akibaha.shop/portfolio/** 입니다.

**현재 상태: 배포 파일 준비 및 로컬 검증 완료. 클러스터 설치·Git push·관리자 계정 생성은 아직 실행하지 못했습니다.** 상세한 검증 범위는 [docs/validation.md](docs/validation.md)에 있습니다.

## 사용 방식

- 비로그인 방문자: 공개된 문서 열람·검색. 작성·수정·삭제·댓글·API·변경 이력 접근 권한 없음.
- 관리자: `lsj2sj03@gmail.com`으로 로그인하여 문서 작성, 이미지·파일 첨부, 분류, 권한 관리.
- 공개 회원가입: 비활성화. 추가 작성자가 필요하면 관리자가 계정을 생성하고 역할을 부여합니다.
- 기본 언어: 한국어. 기본 편집기: Markdown. 화면 이름: Homelab Notes.
- 책·챕터·페이지별로 공개 범위를 조정할 수 있습니다. 이미지도 페이지 권한을 따르는 `local_secure_restricted` 저장 방식을 사용합니다.

권장 구조: `홈랩` 책장 아래 `Kubernetes`, `네트워크`, `CI/CD`, `Linux` 책을 만들고 각 책에서 `학습`, `트러블슈팅` 챕터를 사용하세요. [학습 양식](templates/learning.md)과 [트러블슈팅 양식](templates/troubleshooting.md)을 새 페이지에 붙여 넣고 페이지 템플릿으로 저장하면 재사용할 수 있습니다. 양식 파일은 제공했으며 서버에 콘텐츠를 자동 생성하지는 않습니다.

## 구성

| 항목 | 설정 |
| --- | --- |
| 앱 | LinuxServer BookStack `v26.09.2-ls295`, 1개, Recreate 배포 |
| DB | MariaDB `11.4.13`, 전용 StatefulSet, 비관리자 앱 계정 |
| 저장소 | `longhorn-database`: DB 10Gi + 앱/첨부파일 5Gi, Namespace/PVC prune·delete 보호 |
| Secrets | AWS SSM `/homelab/portfolio/*` → 기존 ESO ClusterSecretStore |
| 라우팅 | 기존 `gateway-system/tunnel-gateway`의 `http` listener |
| GitOps | `homelab-argocd/apps/portfolio.json` → `homelab-portfolio` 저장소 main의 `deploy/` |

기존 `schedule`처럼 앱 저장소와 Argo CD 등록 저장소를 분리합니다.

```text
~/portfolio/                       # github.com/seojelee9999/homelab-portfolio
  deploy/                          # 운영 매니페스트와 bootstrap 코드
  .github/workflows/ci.yml          # PR/main 검증
  scripts/                         # 설치 및 검증 도구
  templates/                       # 학습·트러블슈팅 양식
  gitops/apps/portfolio.json        # homelab에 등록할 파일의 원본

~/homelab-argocd/                   # github.com/seojelee9999/homelab-argocd
  apps/portfolio.json              # 앱 저장소 URL, main, deploy 경로만 등록
```

BookStack 본체는 upstream 이미지를 사용하고, 현재 저장소에서 초기화 PHP/Bash 코드와 Kubernetes 매니페스트를 관리합니다. 앱 이미지를 직접 빌드·게시하는 GHCR 파이프라인은 없습니다. 운영 변경은 `~/portfolio/deploy/`에서 수행하며 homelab 저장소에 매니페스트를 복사하지 않습니다.

## CI/CD

`.github/workflows/ci.yml`은 PR, main push, 수동 실행 시 Python/Bash 구문, 실제 Kustomize 렌더링, 설치 보호 로직 테스트, 등록 패치 일치 여부, 배포 이미지의 PHP 구문을 검사합니다. 런타임 DB 통합 검증이나 운영 클러스터 접근은 이 CI에 포함하지 않습니다.

CD는 기존 ApplicationSet이 생성하는 Argo CD Application이 담당합니다. 등록된 앱 저장소의 main `deploy/`를 읽고 auto-sync/prune/selfHeal합니다. CI가 클러스터 자격증명을 보유하거나 homelab 저장소에 매번 커밋할 필요는 없습니다.

**Argo CD는 GitHub Actions 완료를 기다리지 않습니다.** CI 통과 후에만 배포하려면 GitHub main 보호 규칙에서 `validate` 상태 검사를 필수로 지정하고, PR merge만 허용하며 직접 push/우회를 제한해야 합니다. 워크플로 파일은 준비했지만 GitHub 원격 저장소 생성, CI 실행, 브랜치 보호 규칙 설정은 아직 수행하지 않았습니다.

`/portfolio`는 HTTPS 443의 `/portfolio/`로 리다이렉트됩니다. Gateway는 `/portfolio` 접두사를 제거하고 앱에 전달하며, 앱의 `APP_URL`은 외부 전체 주소를 유지합니다. 세션 이름은 `portfolio_session`, 쿠키 경로는 APP_URL에서 계산된 `/portfolio`, Secure/HttpOnly/SameSite=lax입니다.

## 설치

현재 작업 세션은 homelab 저장소 쓰기와 추가 네트워크 작업을 허용하지 않습니다. 다음 명령은 해당 권한이 있는 로컬 터미널에서 실행할 수 있도록 준비했습니다. 스크립트는 SSM에 필요한 비밀값을 생성하고, 지정한 GitOps 파일만 커밋·push하며 Argo CD와 외부 HTTP 응답을 확인합니다.

사전 조건:

- 로컬 `python3`, PyYAML, `kubectl`, Git, SSH.
- `~/portfolio`: 별도 Git 저장소의 main 브랜치. origin은 `git@github.com:seojelee9999/homelab-portfolio.git` 또는 같은 저장소의 HTTPS URL. 모든 소스가 커밋·push되어 로컬 HEAD와 origin/main이 일치해야 합니다.
- `~/homelab-argocd`: main 브랜치, 미커밋 추적 파일·staged 파일·미게시 커밋 없음. 다른 경로의 untracked 파일은 건드리지 않습니다.
- Argo CD의 기존 repository credentials가 `https://github.com/seojelee9999/homelab-portfolio.git`을 읽을 수 있어야 합니다. private 저장소라면 해당 저장소 접근 권한을 추가합니다.
- 기존 키로 `ubuntu@192.168.55.10` SSH 및 GitHub 저장소 push 가능.
- cp-01에 기존 `kubectl`, Python boto3, `homelab-eso` AWS 프로필.
- AWS 프로필: 새 경로에 `ssm:GetParameter`, `ssm:PutParameter` 및 KMS 권한. ESO identity도 새 경로 읽기·복호화 가능. 쓰기 권한이 없으면 Secret 생성 단계에서 중단됩니다.
- 기존 ApplicationSet, Gateway, ESO, Longhorn 정상. PV 요청량 15Gi에 Longhorn 복제본과 여유 공간을 고려한 실제 디스크 공간 필요.

먼저 GitHub에 `seojelee9999/homelab-portfolio` 저장소를 준비하고 현재 디렉터리의 전체 파일을 main으로 게시합니다. 이 작업 세션의 `.git`은 비어 있는 읽기 전용 디렉터리라 여기서 Git 초기화·원격 등록은 수행하지 못했습니다. 쓰기 권한이 있는 로컬 터미널에서, 아직 저장소가 초기화되지 않은 경우 다음 순서로 준비합니다.

```bash
cd ~/portfolio
git init -b main
git remote add origin git@github.com:seojelee9999/homelab-portfolio.git
git add .gitignore README.md .github deploy docs gitops scripts templates
git commit -m 'Add BookStack portfolio deployment and validation CI'
git push -u origin main
```

이미 Git 저장소인 경우 재초기화나 origin 중복 추가 없이 기존 설정을 확인합니다. GitHub CI가 통과한 다음 등록합니다.

```bash
cd ~/portfolio
python3 scripts/install.py --admin-email lsj2sj03@gmail.com
```

진행 순서:

1. 실제 Kustomize 렌더링과 배포 규칙 검사. portfolio 소스가 독립 저장소이고 origin/main에 게시되었는지 확인한 뒤 GitOps/클러스터 사전 확인.
2. SSM SecureString 5개 준비. 기존 값은 재사용하고 덮어쓰지 않습니다. 이미 PVC가 있는데 Secret이 없으면 복구를 요구하며 중단합니다.
3. homelab 저장소에 `apps/portfolio.json`만 커밋·push.
4. Argo CD가 portfolio 저장소의 `deploy/`에서 DB → 앱 → Route 순서로 동기화.
5. 앱 초기화에서 기본 관리자 계정을 무작위 비밀번호와 지정한 이메일로 교체하고 Public 역할에는 읽기 권한만 부여합니다. 초기화 완료 전에는 readiness가 통과하지 않습니다.
6. portfolio 저장소의 게시 SHA를 기준으로 Argo CD Healthy/Synced와 앱 소스 경로를 확인하고, 외부 HTTP 읽기·로그인 폼·정적 파일·쿠키·비로그인 관리 접근 제한 검사.

실패 시 자동으로 기존 PVC나 SSM 값을 삭제하지 않습니다. Git push 실패 후에는 로컬 커밋을 확인하고 정상적으로 push한 뒤 Argo CD를 확인하세요. 강제 push나 자동 재설정은 하지 않습니다. 최초 설치용 스크립트이므로 기존 앱 등록 정보가 다르면 덮어쓰지 않고 중단합니다. 설치 확인 중 portfolio main이 갱신되면 확인 중인 SHA와 달라질 수 있으므로 설치가 끝날 때까지 추가 게시를 피하세요.

패치로 직접 반영하려면 아래 순서로 수행합니다. 패치에는 `apps/portfolio.json` 하나만 들어 있습니다. 이 경우에도 portfolio 소스 게시와 CI 통과, Argo CD의 해당 저장소 읽기 권한 준비를 먼저 완료해야 합니다.

```bash
python3 scripts/prepare_patch.py
git -C ~/homelab-argocd apply --check ~/portfolio/gitops/homelab-argocd.patch
# SSM 준비는 동일하게 먼저 수행해야 합니다.
ssh -F /dev/null -i ~/.ssh/id_ed25519 -o IdentitiesOnly=yes ubuntu@192.168.55.10 \
  'python3 - --admin-email lsj2sj03@gmail.com' < scripts/bootstrap_secrets.py
git -C ~/homelab-argocd apply ~/portfolio/gitops/homelab-argocd.patch
git -C ~/homelab-argocd add apps/portfolio.json
git -C ~/homelab-argocd commit -m 'Register portfolio application'
git -C ~/homelab-argocd push origin main
```

## 최초 로그인

설치 성공 후 관리자 이메일은 `lsj2sj03@gmail.com`입니다. 초기 비밀번호는 SSM에만 생성됩니다. 본인 터미널에서 아래 명령으로 확인한 뒤 프로필에서 비밀번호를 변경하세요.

```bash
ssh -F /dev/null -i ~/.ssh/id_ed25519 -o IdentitiesOnly=yes ubuntu@192.168.55.10 \
  'aws --profile homelab-eso --region ap-northeast-2 ssm get-parameter --name /homelab/portfolio/INITIAL_ADMIN_PASSWORD --with-decryption --query Parameter.Value --output text'
```

이메일은 로그인 ID입니다. SMTP는 구성하지 않았으므로 비밀번호 재설정 이메일 발송은 아직 사용할 수 없습니다. 계정 복구가 필요하면 BookStack의 `bookstack:create-admin` 명령을 Pod 안에서 대화형으로 실행할 수 있습니다. 재시작해도 관리자가 변경한 비밀번호·이메일·공개 설정을 초기값으로 되돌리지 않습니다.

## 점검과 운영

```bash
python3 scripts/validate.py
python3 -m unittest discover -s scripts -p 'test_*.py' -v
python3 scripts/smoke.py  # 실제 설치 후 실행
kubectl -n argocd get application portfolio
kubectl -n portfolio get pods,pvc,externalsecrets
kubectl -n portfolio describe httproute portfolio
kubectl -n portfolio logs deployment/portfolio-bookstack --tail=100
```

Route의 Accepted/ResolvedRefs=True, PVC Bound, ExternalSecret Ready=True를 확인합니다. BookStack 초기화가 실패하면 Pod가 Ready가 되지 않고 Route가 외부에 공개되지 않거나 503을 반환합니다. SSM 정책, DB 준비 상태, 이미지 다운로드, bootstrap 호환성을 확인하세요. bootstrap Secret이 바뀐 경우 앱 재시작이 필요합니다.

초기 DB 비밀번호는 빈 DB에서만 사용됩니다. 이후 SSM만 바꾸면 DB와 비밀번호가 불일치합니다. DB 계정 변경, SSM 갱신, ESO 동기화, 앱 재시작을 함께 수행해야 합니다. APP_KEY는 기존 데이터를 계속 복호화하는 데 필요하므로 재생성하지 마세요.

DB 덤프, `/config` 전체(첨부파일·설정), APP_KEY를 함께 백업해야 복구할 수 있습니다. Longhorn 복제는 별도 백업을 대신하지 않습니다. **자동 백업은 이번 구성에 포함하지 않았습니다.** [백업·복구 절차](docs/operations.md)를 참고하세요.

## 참고

- [BookStack 설치 및 Docker 이미지 안내](https://www.bookstackapp.com/docs/admin/installation/)
- [BookStack 권한](https://www.bookstackapp.com/docs/user/roles-and-permissions/)
- [하위 경로 설치](https://www.bookstackapp.com/docs/admin/subdirectory-setup/)
- [이미지 접근 권한을 포함한 파일 저장 방식](https://www.bookstackapp.com/docs/admin/upload-config/)
- [LinuxServer BookStack 설정](https://docs.linuxserver.io/images/docker-bookstack/)
- [BookStack 이미지 릴리스](https://github.com/linuxserver/docker-bookstack/releases)
