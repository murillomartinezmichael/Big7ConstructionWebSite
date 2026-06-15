#!/bin/sh
# Railway injects $PORT — substitute it into the nginx config before starting
sed -i "s/\${PORT}/${PORT:-8080}/g" /etc/nginx/conf.d/default.conf
exec nginx -g 'daemon off;'
