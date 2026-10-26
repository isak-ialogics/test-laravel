# Build frontend assets
FROM node:22-alpine AS nodebuild
WORKDIR /app
COPY package*.json ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi
COPY resources ./resources
COPY vite.config.js ./
COPY public ./public
# If you have Tailwind/etc config, copy as needed
RUN npm run build

# The donor provides only the PHAR. Its PHP interpreter is never executed.
FROM composer:2@sha256:b6dcd72ca98fa19d0e5b8476de179859704891fad06dd9e0b96833d4c430a5fc AS composer-phar

# Install PHP deps under the same patched PHP minor as the FPM image.
FROM php:8.3.36-cli-alpine@sha256:86a7a8f46bbf73120a19cf72246f606b6de9aaa84a00971c25d187fbae44c211 AS vend
WORKDIR /app
RUN php -r 'exit(PHP_VERSION_ID === 80336 ? 0 : 78);' \
    && apk add --no-cache icu-dev oniguruma-dev libzip-dev sqlite-dev git unzip \
    && docker-php-ext-install intl pdo pdo_sqlite mbstring zip
COPY --from=composer-phar /usr/bin/composer /usr/local/bin/composer
COPY composer.json composer.lock ./
# Laravel's composer scripts call artisan; we install deps without running scripts in this stage.
RUN composer install --no-dev --prefer-dist --no-interaction --no-progress --no-scripts --no-plugins

# Runtime
FROM php:8.3.36-fpm-alpine@sha256:25e15cf35ed0f5b75d8cf14fc2c4ed7e0e6bee00d359e681b7fa3e91a7bee49f
WORKDIR /var/www/html

# System deps for common Laravel needs
RUN php -r 'exit(PHP_VERSION_ID === 80336 ? 0 : 78);' \
    && apk add --no-cache \
    icu-dev \
    oniguruma-dev \
    libzip-dev \
    sqlite \
    sqlite-dev \
    && docker-php-ext-install intl pdo pdo_sqlite mbstring zip \
    && printf 'session.upload_progress.enabled=0\n' > /usr/local/etc/php/conf.d/99-security.ini

COPY docker/php-entrypoint.sh /usr/local/bin/php-entrypoint
RUN chmod 755 /usr/local/bin/php-entrypoint
COPY --from=vend /app/vendor ./vendor
COPY . .
COPY --from=nodebuild /app/public/build ./public/build

# Ensure sqlite file exists and pre-warm Laravel caches (best-effort)
RUN mkdir -p database storage/app/public storage/app/private \
    storage/framework/cache/data storage/framework/sessions \
    storage/framework/testing storage/framework/views storage/logs bootstrap/cache \
    && touch database/database.sqlite \
    && php artisan package:discover --ansi || true \
    && php artisan config:cache || true \
    && php artisan route:cache || true \
    && php artisan view:cache || true \
    && chown -R www-data:www-data /var/www/html

USER www-data
ENTRYPOINT ["/usr/local/bin/php-entrypoint"]
CMD ["php-fpm"]

