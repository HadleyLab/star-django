FROM node:8-alpine
RUN mkdir -p /app/user/
WORKDIR /app
ADD package.json ./package.json
ADD yarn.lock ./yarn.lock
RUN yarn
ADD . /app/user/
WORKDIR /app/user/
