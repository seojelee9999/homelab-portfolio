<?php
declare(strict_types=1);

require '/app/www/vendor/autoload.php';
$root = $argv[1] ?? '/checks/theme';
$compiler = new Illuminate\View\Compilers\BladeCompiler(new Illuminate\Filesystem\Filesystem(), '/tmp/portfolio-view-cache');
$files = new RecursiveIteratorIterator(new RecursiveDirectoryIterator($root));
$count = 0;
foreach ($files as $file) {
    if (!$file->isFile() || !str_ends_with($file->getFilename(), '.php')) {
        continue;
    }
    $source = $file->getPathname();
    $temporary = null;
    if (str_ends_with($source, '.blade.php')) {
        $temporary = tempnam('/tmp', 'portfolio-view-');
        file_put_contents($temporary, $compiler->compileString(file_get_contents($source)));
        $source = $temporary;
    }
    passthru(escapeshellarg(PHP_BINARY) . ' -l ' . escapeshellarg($source), $status);
    if ($temporary) {
        unlink($temporary);
    }
    if ($status !== 0) {
        exit($status);
    }
    $count++;
}
echo "PASS: {$count} theme PHP/compiled Blade files.\n";
