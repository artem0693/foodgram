# build env
FROM node:21.7.1-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . ./
RUN npm run build
FROM alpine:3.19
RUN mkdir /app
COPY --from=build /app/build /app/result/
ENTRYPOINT ["cp", "-r", "/app/result/.", "/var/html/static/"]