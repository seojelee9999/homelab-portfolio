<?php
declare(strict_types=1);

// Preserve upstream translations and interpolation keys, but use work-note terms.
// This file is mounted at themes/homelab/lang/ko/entities.php.
$translations = require '/app/www/lang/ko/entities.php';
$translate = function (array $values) use (&$translate): array {
    foreach ($values as $key => $value) {
        if (is_array($value)) {
            $values[$key] = $translate($value);
            continue;
        }
        $value = preg_replace_callback('/(?<![가-힣])(책꽂이|책장|서가|책)(으로|을|은|이|과)?/u', function ($match) {
            $particle = $match[2] ?? '';
            if ($match[1] === '책') {
                $particle = ['으로' => '로', '을' => '를', '은' => '는', '이' => '가', '과' => '와'][$particle] ?? $particle;
                return '기술 분류' . $particle;
            }
            return '작업 공간' . $particle;
        }, $value);
        $values[$key] = strtr($value, ['챕터' => '기록 유형', '페이지' => '작업 노트', '문서' => '작업 노트']);
    }
    return $values;
};
return array_replace($translate($translations), [
    'book' => '기술 분류', 'books' => '기술 분류',
    'shelf' => '작업 공간', 'shelves' => '작업 공간',
    'chapter' => '기록 유형', 'chapters' => '기록 유형',
    'page' => '작업 노트', 'pages' => '작업 노트',
    'books_create' => '기술 분류 추가', 'books_new_action' => '새 기술 분류',
    'books_form_book_name' => '기술 이름', 'books_edit' => '기술 분류 편집',
    'books_empty_contents' => '아직 작업 기록이 없습니다. 새 작업 노트를 작성하세요.',
    'books_empty_create_page' => '작업 노트 작성',
    'books_empty_add_chapter' => '기록 유형 추가',
    'pages_create' => '작업 노트 작성', 'pages_new' => '새 작업 노트',
    'pages_new_action' => '새 작업 노트',
    'pages_initial_name' => '새 작업 기록',
    'chapters_create' => '기록 유형 추가',
    'chapters_new' => '새 기록 유형',
    'my_recent_drafts' => '작성 중인 작업 노트',
    'recently_updated_pages' => '최근 수정한 작업 노트',
    'recent_activity' => '작업 기록 변경 이력',
    'page_contents' => '작업 노트 목차',
    'pages_md_insert_drawing' => '구성도 / 그림 그리기',
    'pages_md_insert_image' => '사진 / 스크린샷 업로드',
]);
