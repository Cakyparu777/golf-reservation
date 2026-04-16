FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    HOST=0.0.0.0 \
    PORT=8000 \
    DATABASE_PATH=/app/data/golf_reservation.db

WORKDIR /app

COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt

COPY backend /app/backend
COPY scripts /app/scripts
COPY .env.example /app/.env.example

RUN mkdir -p /app/data

EXPOSE 8000

CMD ["sh", "-c", "python -m backend.db.seed_data && uvicorn backend.host.app:app --host 0.0.0.0 --port 8000"]
