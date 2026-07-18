# build env
FROM node:21.7.1-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . ./
RUN npm run build
FROM alpine:3.19
COPY --from=build /app/build /app/result/