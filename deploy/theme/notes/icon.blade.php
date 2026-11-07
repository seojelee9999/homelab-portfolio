<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    @switch($name ?? '')
        @case('네트워크')
            <rect x="8" y="2" width="8" height="6" rx="1.5"/><rect x="2" y="16" width="7" height="6" rx="1.5"/><rect x="15" y="16" width="7" height="6" rx="1.5"/><path d="M12 8v4M5.5 16v-4h13v4"/>
            @break
        @case('OpenStack')
            <path d="M6 17a4 4 0 0 1-.8-7.9 7 7 0 0 1 13.5 1.6A3.2 3.2 0 0 1 18 17H6Z"/><path d="M9 21h6M12 17v4"/>
            @break
        @case('Kubernetes')
            <path d="m12 2 9 5v10l-9 5-9-5V7l9-5Zm0 10 9-5M12 12 3 7m9 5v10"/>
            @break
        @case('Linux')
            <rect x="2" y="4" width="20" height="16" rx="3"/><path d="m6 9 3 3-3 3m7 0h5"/>
            @break
        @case('스토리지')
            <ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 4 18 4 18 0V5M3 12c0 4 18 4 18 0"/>
            @break
        @case('자동화 · GitOps')
            <circle cx="6" cy="5" r="3"/><circle cx="6" cy="19" r="3"/><circle cx="18" cy="6" r="3"/><path d="M6 8v8m12-7v1a5 5 0 0 1-5 5H6"/>
            @break
        @default
            <rect x="3" y="3" width="18" height="7" rx="2"/><rect x="3" y="14" width="18" height="7" rx="2"/><path d="M7 6.5h.01M7 17.5h.01M15 6.5h3M15 17.5h3M12 10v4"/>
    @endswitch
</svg>
