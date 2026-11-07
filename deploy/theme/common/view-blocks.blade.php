{{-- Keep actions, search, drafts and updates; omit reading-history/popularity blocks. --}}
@php
    $sectionVars = get_defined_vars();
    $hiddenBlocks = [
        'HomeRecentlyViewedOrRecentBooks',
        'BooksIndexRecents', 'BooksIndexPopular',
        'ShelvesIndexRecents', 'ShelvesIndexPopular',
    ];
@endphp
@foreach($viewBlocks->getInstancesForLocationAndPositionForCurrentUser($location, $position) as $block)
    @unless(in_array(class_basename($block), $hiddenBlocks, true))
        @include($block->getView($sectionVars), $block->getViewData($sectionVars))
    @endunless
@endforeach
