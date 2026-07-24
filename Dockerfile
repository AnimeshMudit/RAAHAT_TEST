# ===========================
# Stage 1: Build React
# ===========================
FROM node:20-alpine AS frontend-builder

WORKDIR /frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./

RUN npm run build


# ===========================
# Stage 2: Backend
# ===========================
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libgomp1 && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
COPY constraints.txt ./

# Install production dependencies with CPU-only torch pinned by constraints
RUN pip install --no-cache-dir -r requirements.txt -c constraints.txt

COPY . .

# Copy compiled frontend
COPY --from=frontend-builder /static /app/static

EXPOSE 8000

CMD ["uvicorn", "app.api.server:app", "--host", "0.0.0.0", "--port", "8000"]