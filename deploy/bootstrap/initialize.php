<?php
declare(strict_types=1);

// No credentials in arguments, files, or logs. Only the factory account is changed.
try {
    $email = getenv('INITIAL_ADMIN_EMAIL');
    $password = getenv('INITIAL_ADMIN_PASSWORD');
    if (!filter_var($email, FILTER_VALIDATE_EMAIL) || strlen($password ?: '') < 24) {
        throw new RuntimeException('Invalid initial administrator secret');
    }
    $db = new PDO(
        'mysql:host=' . getenv('DB_HOST') . ';port=' . getenv('DB_PORT') .
        ';dbname=' . getenv('DB_DATABASE') . ';charset=utf8mb4',
        getenv('DB_USERNAME'), getenv('DB_PASSWORD'),
        [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]
    );
    $marker = '/config/.portfolio-initialized-v1';
    $db->beginTransaction();
    $query = $db->prepare('SELECT id, password FROM users WHERE email = ? FOR UPDATE');
    $query->execute(['admin@admin.com']);
    $factory = $query->fetch(PDO::FETCH_ASSOC);

    if (!file_exists($marker)) {
        if (!$factory || !password_verify('password', $factory['password'])) {
            // Allow recovery from a crash after DB commit but before marker write.
            $query->execute([$email]);
            $existing = $query->fetch(PDO::FETCH_ASSOC);
            if ($factory || !$existing || !password_verify($password, $existing['password'])) {
                throw new RuntimeException('Database is not a fresh or partially initialized installation');
            }
        } else {
            $update = $db->prepare(
                'UPDATE users SET name = ?, email = ?, password = ?, remember_token = NULL WHERE id = ?'
            );
            $update->execute(['Homelab Admin', $email, password_hash($password, PASSWORD_BCRYPT), $factory['id']]);
        }
    } elseif ($factory && password_verify('password', $factory['password'])) {
        throw new RuntimeException('Factory credentials unexpectedly present after initialization');
    }
    $db->commit();
    if (!file_exists($marker) && file_put_contents($marker, "initialized\n", LOCK_EX) === false) {
        throw new RuntimeException('Could not persist initialization marker');
    }
    echo "Portfolio administrator initialization verified.\n";
} catch (Throwable $error) {
    // Exception text from database drivers may contain sensitive connection data.
    fwrite(STDERR, "Portfolio initialization failed; readiness remains disabled. Check DB migrations and initial administrator secrets.\n");
    exit(1);
}
