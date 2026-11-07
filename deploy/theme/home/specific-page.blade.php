@extends('layouts.base')
@push('body-class', 'notes-layout ')
@section('content')
@if($customHomepage->name !== '홈랩 기록 시작하기')
    <main id="main-content" class="notes-shell"><div class="card content-wrap page-content" component="page-display" option:page-display:page-id="{{ $customHomepage->id }}">@include('pages.parts.page-display', ['page' => $customHomepage])</div></main>
@else
@php
    $queries = app(\BookStack\Entities\Queries\EntityQueries::class);
    $topics = $queries->books->visibleForList()->where('id', '!=', $customHomepage->book_id)->orderBy('name')->get();
    $chapters = $queries->chapters->visibleForList()->whereIn('book_id', $topics->pluck('id'))->orderBy('priority')->get()->groupBy('book_id');
    $notesQuery = $queries->pages->visibleForList()->where('draft', false)->where('template', false)->where('book_id', '!=', $customHomepage->book_id);
    $noteCount = (clone $notesQuery)->count();
    $counts = (clone $notesQuery)->reorder()->select('book_id')->selectRaw('COUNT(*) AS total')->groupBy('book_id')->pluck('total', 'book_id');
    $recent = (clone $notesQuery)->orderByDesc('updated_at')->limit(5)->get();
    $drafts = user()->isGuest() ? collect() : $queries->pages->currentUserDraftsForList()->orderByDesc('updated_at')->limit(4)->get();
    $templates = $queries->pages->visibleTemplates()->where('book_id', $customHomepage->book_id)->orderBy('priority')->get();
    $guide = $queries->books->findVisibleById($customHomepage->book_id);
    $topicNames = $topics->pluck('name', 'id');
    $canWrite = !user()->isGuest() && $chapters->flatten()->contains(fn ($chapter) => userCan('page-create', $chapter));
@endphp
<main id="main-content" class="notes-shell" data-notes-dashboard>
    <div class="notes-breadcrumb"><span class="notes-square"></span> HOMELAB NOTES <span>/</span> 작업 공간</div>
    <section class="notes-hero" aria-labelledby="notes-title">
        <div class="notes-hero-copy">
            <div class="notes-eyebrow">나의 인프라, 나의 기록</div>
            <h1 id="notes-title">만들고, 고치고.<br><span>기록으로 남기기.</span></h1>
            <p>작은 설정 변경부터 복잡한 장애 해결까지.<br>코드, 구성도, 스크린샷으로 홈랩의 경험을 쌓아보세요.</p>
            <div class="notes-actions">
                <a class="notes-button notes-button-primary" href="{{ $canWrite ? '#write' : url('/login') }}"><span aria-hidden="true">＋</span> {{ $canWrite ? '작업 기록하기' : '로그인하고 기록하기' }}</a>
                @if($guide)<a class="notes-button notes-button-quiet" href="{{ $guide->getUrl() }}">작성 양식 살펴보기 <span aria-hidden="true">↗</span></a>@endif
            </div>
            <div class="notes-capabilities"><span>Markdown</span><span>구성도 그리기</span><span>사진 첨부</span></div>
        </div>
        @include('notes.topology')
    </section>
    <div class="notes-overview" aria-label="기록 현황">
        <div><strong>{{ $noteCount }}</strong><span>쌓아온 작업 노트</span></div>
        <div><strong>{{ $topics->count() }}</strong><span>기술 분류</span></div>
        <div class="notes-overview-message"><span class="notes-dot"></span><span>다음 작업의 시작점이 되는 기록</span></div>
    </div>
    <div class="notes-columns">
        <div class="notes-main-column">
            <section class="notes-section" id="write" aria-labelledby="topics-title">
                <div class="notes-section-heading"><div><span class="notes-section-kicker">EXPLORE YOUR STACK</span><h2 id="topics-title">기술별 작업 공간</h2></div><a href="{{ url('/books') }}">전체 보기 <span aria-hidden="true">↗</span></a></div>
                <div class="notes-topic-grid">
                @forelse($topics as $topic)
                    @php $writableChapters = ($chapters[$topic->id] ?? collect())->filter(fn ($chapter) => !user()->isGuest() && userCan('page-create', $chapter)); @endphp
                    <article class="notes-topic">
                        <a href="{{ $topic->getUrl() }}" class="notes-topic-main">
                            <div class="notes-topic-top"><span class="notes-topic-icon">@include('notes.icon', ['name' => $topic->name])</span><span class="notes-count">{{ $counts[$topic->id] ?? 0 }}개의 기록</span></div>
                            <h3>{{ $topic->name }}</h3><p>{{ $topic->description ?: '작업 과정과 배운 내용을 기록하는 공간' }}</p>
                            <span class="notes-topic-open">기록 살펴보기 <span aria-hidden="true">↗</span></span>
                        </a>
                        @if($writableChapters->isNotEmpty())
                            <details class="notes-write-menu"><summary>새 기록 작성 <span aria-hidden="true">＋</span></summary><div class="notes-write-options">@foreach($writableChapters as $chapter)<a href="{{ $chapter->getUrl('/create-page') }}">{{ $chapter->name }} <span aria-hidden="true">→</span></a>@endforeach</div></details>
                        @elseif(!user()->isGuest() && userCan('page-create', $topic))
                            <a class="notes-direct-write" href="{{ $topic->getUrl('/create-page') }}">새 작업 노트 ＋</a>
                        @endif
                    </article>
                @empty
                    <div class="notes-empty"><h3>첫 기술 분류를 만들어보세요.</h3><p>기술별로 공간을 나누면 작업 기록을 다시 찾기 쉬워집니다.</p>@if(userCan('book-create-all'))<a class="notes-button notes-button-primary" href="{{ url('/create-book') }}">기술 분류 추가</a>@endif</div>
                @endforelse
                </div>
            </section>
            <section class="notes-section" aria-labelledby="recent-title">
                <div class="notes-section-heading"><div><span class="notes-section-kicker">WORK IN PROGRESS</span><h2 id="recent-title">최근 작업 기록</h2></div><a href="{{ url('/search') }}">기록 검색 <span aria-hidden="true">↗</span></a></div>
                <div class="notes-panel">
                @forelse($recent as $note)
                    <a class="notes-entry" href="{{ $note->getUrl() }}"><span class="notes-entry-icon" aria-hidden="true">↳</span><span><small>{{ $topicNames[$note->book_id] ?? '작업 노트' }}</small><strong>{{ $note->name }}</strong><span class="notes-entry-excerpt">{{ \Illuminate\Support\Str::limit($note->text, 95) }}</span></span><time datetime="{{ $note->updated_at->toIso8601String() }}">{{ $note->updated_at->format('m.d') }}</time></a>
                @empty
                    <div class="notes-empty"><span class="notes-empty-icon" aria-hidden="true">⌘</span><h3>첫 번째 작업 기록을 기다리고 있어요.</h3><p>오늘 바꾼 설정 한 줄, 해결한 오류 하나부터 시작해보세요.<br>저장한 작업 노트가 이곳에 모입니다.</p><a href="{{ $canWrite ? '#write' : url('/login') }}">{{ $canWrite ? '기술을 선택하고 시작하기' : '로그인하고 첫 기록 남기기' }} <span aria-hidden="true">→</span></a></div>
                @endforelse
                </div>
            </section>
        </div>
        <aside class="notes-aside" aria-label="작성 도구">
            @if($drafts->isNotEmpty())
            <section class="notes-panel notes-side-card"><div class="notes-side-heading"><h2>이어서 작성하기</h2><span class="notes-count">초안</span></div>@foreach($drafts as $draft)<a class="notes-draft" href="{{ $draft->getUrl('/edit') }}"><strong>{{ $draft->name }}</strong><small>{{ $draft->updated_at->diffForHumans() }} 수정 <span aria-hidden="true">↗</span></small></a>@endforeach</section>
            @endif
            <section class="notes-panel notes-side-card"><span class="notes-section-kicker">START WITH A TEMPLATE</span><h2>빈 화면 대신, 작성 양식</h2><p>어떤 작업인지 골라보세요.<br>필요한 항목이 미리 준비되어 있어요.</p><div class="notes-template-list">@foreach($templates as $template)<a href="{{ $template->getUrl() }}"><span class="notes-template-icon" aria-hidden="true">≡</span><span>{{ str_replace(' 양식', '', $template->name) }}</span><span aria-hidden="true">↗</span></a>@endforeach</div></section>
            <section class="notes-tip"><div class="notes-tip-label"><span aria-hidden="true">✳</span> 기록을 더 생생하게</div><h2>말로 설명하기 어려울 땐,<br>그림 한 장.</h2><p>편집기에서 네트워크 구성도를 그리고, 작업 중 찍은 스크린샷을 함께 넣어보세요.</p><div class="notes-mini-diagram" aria-hidden="true"><span>CLIENT</span><i>→</i><span>GATEWAY</span><i>→</i><span>SERVICE</span></div><a href="{{ $customHomepage->getUrl() }}">사진·구성도 작성 안내 <span aria-hidden="true">↗</span></a></section>
            <div class="notes-side-foot">기록은 작게 시작해도 괜찮아요.<br>다음의 내가 이해할 수 있다면 충분합니다.</div>
        </aside>
    </div>
    <footer class="notes-footer"><span>HOMELAB NOTES</span><span>Build. Break. Learn. Document.</span></footer>
</main>
@endif
@endsection
