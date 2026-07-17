FROM nginx:alpine

COPY index.html         /usr/share/nginx/html/index.html
COPY 404.html           /usr/share/nginx/html/404.html
COPY accessibility.html         /usr/share/nginx/html/accessibility.html
COPY home-repair.html               /usr/share/nginx/html/home-repair.html
COPY commercial-industrial.html     /usr/share/nginx/html/commercial-industrial.html
COPY residential-construction.html  /usr/share/nginx/html/residential-construction.html
COPY big7.js            /usr/share/nginx/html/big7.js
COPY robots.txt         /usr/share/nginx/html/robots.txt
COPY sitemap.xml        /usr/share/nginx/html/sitemap.xml
COPY images/            /usr/share/nginx/html/images/

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
    # sed -i writes a temp file INSIDE conf.d then renames — chowning only
    # default.conf still crashes at boot with "can't create temp file ...
    # Permission denied". The directory itself must belong to nginx.
    && chown -R nginx:nginx /etc/nginx/conf.d

USER nginx

EXPOSE 8080

# Runtime liveness — Railway ignores this, but local `docker run` + orchestrators
# (compose / k8s) use it to know when nginx is actually serving. wget is present
# in the alpine base; the substituted $PORT is what nginx binds.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -q --spider "http://localhost:${PORT:-8080}/" || exit 1

CMD ["sh", "-c", "sed -i s/NGINX_PORT/${PORT:-8080}/g /etc/nginx/conf.d/default.conf && exec nginx -g 'daemon off;'"]
