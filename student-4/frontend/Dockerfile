FROM nginx:alpine

COPY student-4/frontend/ /usr/share/nginx/html/
COPY shared/frontend/css/ /usr/share/nginx/html/shared/css/

COPY student-4/frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80