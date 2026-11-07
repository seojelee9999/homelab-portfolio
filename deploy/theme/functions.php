<?php
use BookStack\Facades\Theme;
use BookStack\Theming\ThemeEvents;
use BookStack\Theming\ThemeViews;

Theme::listen(ThemeEvents::THEME_REGISTER_VIEWS, function (ThemeViews $views): void {
    $views->renderAfter('layouts.parts.custom-head', 'notes.head');
});
