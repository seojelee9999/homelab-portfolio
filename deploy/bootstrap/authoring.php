<?php
declare(strict_types=1);

use BookStack\Entities\Repos\BookRepo;
use BookStack\Entities\Repos\BookshelfRepo;
use BookStack\Entities\Repos\ChapterRepo;
use BookStack\Entities\Repos\PageRepo;
use BookStack\Settings\SettingService;
use BookStack\Users\Models\User;
use Illuminate\Contracts\Console\Kernel;
use Illuminate\Support\Facades\DB;

/** One transaction, one version marker. Never reconcile user-edited content. */
function seedPortfolioAuthoring(string $contentPath): array
{
    $settings = app(SettingService::class);
    $marker = 'portfolio-authoring-v1';
    if ($settings->get($marker, false)) {
        return ['created' => false];
    }
    $admin = User::query()->whereHas('roles', fn ($q) => $q->where('system_name', 'admin'))
        ->orderBy('id')->firstOrFail();
    auth()->setUser($admin);

    $types = [
        'build' => '구축 기록', 'troubleshooting' => '트러블슈팅',
        'learning' => '학습 노트', 'stack' => '기술 스택',
    ];
    $markdown = [];
    foreach ($types as $key => $name) {
        $text = file_get_contents($contentPath . '/' . $key . '.md');
        if ($text === false || trim($text) === '') {
            throw new RuntimeException('Missing authoring template: ' . $key);
        }
        $markdown[$key] = $text;
    }

    return DB::transaction(function () use ($settings, $marker, $types, $markdown): array {
        $books = app(BookRepo::class);
        $chapters = app(ChapterRepo::class);
        $pages = app(PageRepo::class);
        $guide = $books->create([
            'name' => '작성 가이드와 양식',
            'description' => '홈랩 기록 시작하기 · 재사용 가능한 Markdown 양식',
        ]);
        $templates = [];
        foreach ($types as $key => $name) {
            $templates[$key] = $pages->publishDraft($pages->getNewDraftPage($guide), [
                'name' => $name . ' 양식', 'markdown' => $markdown[$key], 'template' => 'true',
                'tags' => [['name' => '문서 유형', 'value' => '양식']],
            ]);
            if (!$templates[$key]->template) {
                throw new RuntimeException('Template permission missing');
            }
        }
        $topics = [
            '홈랩' => '전체 구성도, 하드웨어, 가상화와 구축 여정',
            '네트워크' => 'VLAN, 라우팅, DNS, 방화벽, 로드밸런서와 패킷 흐름',
            'OpenStack' => 'Keystone, Nova, Neutron, Glance, Cinder와 클라우드 운영',
            'Kubernetes' => '클러스터, 워크로드, CNI, Gateway와 운영',
            'Linux' => '운영체제, 시스템 서비스, 권한과 성능 분석',
            '스토리지' => 'Ceph, Longhorn, 볼륨, 데이터베이스와 백업·복구',
            '자동화 · GitOps' => 'Ansible, Terraform, CI/CD와 Argo CD',
        ];
        $bookIds = [$guide->id];
        $chapterIds = [];
        $home = "# 홈랩 기술 기록\n\n직접 구축하고, 문제를 해결하고, 배운 내용을 쌓아가는 기술 지식 저장소입니다.\n\n";
        $home .= '기록을 남기려면 [로그인](' . url('/login') . ")한 뒤 아래 표에서 작성할 항목을 선택하세요. 새 문서에는 해당 양식이 자동으로 채워집니다.\n\n";
        $home .= "## 기술별 기록과 작성\n\n| 기술 / 기록 보기 | 구축 기록 | 트러블슈팅 | 학습 노트 | 기술 스택 |\n| --- | --- | --- | --- | --- |\n";
        foreach ($topics as $name => $description) {
            $book = $books->create(['name' => $name, 'description' => $description,
                'tags' => [['name' => '기술', 'value' => $name]]]);
            $bookIds[] = $book->id;
            $home .= '| [' . $name . '](' . $book->getUrl() . ') |';
            foreach ($types as $key => $chapterName) {
                $chapter = $chapters->create([
                    'name' => $chapterName,
                    'description' => $name . ' ' . $chapterName . '을 기록하는 공간입니다.',
                    'default_template_id' => $templates[$key]->id,
                ], $book);
                if ((int) $chapter->default_template_id !== $templates[$key]->id) {
                    throw new RuntimeException('Default template was not assigned');
                }
                $chapterIds[] = $chapter->id;
                $home .= ' [작성](' . $chapter->getUrl('/create-page') . ') |';
            }
            $home .= "\n";
        }
        $shelf = app(BookshelfRepo::class)->create([
            'name' => '홈랩 기술 기록', 'description' => '구축부터 운영과 문제 해결까지, 기술별로 쌓는 나의 홈랩 기록',
        ], $bookIds);
        $home .= "\n## 기록하는 방법\n\n";
        $home .= "1. 기술과 문서 유형을 선택하고 제목을 구체적으로 적습니다. 예: `Neutron 외부 네트워크 연결 실패 해결`.\n";
        $home .= "2. Markdown 편집기에서 양식을 채웁니다. 코드 블록에는 언어를 지정하고, 스크린샷과 로그 파일은 편집기의 이미지·첨부 기능으로 추가합니다.\n";
        $home .= "3. 태그에 `기술: OpenStack`, `상태: 해결`, `환경: 홈랩`처럼 이름과 값을 넣으면 관련 문서를 모아 찾기 쉽습니다.\n";
        $home .= "4. 저장한 뒤 검색과 변경 이력으로 기록을 다시 찾거나 이전 내용을 확인합니다. 작업 중인 새 페이지는 초안으로 남길 수 있습니다.\n\n";
        $home .= "## 문서 유형 선택\n\n- **구축 기록**: 목표 → 구성도 → 설치·설정 → 검증 → 롤백\n- **트러블슈팅**: 증상 → 증거 → 가설 검증 → 원인 → 해결 → 재발 방지\n- **학습 노트**: 개념 → 동작 흐름 → 실습 → 배운 점\n- **기술 스택**: 역할 → 선택 이유 → 구성 → 운영 방법\n\n";
        $home .= '다른 양식이 필요하면 편집기 사이드바의 **템플릿**에서 선택하세요. [전체 양식](' . $guide->getUrl() . ")은 직접 수정해 재사용할 수 있습니다.\n\n";
        $home .= "## 공개 범위\n\n현재 공개 문서는 로그인 없이 읽을 수 있고, 작성·수정은 권한이 있는 계정만 가능합니다. 비공개 기록은 책이나 페이지의 권한에서 공개 역할의 열람을 해제한 후 작성하세요. 토큰·비밀번호·개인정보는 로그와 설정에서 제거하세요.\n";
        $landing = $pages->publishDraft($pages->getNewDraftPage($guide), [
            'name' => '홈랩 기록 시작하기', 'markdown' => $home,
        ]);
        // Preserve an explicitly selected home page on an existing installation.
        if ($settings->get('app-homepage-type') === 'default') {
            $settings->put('app-homepage', $landing->id . ':' . $landing->slug);
            $settings->put('app-homepage-type', 'page');
        }
        $settings->put($marker, 'true');
        return ['created' => true, 'books' => $bookIds, 'chapters' => $chapterIds,
            'templates' => array_map(fn ($p) => $p->id, $templates),
            'home' => $landing->id, 'shelf' => $shelf->id];
    });
}

// The callable function is reused by the rollback-only integration check.
if (realpath($_SERVER['SCRIPT_FILENAME'] ?? '') === __FILE__) {
    try {
        require '/app/www/vendor/autoload.php';
        $app = require '/app/www/bootstrap/app.php';
        $app->make(Kernel::class)->bootstrap();
        $lock = DB::selectOne("SELECT GET_LOCK('portfolio-authoring-v1', 30) AS acquired");
        if ((int) $lock->acquired !== 1) {
            throw new RuntimeException('Authoring initialization is already running');
        }
        $result = seedPortfolioAuthoring(getenv('PORTFOLIO_CONTENT_PATH') ?: '/portfolio-content');
        DB::selectOne("SELECT RELEASE_LOCK('portfolio-authoring-v1')");
        echo $result['created'] ? "Portfolio authoring workspace created.\n" : "Portfolio authoring workspace already initialized; content preserved.\n";
    } catch (Throwable $error) {
        fwrite(STDERR, 'Portfolio authoring setup failed (' . get_class($error) . "); readiness remains disabled.\n");
        exit(1);
    }
}
