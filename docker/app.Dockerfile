# Build frontend assets
FROM node:22-alpine AS nodebuild
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY resources ./resources
COPY vite.config.js ./
COPY public ./public
# If you have Tailwind/etc config, copy as needed
RUN npm run build

# Install PHP deps
FROM composer:2 AS vend
WORKDIR /app
COPY composer.json composer.lock ./
RUN composer install --no-dev --prefer-dist --no-interaction --no-progress

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

# Ensure sqlite file exists
RUN mkdir -p database storage bootstrap/cache \
    && touch database/database.sqlite \
    && chown -R www-data:www-data /var/www/html

USER www-data

