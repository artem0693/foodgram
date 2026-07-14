# build env
FROM node:21.7.1-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . ./
RUN npm run build
FROM nginx:1.25.4-alpine
COPY --from=build /app/build /usr/share/nginx/html