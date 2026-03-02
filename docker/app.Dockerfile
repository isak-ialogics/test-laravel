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

# Install PHP deps
FROM composer:2 AS vend
WORKDIR /app
COPY composer.json composer.lock ./
# Laravel's composer scripts call artisan; we install deps without running scripts in this stage.
RUN composer install --no-dev --prefer-dist --no-interaction --no-progress --no-scripts

# Runtime
FROM php:8.3-fpm-alpine
WORKDIR /var/www/html

# System deps for common Laravel needs
RUN apk add --no-cache \
    icu-dev \
    oniguruma-dev \
    libzip-dev \
    sqlite \
    sqlite-dev \
    && docker-php-ext-install intl pdo pdo_sqlite mbstring zip

COPY --from=vend /app/vendor ./vendor
COPY . .
COPY --from=nodebuild /app/public/build ./public/build

# Ensure sqlite file exists and pre-warm Laravel caches (best-effort)
RUN mkdir -p database storage bootstrap/cache \
    && touch database/database.sqlite \
    && php artisan package:discover --ansi || true \
    && php artisan config:cache || true \
    && php artisan route:cache || true \
    && php artisan view:cache || true \
    && chown -R www-data:www-data /var/www/html

USER www-data

