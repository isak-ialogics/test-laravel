<?php

/** Reject unsupported/unpatched PHP branches before Laravel or environment bootstrapping. */
function php_runtime_supported(int $versionId): bool
{
    $minor = intdiv($versionId, 100);

    return match ($minor) {
        803 => $versionId >= 80336 && $versionId < 80400,
        804 => $versionId >= 80427 && $versionId < 80500,
        805 => $versionId >= 80512 && $versionId < 80600,
        default => false,
    };
}

if (! php_runtime_supported(PHP_VERSION_ID)) {
    $message = 'Unsupported PHP runtime: a patched PHP 8.3.36+, 8.4.27+, or 8.5.12+ branch is required.';
    if (PHP_SAPI === 'cli') {
        fwrite(STDERR, $message.PHP_EOL);
    } else {
        http_response_code(503);
        error_log($message);
    }
    exit(78);
}
