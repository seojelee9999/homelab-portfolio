# Argo CD 등록

`apps/portfolio.json`은 `~/homelab-argocd/apps/portfolio.json`으로 반영할 등록 정보입니다. `homelab-argocd.patch`는 이 파일 하나만 추가합니다.

- repoURL: `https://github.com/seojelee9999/homelab-portfolio.git`
- targetRevision: `main`
- manifest_path: `deploy`
- namespace / appName: `portfolio`

현재 저장소의 `deploy/` 및 bootstrap 코드는 portfolio 저장소에서 관리합니다. homelab 저장소에는 복사하지 않습니다. `scripts/install.py`는 portfolio 저장소의 게시 상태를 먼저 확인하고, homelab에는 등록 JSON 하나만 반영합니다.

기존 ApplicationSet은 `apps/*.json`을 읽으므로 ApplicationSet 자체를 수정할 필요가 없습니다. Argo CD 저장소 자격증명은 portfolio 원격 저장소를 읽을 수 있어야 합니다.

현재 homelab 경로는 이 세션에서 읽기 전용입니다. 패치 적용 검사만 수행했으며 등록 정보의 실제 적용·push는 아직 하지 않았습니다. [설치 안내](../README.md)를 참고하세요.
