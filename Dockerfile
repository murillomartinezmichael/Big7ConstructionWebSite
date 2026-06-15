FROM nginx:alpine

COPY index.html /usr/share/nginx/html/index.html
COPY images/    /usr/share/nginx/html/images/

RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf

CMD ["sh", "-c", "sed -i s/NGINX_PORT/${PORT:-8080}/g /etc/nginx/conf.d/default.conf && exec nginx -g 'daemon off;'"]
