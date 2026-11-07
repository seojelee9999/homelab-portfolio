<?php
declare(strict_types=1);

use BookStack\Permissions\Models\RolePermission;
use BookStack\Settings\SettingService;
use BookStack\Users\Models\Role;
use BookStack\Users\Models\User;
use Illuminate\Contracts\Console\Kernel;
use Illuminate\Support\Facades\DB;

try {
    require '/app/www/vendor/autoload.php';
    $app = require '/app/www/bootstrap/app.php';
    $kernel = $app->make(Kernel::class);
    $kernel->bootstrap();
    $settings = $app->make(SettingService::class);
    if (!$settings->get('portfolio-public-configured-v1', false)) {
        DB::transaction(function () use ($settings): void {
            $role = Role::getSystemRole('public');
            if (!$role) {
                throw new RuntimeException('Missing public role');
            }
            // Visitors get only read permissions, no writes, API access, or revision history.
            $permissions = RolePermission::query()->whereIn('name', [
                'bookshelf-view-all', 'book-view-all', 'chapter-view-all', 'page-view-all',
            ])->pluck('id');
            if ($permissions->count() !== 4) {
                throw new RuntimeException('Unexpected permission schema');
            }
            $role->permissions()->sync($permissions->all());
            User::getGuest()->roles()->sync([$role->id]);
            $settings->put('registration-enabled', 'false');
            $settings->put('app-public', 'true');
            $settings->put('app-name', 'Homelab Notes');
            $settings->put('app-editor', 'markdown');
            $settings->put('portfolio-public-configured-v1', 'true');
        });
    }
    if ($kernel->call('bookstack:regenerate-permissions', ['--no-interaction' => true]) !== 0) {
        throw new RuntimeException('Permission index regeneration failed');
    }
    echo "Portfolio public reading and permission index verified.\n";
} catch (Throwable $error) {
    fwrite(STDERR, 'Portfolio access setup failed (' . get_class($error) .
        "); readiness remains disabled. Check migrations and bootstrap compatibility.\n");
    exit(1);
}
