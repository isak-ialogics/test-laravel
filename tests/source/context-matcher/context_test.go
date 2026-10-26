package contextmatcher

import (
    "os"
    "path"
    "path/filepath"
    "strings"
    "testing"

    "github.com/moby/patternmatcher"
    "github.com/moby/patternmatcher/ignorefile"
)

// Exercise the upstream Docker ignore parser and matcher, not an approximation.
func TestContextAllowsOnlyRequiredSource(t *testing.T) {
    root, err := filepath.Abs("../../..")
    if err != nil { t.Fatal(err) }
    data, err := os.ReadFile(filepath.Join(root, ".dockerignore"))
    if err != nil { t.Fatal(err) }
    patterns, err := ignorefile.ReadAll(strings.NewReader(string(data)))
    if err != nil { t.Fatal(err) }
    matcher, err := patternmatcher.New(patterns)
    if err != nil { t.Fatal(err) }
    allowed := []string{
        "artisan", "composer.json", "composer.lock", "package.json", "vite.config.js",
        "app/Http/Controllers/Controller.php", "app/Models/User.php", "app/Providers/AppServiceProvider.php",
        "bootstrap/app.php", "bootstrap/providers.php", "bootstrap/php-runtime.php",
        "config/app.php", "config/auth.php", "config/cache.php", "config/database.php",
        "config/filesystems.php", "config/logging.php", "config/mail.php", "config/queue.php",
        "config/services.php", "config/session.php",
        "database/factories/UserFactory.php", "database/migrations/0001_01_01_000000_create_users_table.php",
        "database/migrations/0001_01_01_000001_create_cache_table.php",
        "database/migrations/0001_01_01_000002_create_jobs_table.php", "database/seeders/DatabaseSeeder.php",
        "docker/app.Dockerfile", "docker/web.Dockerfile", "docker/php-entrypoint.sh", "docker/nginx/default.conf",
        "public/.htaccess", "public/favicon.ico", "public/index.php", "public/robots.txt",
        "resources/css/app.css", "resources/js/app.js", "resources/js/bootstrap.js",
        "resources/views/welcome.blade.php", "routes/console.php", "routes/web.php",
    }
    seen := map[string]bool{}
    for _, leaf := range allowed {
        if _, err := os.Stat(filepath.Join(root, filepath.FromSlash(leaf))); err != nil { t.Fatal(err) }
        for name := leaf; name != "."; name = path.Dir(name) {
            if seen[name] { continue }
            seen[name] = true
            ignored, err := matcher.MatchesOrParentMatches(name)
            if err != nil { t.Fatal(err) }
            if ignored { t.Errorf("required context path excluded: %s", name) }
        }
    }
    denied := []string{
        ".env", ".env.example", ".env.production", "auth.json", "credentials.json", ".git/config",
        "composer-auth.json", "vendor/autoload.php", "node_modules/private.js", "tests/source/private.txt",
        "app/private.key", "app/Http/private.key", "app/Http/Controllers/private.key",
        "app/Models/private.php", "app/Providers/private.php", "bootstrap/cache/config.php",
        "bootstrap/secret.key", "config/private.php", "config/cache/credentials.json",
        "database/database.sqlite", "database/factories/private.php", "database/migrations/private.php",
        "database/seeders/private.php", "docker/private.key", "docker/nginx/private.key",
        "public/build/private.js", "public/hot", "public/private.key",
        "resources/private.key", "resources/css/private.css", "resources/js/private.js",
        "resources/views/private.blade.php", "resources/views/nested/private.blade.php",
        "routes/private.php", "storage/logs/private.log", "storage/app/private/credentials.json",
    }
    for _, name := range denied {
        ignored, err := matcher.MatchesOrParentMatches(name)
        if err != nil { t.Fatal(err) }
        if !ignored { t.Errorf("unlisted/private context path admitted: %s", name) }
    }
}
