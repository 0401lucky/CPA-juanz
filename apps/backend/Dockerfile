FROM mcr.microsoft.com/devcontainers/python:1-3.13-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:create_dev_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
