FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
COPY requirements.txt ./
RUN apt-get update && apt-get install -y --no-install-recommends tzdata && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.txt && useradd --create-home garage
COPY --chown=garage:garage . .
USER garage
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn backend.main:app --host 0.0.0.0 --port 8000"]
