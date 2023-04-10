FROM node:8-alpine
RUN mkdir -p /app/user/
WORKDIR /app/user
COPY package.json yarn.lock ./
RUN yarn
COPY . .
EXPOSE 8082