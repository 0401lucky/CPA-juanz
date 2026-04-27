FROM mcr.microsoft.com/devcontainers/javascript-node:1-22-bookworm AS frontend-builder

WORKDIR /workspace/frontend

COPY apps/frontend/package.json apps/frontend/package-lock.json ./
RUN npm install

COPY apps/frontend/ ./
RUN npm run build

FROM mcr.microsoft.com/devcontainers/python:1-3.13-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FRONTEND_DIST_PATH=/app/frontend-dist

WORKDIR /app

COPY apps/backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY apps/backend/app ./app
COPY --from=frontend-builder /workspace/frontend/dist ./frontend-dist

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:create_dev_app --factory --host 0.0.0.0 --port ${PORT:-8000}"]
