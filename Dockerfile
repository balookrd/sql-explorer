# ==========================================
# Этап 1: Сборка Frontend (Svelte 5 + Vite)
# ==========================================
FROM node:22-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ==========================================
# Этап 2: Финальный образ Backend + Static
# ==========================================
FROM python:3.12-slim

# Установка системных зависимостей для Kerberos GSSAPI и SASL
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libkrb5-dev \
    libsasl2-dev \
    libsasl2-modules-gssapi-mit \
    krb5-user \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Установка Python зависимостей
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r backend/requirements.txt

# Копирование исходного кода backend и конфигурации
COPY backend/ ./backend/
COPY config/ ./config/
COPY pytest.ini ./

# Копирование собранного Frontend из этапа 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Делаем скрипт запуска исполняемым
RUN chmod +x /app/backend/docker-entrypoint.sh

ENV CONFIG_PATH=/app/config/config.yaml \
    PYTHONUNBUFFERED=1

EXPOSE 8000

ENTRYPOINT ["/app/backend/docker-entrypoint.sh"]
