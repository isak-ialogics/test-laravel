# Build frontend assets
FROM node:22-alpine AS nodebuild
WORKDIR /app
COPY package*.json ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi
COPY resources ./resources
COPY vite.config.js ./
COPY public ./public
RUN npm run build

FROM nginx:1.27-alpine
WORKDIR /var/www/html
COPY public ./public
COPY --from=nodebuild /app/public/build ./public/build
COPY docker/nginx/default.conf /etc/nginx/conf.d/default.conf
