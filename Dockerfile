# Stage 1: Build React Frontend
FROM node:18-alpine AS frontend-builder
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Final Python/Uvicorn Backend
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy all files (including app, evaluations, configurations)
COPY . .

# Copy compiled React HTML and asset builds from the builder stage
COPY --from=frontend-builder /static /app/static

EXPOSE 8000

CMD ["uvicorn", "app.api.server:app", "--host", "0.0.0.0", "--port", "8000"]