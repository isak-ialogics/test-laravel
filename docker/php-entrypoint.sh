#!/bin/sh
# Run before FPM or any caller-provided command; never rely on a PHP-level
# auto-prepend alone to secure a PHP engine which is already executing.
/usr/local/bin/php -r 'exit(PHP_VERSION_ID >= 80336 && PHP_VERSION_ID < 80400 ? 0 : 78);'
status=$?
if [ "$status" -ne 0 ]; then
    if [ "$status" -eq 78 ]; then
        echo 'Unsupported PHP runtime for this image (requires patched PHP 8.3).' >&2
    else
        echo 'PHP runtime verification failed.' >&2
    fi
    exit "$status"
fi
exec "$@"
