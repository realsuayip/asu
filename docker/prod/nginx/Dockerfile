FROM nginx:1.25-alpine

COPY docker/prod/nginx /etc/nginx/

RUN  chown -R nginx:nginx /var/cache/nginx && \
     chown -R nginx:nginx /var/log/nginx && \
     chown -R nginx:nginx /etc/nginx/conf.d && \
     chown -R nginx:nginx /etc/nginx/certs
RUN touch /var/run/nginx.pid && \
        chown -R nginx:nginx /var/run/nginx.pid

USER nginx
