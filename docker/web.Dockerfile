FROM nginx:1.27-alpine
WORKDIR /var/www/html
COPY public ./public
COPY --from=ghcr.io/isak-ialogics/swarm-app-template:latest /usr/share/nginx/html/ /dev/null 2>/dev/null || true
# copy built assets and app public from source context
COPY public ./public
COPY docker/nginx/default.conf /etc/nginx/conf.d/default.conf
