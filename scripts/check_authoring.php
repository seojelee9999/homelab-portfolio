<?php
declare(strict_types=1);

use BookStack\Entities\Models\Book;
use BookStack\Entities\Models\Chapter;
use BookStack\Entities\Models\Page;
use BookStack\Entities\Repos\PageRepo;
use BookStack\Settings\SettingService;
use BookStack\Users\Models\User;
use Illuminate\Contracts\Console\Kernel;
use Illuminate\Support\Facades\DB;

require '/app/www/vendor/autoload.php';
$app = require '/app/www/bootstrap/app.php';
$app->make(Kernel::class)->bootstrap();
require __DIR__ . '/authoring.php';

function expect(bool $condition, string $message): void
{
    if (!$condition) {
        throw new RuntimeException($message);
    }
}

$settings = app(SettingService::class);
$counts = fn () => [Book::count(), Chapter::count(), Page::count()];
$before = $counts();
$oldMarker = $settings->get('portfolio-authoring-v1', false);
$oldHomepage = $settings->get('app-homepage');
DB::beginTransaction();
try {
    $settings->remove('portfolio-authoring-v1');
    $settings->remove('portfolio-work-notes-v1');
    $settings->put('app-homepage-type', 'default');
    $seed = seedPortfolioAuthoring(__DIR__ . '/content');
    configurePortfolioWorkNotes();
    $terms = require __DIR__ . '/theme/lang/ko/entities.php';
    expect($terms['books'] === '기술 분류' && $terms['shelves'] === '작업 공간', 'Work-note terminology missing');
    expect($seed['created'] && count($seed['books']) === 8 && count($seed['chapters']) === 28,
        'Workspace hierarchy mismatch');
    expect($settings->get('app-homepage-type') === 'page', 'Homepage not selected');
    $home = Page::findOrFail($seed['home']);
    expect(str_contains($home->markdown, '구성도 / 그림 그리기') && !str_contains($home->markdown, '책이나'),
        'Work-note guide upgrade failed');
    expect(str_contains($home->html, '/portfolio/books/') && str_contains($home->html, '/create-page'),
        'Subpath authoring links missing');
    $repo = app(PageRepo::class);
    foreach ($seed['chapters'] as $id) {
        $chapter = Chapter::findOrFail($id);
        $template = Page::findOrFail($chapter->default_template_id);
        $draft = $repo->getNewDraftPage($chapter);
        expect($draft->draft && $draft->markdown === $template->markdown, 'Draft template not prefilled');
    }
    $draft = $repo->getNewDraftPage(Chapter::findOrFail($seed['chapters'][0]));
    $page = $repo->publishDraft($draft, ['name' => '검증 기록', 'markdown' => "## OpenStack 확인\n\n```bash\nopenstack server list\n```"]);
    expect(!$page->draft && str_contains($page->html, 'openstack server list'), 'Markdown publish failed');
    $repo->update($page, ['name' => '검증 기록 수정', 'markdown' => '검증 결과를 수정했습니다.', 'changelog' => '검증']);
    $page->refresh();
    expect($page->revisions()->count() >= 2 && str_contains($page->text, '검증 결과'), 'Revision or searchable content missing');
    $template = Page::findOrFail($seed['templates']['build']);
    $repo->update($template, ['markdown' => '사용자가 변경한 양식']);
    $settings->put('app-homepage-type', 'books');
    $seededCounts = $counts();
    expect(seedPortfolioAuthoring(__DIR__ . '/content') === ['created' => false], 'Second run was not skipped');
    expect($counts() === $seededCounts && $template->fresh()->markdown === '사용자가 변경한 양식'
        && $settings->get('app-homepage-type') === 'books', 'User edits or settings overwritten');
    $settings->remove('portfolio-authoring-v1');
    seedPortfolioAuthoring(__DIR__ . '/content');
    expect($settings->get('app-homepage-type') === 'books', 'Existing custom homepage overwritten');
    auth()->setUser(User::getGuest());
    expect(userCan('page-view', $home), 'Guest cannot read guide');
    expect(!userCan('page-update', $home) && !userCan('page-create', $home->book), 'Guest can write');
    DB::rollBack();
    $settings->flushCache();
    expect($counts() === $before && $settings->get('portfolio-authoring-v1', false) === $oldMarker
        && $settings->get('app-homepage') === $oldHomepage, 'Rollback did not restore state');
    echo "PASS: hierarchy, 28 prefilled drafts, Markdown save/edit/revisions, subpath links, repeat-run preservation, guest permissions; all DB changes rolled back.\n";
} catch (Throwable $error) {
    while (DB::transactionLevel() > 0) {
        DB::rollBack();
    }
    fwrite(STDERR, 'Authoring check failed: ' . get_class($error) . ' at ' . basename($error->getFile()) . ':' . $error->getLine() . "\n");
    exit(1);
}
