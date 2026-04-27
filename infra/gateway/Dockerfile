FROM mcr.microsoft.com/devcontainers/javascript-node:1-22-bookworm

WORKDIR /app

COPY proxy.mjs ./proxy.mjs

EXPOSE 80

CMD ["node", "proxy.mjs"]

