# 운영과 백업

아래는 배포 이후 클러스터 접근이 가능한 관리자 터미널에서 실행하는 절차입니다. 아직 실행된 백업은 없습니다.

## 백업

이미지/파일과 DB의 시점을 맞추기 위해 앱을 maintenance mode로 전환한 뒤 백업합니다. 이 동안 사용자는 기록을 열거나 편집할 수 없습니다. 운영 업데이트나 재시작이 동시에 진행되지 않도록 하세요.

```bash
umask 077
mkdir -p backups
kubectl -n portfolio exec deployment/portfolio-bookstack -- php /app/www/artisan down
```

별도 명령으로 각각 실행하고 실패 여부를 확인합니다. DB 비밀번호는 컨테이너 환경에서만 사용합니다.

```bash
kubectl -n portfolio exec portfolio-mariadb-0 -- sh -ec \
  'MYSQL_PWD="$MARIADB_ROOT_PASSWORD" mariadb-dump -u root --single-transaction --routines --events --triggers bookstack' \
  > backups/bookstack.sql
kubectl -n portfolio exec deployment/portfolio-bookstack -- tar czf - -C /config . \
  > backups/bookstack-config.tar.gz
kubectl -n portfolio exec deployment/portfolio-bookstack -- php /app/www/artisan up
```

중간 실패가 있어도 반드시 `artisan up`으로 서비스를 복구합니다. maintenance mode는 readiness HTTP 검사도 실패시키므로 일시적으로 Argo CD가 Degraded로 보일 수 있습니다. liveness는 TCP 검사라 maintenance 자체로 재시작하지 않습니다.

백업 파일은 앱 설정·세션 등을 포함하므로 비공개 저장소로 보관합니다. 파일 크기, SQL 완료 표시, `tar tzf`로 아카이브 무결성을 확인하고 별도 매체에 복사합니다. APP_KEY 및 DB 자격증명의 원본 SSM 값도 접근 통제된 별도 비밀 저장소에 보존해야 합니다. 이 저장소에는 백업이나 비밀값을 커밋하지 마세요.

## 복구

1. 같은 BookStack/MariaDB 버전과 원본 APP_KEY를 준비합니다.
2. 별도 네임스페이스·새 PVC에 복원해 검증하는 것을 권장합니다. 운영 PVC를 지우거나 재활용하지 않습니다.
3. DB를 복원하고 앱 `/config`를 같은 백업 시점으로 복원합니다. DB 계정은 원본 비밀번호와 일치해야 합니다.
4. 백업 당시 maintenance 상태 파일이 포함될 수 있으므로 앱에서 `php /app/www/artisan up`을 실행합니다.
5. 관리자 로그인, 공개 읽기, 익명 쓰기 거부, 이미지·첨부파일, 검색을 확인한 뒤 운영 라우팅을 전환합니다.

초기화 완료 상태는 DB의 `portfolio-public-configured-v1`, `portfolio-authoring-v1` 설정과 `/config/.portfolio-initialized-v1` 파일에 저장됩니다. 둘을 포함해 복원해야 최초 설치 설정이 다시 적용되지 않습니다. 기본 `admin@admin.com/password` 계정을 다시 만들지 마세요.

## 업데이트

운영 원본은 `~/portfolio/deploy/`이며, 원격 저장소는 `seojelee9999/homelab-portfolio`입니다. 백업 후 고정 이미지 태그를 새 버전으로 변경하고 PR의 CI 검증을 통과한 뒤 main에 merge합니다. Argo CD가 해당 저장소의 `deploy/`를 동기화합니다. `~/homelab-argocd/apps/portfolio.json`은 저장소·브랜치·경로를 바꾸는 경우에만 수정합니다.

앱 시작 시 upstream 마이그레이션이 실행되므로 이전 이미지만 다시 지정하는 것으로 DB 변경을 되돌릴 수 있는 것은 아닙니다. DB 마이그레이션을 포함한 롤백은 백업 복구 계획과 함께 진행하세요.

앱은 단일 replica와 Recreate 전략을 사용하므로 업데이트 중 짧은 중단이 있습니다. 다중 replica로 변경하려면 파일 저장 방식과 세션, 마이그레이션 동시 실행부터 조정해야 합니다.

## 작성 공간 유지보수

`deploy/content`는 최초 생성용 양식입니다. 초기화 후에는 BookStack의 `작성 가이드와 양식` 책에서 템플릿을 수정합니다. Git의 초기 양식 변경을 기존 문서에 덮어쓰지 않습니다. `portfolio-authoring-v1` 설정을 지우면 전체 초기 공간이 추가 생성되므로 재생성 목적으로 삭제하지 마세요. 추가 기술은 화면에서 책을 만들고 챕터별 기본 양식을 연결합니다.

이미지 버전 변경 시 `python3 scripts/check_authoring.py`를 테스트 환경에서 실행해 내부 저장 로직 호환성을 확인합니다. 이 검사는 DB 트랜잭션 안에서 임시 문서 작성·수정·권한·중복 방지를 확인하고 전부 롤백합니다. DB 자동 증가 번호에는 빈 구간이 생길 수 있습니다.
