"""Parsed contracts for pinned image builds and isolated pull-request CI."""
import hashlib
import re
import subprocess
import unittest
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]
CLI = 'sha256:86a7a8f46bbf73120a19cf72246f606b6de9aaa84a00971c25d187fbae44c211'
FPM = 'sha256:25e15cf35ed0f5b75d8cf14fc2c4ed7e0e6bee00d359e681b7fa3e91a7bee49f'
DONOR = 'sha256:b6dcd72ca98fa19d0e5b8476de179859704891fad06dd9e0b96833d4c430a5fc'


def workflow(name):
    return yaml.safe_load((ROOT / '.github/workflows' / name).read_text(encoding='utf-8'))


class PinnedBuildTest(unittest.TestCase):
    def test_every_executing_php_stage_pinned_and_checked_before_use(self):
        docker = (ROOT / 'docker/app.Dockerfile').read_text(encoding='utf-8')
        stages = re.split(r'(?m)^FROM ', docker)[1:]
        vend = next(s for s in stages if ' AS vend\n' in s)
        runtime = stages[-1]
        self.assertIn(f'php:8.3.36-cli-alpine@{CLI} AS vend', vend)
        self.assertIn(f'php:8.3.36-fpm-alpine@{FPM}', runtime)
        self.assertIn(f'composer:2@{DONOR} AS composer-phar', stages[0] + ''.join(stages))
        self.assertRegex(docker, r'COPY --from=composer-phar /usr/bin/composer /usr/local/bin/composer')
        for stage, first_use in [(vend, 'composer install'), (runtime, 'COPY --from=vend')]:
            guard = stage.find('PHP_VERSION_ID')
            self.assertGreaterEqual(guard, 0)
            self.assertLess(guard, stage.index(first_use))
            self.assertIn('80336', stage)
        self.assertIn('ENTRYPOINT ["/usr/local/bin/php-entrypoint"]', docker)
        self.assertIn('session.upload_progress.enabled=0', docker)
        self.assertNotIn('RUN ', next(s for s in stages if ' AS composer-phar\n' in s))

    def test_publisher_bytes_remain_exact_base_blob(self):
        data = (ROOT / '.github/workflows/ci.yml').read_bytes()
        # Git's blob SHA-1 includes the type and byte length.
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        self.assertEqual(blob, 'df9eafc61261464d37cba293721ef19765727af4')

    def test_excluded_runtime_state_is_created_inside_image(self):
        docker = (ROOT / 'docker/app.Dockerfile').read_text(encoding='utf-8')
        for required in ('storage/framework/cache/data', 'storage/framework/views',
                         'storage/framework/sessions', 'storage/logs', 'bootstrap/cache'):
            self.assertIn(required, docker)


class WorkflowTest(unittest.TestCase):
    def test_fpm_probe_fails_even_when_producer_prints_matching_version(self):
        steps = workflow('php-security-pr.yml')['jobs']['verify']['steps']
        script = next(s['run'] for s in steps if s.get('name', '').startswith('Read back actual'))
        stub = ('docker() { if [[ "$*" == *"--entrypoint php-fpm"* ]]; then '
                'printf "PHP 8.3.36\\n"; return 42; fi; return 0; }\n')
        failure = subprocess.run(['bash', '-e', '-c', stub + script + '\necho DOWNSTREAM_MARKER'],
                                 text=True, capture_output=True)
        self.assertEqual(failure.returncode, 42, failure.stderr)
        self.assertNotIn('DOWNSTREAM_MARKER', failure.stdout)
        mutated = script.replace('set -o pipefail', '')
        self.assertNotEqual(mutated, script)
        unprotected = subprocess.run(['bash', '-e', '-c', stub + mutated + '\necho DOWNSTREAM_MARKER'],
                                     text=True, capture_output=True)
        self.assertEqual(unprotected.returncode, 0, unprotected.stderr)
        self.assertIn('DOWNSTREAM_MARKER', unprotected.stdout)

    def test_manual_azure_setup_refreshes_and_checks_actual_patch(self):
        azure = workflow('azure-deploy.yml')
        self.assertEqual(list(azure.get('on', azure.get(True))), ['workflow_dispatch'])
        steps = azure['jobs']['build-and-deploy']['steps']
        index = next(i for i, s in enumerate(steps) if 'shivammathur/setup-php@' in s.get('uses', ''))
        self.assertIs(steps[index].get('env', {}).get('update'), True)
        check = steps[index + 1]
        self.assertIn('PHP_VERSION_ID', check.get('run', ''))
        self.assertIn('80336', check['run'])
        self.assertNotIn('continue-on-error', check)
        self.assertNotIn('if', check)

    def test_pull_request_workflow_is_read_only_and_fails_closed(self):
        ci = workflow('php-security-pr.yml')
        self.assertEqual(list(ci.get('on', ci.get(True))), ['pull_request'])
        self.assertEqual(ci['permissions'], {'contents': 'read'})
        self.assertIn('concurrency', ci)
        raw = (ROOT / '.github/workflows/php-security-pr.yml').read_text(encoding='utf-8')
        for forbidden in ('secrets.', 'docker/login-action', 'azure/', 'push: true', 'workflow_dispatch', 'pull_request_target'):
            self.assertNotIn(forbidden, raw)
        steps = ci['jobs']['verify']['steps']
        for step in steps:
            if 'uses' in step:
                self.assertRegex(step['uses'], r'^[^@]+@[0-9a-f]{40}$')
            if '|' in step.get('run', ''):
                self.assertIn('set -o pipefail', step['run'])
        index = next(i for i, s in enumerate(steps) if 'shivammathur/setup-php@' in s.get('uses', ''))
        self.assertIs(steps[index].get('env', {}).get('update'), True)
        guard = steps[index + 1]
        self.assertIn('PHP_VERSION_ID', guard['run'])
        self.assertIn('80336', guard['run'])
        self.assertNotIn('if', guard)
        commands = '\n'.join(s.get('run', '') for s in steps)
        for required in ('unittest discover', 'composer audit --locked', 'composer install',
                         'docker build', 'docker run', '--target vend', '--entrypoint php-fpm',
                         'session.upload_progress.enabled', 'extension_loaded', 'docker/web.Dockerfile',
                         'go test -mod=readonly'):
            self.assertIn(required, commands)


if __name__ == '__main__':
    unittest.main()
