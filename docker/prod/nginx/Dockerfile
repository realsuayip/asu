FROM nginx:1.29.3-alpine3.22@sha256:b3c656d55d7ad751196f21b7fd2e8d4da9cb430e32f646adcf92441b72f82b14

COPY docker/prod/nginx /etc/nginx/

RUN  chown -R nginx:nginx /var/cache/nginx && \
     chown -R nginx:nginx /var/log/nginx && \
     chown -R nginx:nginx /etc/nginx/conf.d && \
     chown -R nginx:nginx /etc/nginx/certs
RUN touch /var/run/nginx.pid && \
        chown -R nginx:nginx /var/run/nginx.pid

USER nginx
