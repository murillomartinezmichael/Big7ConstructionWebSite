FROM nginx:alpine

COPY index.html /usr/share/nginx/html/index.html
COPY images/    /usr/share/nginx/html/images/

RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Non-root nginx — hardening pattern from templates/dockerfiles/static-nginx.
# nginx writes to /var/cache/nginx, /var/log/nginx, /var/run/nginx.pid at
# runtime; without ownership fixes it fails with "permission denied" and
# the container never starts. The default.conf gets sed-rewritten at
# runtime for dynamic $PORT so it also needs to be writable by nginx.
RUN chown -R nginx:nginx /var/cache/nginx /var/log/nginx /usr/share/nginx/html \
    && touch /var/run/nginx.pid \
    && chown nginx:nginx /var/run/nginx.pid \
    && chown nginx:nginx /etc/nginx/conf.d/default.conf

USER nginx

EXPOSE 8080

CMD ["sh", "-c", "sed -i s/NGINX_PORT/${PORT:-8080}/g /etc/nginx/conf.d/default.conf && exec nginx -g 'daemon off;'"]
