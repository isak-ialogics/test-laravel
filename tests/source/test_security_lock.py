"""Parsed Composer security floors: inherited families and direct runtime policy."""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
# First safe versions for currently affected compatible major/minor families.
MINIMUMS = {
    'guzzlehttp/guzzle': (7, 15, 2),
    # guzzle 7.15.2's tagged manifest requires these newer transitives.
    'guzzlehttp/promises': (2, 5, 1),
    'guzzlehttp/psr7': (2, 13, 0),
    'laravel/framework': (12, 69, 0),
    'league/commonmark': (2, 10, 2),
    'league/flysystem': (3, 35, 3),
    'symfony/http-foundation': (7, 4, 19),
    'symfony/http-kernel': (7, 4, 12),
    'symfony/mailer': (7, 4, 12),
    'symfony/mime': (7, 4, 12),
    'symfony/polyfill-intl-idn': (1, 38, 1),
    'symfony/polyfill-php84': (1, 34, 0),
    'symfony/polyfill-php85': (1, 34, 0),
    'symfony/routing': (7, 4, 13),
    'symfony/yaml': (7, 4, 18),
}


class ComposerSecurityContract(unittest.TestCase):
    def test_direct_php_and_laravel_floors(self):
        manifest = json.loads((ROOT / 'composer.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['require']['php'], '~8.3.36 || ~8.4.27 || ~8.5.12')
        self.assertEqual(manifest['require']['laravel/framework'], '^12.69.0')

    def test_affected_locked_families_are_patched_and_stay_on_compatible_lines(self):
        lock = json.loads((ROOT / 'composer.lock').read_text(encoding='utf-8'))
        versions = {p['name']: p['version'] for family in ('packages', 'packages-dev')
                    for p in lock[family]}
        for package, floor in MINIMUMS.items():
            with self.subTest(package=package):
                self.assertIn(package, versions)
                match = re.fullmatch(r'v?(\d+)\.(\d+)\.(\d+)', versions[package])
                self.assertIsNotNone(match, versions[package])
                version = tuple(map(int, match.groups()))
                self.assertEqual(version[0], floor[0], package)
                if package.startswith('symfony/') and not package.startswith('symfony/polyfill-'):
                    self.assertEqual(version[1], 4, package)
                self.assertGreaterEqual(version, floor, package)
        self.assertEqual(lock['platform']['php'], '~8.3.36 || ~8.4.27 || ~8.5.12')


if __name__ == '__main__':
    unittest.main()
