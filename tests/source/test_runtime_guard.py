"""Executable and parsed contracts for the PHP entry boundary."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
PHP = os.environ.get('PHP_BIN', 'php')
INI = os.environ.get('PHP_INI')


def run_php(*args, cwd=None):
    command = [PHP] + (['-c', INI] if INI else []) + list(args)
    return subprocess.run(command, cwd=cwd, text=True, capture_output=True)


class RuntimePolicyTest(unittest.TestCase):
    def test_explicit_patched_branches_and_unsupported_versions(self):
        guard = ROOT / 'bootstrap/php-runtime.php'
        self.assertTrue(guard.is_file(), 'shared runtime policy missing')
        for version, supported in [(80336, True), (80399, True), (80427, True),
                                   (80512, True), (80335, False), (80426, False),
                                   (80511, False), (80235, False), (80600, False)]:
            code = f'require {str(guard)!r}; exit(php_runtime_supported({version}) ? 0 : 78);'
            result = run_php('-r', code)
            self.assertEqual(result.returncode, 0 if supported else 78,
                             f'PHP {version}: {result.stderr}')

    def test_actual_artisan_and_web_callers_reject_before_autoload(self):
        with tempfile.TemporaryDirectory() as temp:
            sandbox = Path(temp)
            (sandbox / 'bootstrap').mkdir()
            (sandbox / 'public').mkdir()
            (sandbox / 'vendor').mkdir()
            (sandbox / 'bootstrap/php-runtime.php').write_text(
                (ROOT / 'bootstrap/php-runtime.php').read_text(encoding='utf-8').replace(
                    'PHP_VERSION_ID', '80335'), encoding='utf-8')
            (sandbox / 'vendor/autoload.php').write_text(
                "<?php file_put_contents(__DIR__.'/../autoload-executed', 'yes');", encoding='utf-8')
            for caller, destination in [('artisan', 'artisan'), ('public/index.php', 'public/index.php')]:
                (sandbox / destination).write_bytes((ROOT / caller).read_bytes())
                result = run_php(str(sandbox / destination), cwd=sandbox)
                self.assertEqual(result.returncode, 78, f'{caller}: {result.stderr}')
                self.assertIn('Unsupported PHP runtime', result.stderr)
                self.assertFalse((sandbox / 'autoload-executed').exists(), caller)

    def test_entrypoint_fails_before_arbitrary_command_and_accepts_fixed_runtime(self):
        entry = ROOT / 'docker/php-entrypoint.sh'
        self.assertTrue(entry.is_file(), 'container entrypoint missing')
        self.assertIn('/usr/local/bin/php -r', entry.read_text(encoding='utf-8'))
        with tempfile.TemporaryDirectory() as temp:
            sandbox = Path(temp)
            marker = sandbox / 'ran'
            marker_shell = marker.as_posix().replace('C:/', '/c/')
            # Source the real POSIX script in an isolated bash child with a scoped
            # command function. This works even when the test host is Windows.
            launcher = '/usr/local/bin/php() { return "$FAKE_PHP_STATUS"; }; . "$1" sh -c "$2"'
            for status in (78, 42):
                result = subprocess.run(['bash', '-c', launcher, '_', str(entry), f'touch {marker_shell}'],
                                        env={**os.environ, 'FAKE_PHP_STATUS': str(status)},
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, status)
                self.assertFalse(marker.exists())
            result = subprocess.run(['bash', '-c', launcher, '_', str(entry), f'touch {marker_shell}'],
                                    env={**os.environ, 'FAKE_PHP_STATUS': '0'},
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(marker.exists())

    def test_entrypoint_preserves_flags_only_fpm_command_after_guard(self):
        entry = ROOT / 'docker/php-entrypoint.sh'
        with tempfile.TemporaryDirectory() as temp:
            sandbox = Path(temp)
            fpm = sandbox / 'php-fpm'
            fpm.write_text('#!/bin/sh\nprintf "FPM_ARG=%s\\n" "$@"\n', encoding='utf-8')
            fpm.chmod(0o755)
            launcher = ('PATH="$(cd "$2" && pwd):$PATH"; export PATH; '
                        '/usr/local/bin/php() { return "$FAKE_PHP_STATUS"; }; '
                        '. "$1" -v')
            for status in (0, 78, 42):
                with self.subTest(status=status):
                    result = subprocess.run(['bash', '-c', launcher, '_', str(entry), str(sandbox)],
                                            env={**os.environ, 'FAKE_PHP_STATUS': str(status)},
                                            capture_output=True, text=True)
                    self.assertEqual(result.returncode, status, result.stderr)
                    self.assertEqual(result.stdout, 'FPM_ARG=-v\n' if status == 0 else '')


if __name__ == '__main__':
    unittest.main()
