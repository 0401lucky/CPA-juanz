FROM mcr.microsoft.com/devcontainers/javascript-node:1-22-bookworm AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm install

COPY . .
RUN npm run build

FROM mcr.microsoft.com/devcontainers/javascript-node:1-22-bookworm

WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY server.mjs ./server.mjs

EXPOSE 80

CMD ["node", "server.mjs"]
