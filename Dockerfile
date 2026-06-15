FROM nginx:alpine

# Copy site content
COPY index.html /usr/share/nginx/html/index.html
COPY images/    /usr/share/nginx/html/images/

# Drop default config, inject ours (PORT is substituted at startup)
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Startup script that swaps ${PORT} for Railway's injected value
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]
