FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# Set INSTALL_ML=1 to include sentence-transformers (larger image, better semantic matching).
ARG INSTALL_ML=0
COPY requirements.txt requirements-ml.txt ./
RUN if [ "$INSTALL_ML" = "1" ]; then pip install --no-cache-dir -r requirements-ml.txt; \
    else pip install --no-cache-dir -r requirements.txt; fi

COPY alembic.ini ./
COPY migrations ./migrations
COPY app ./app
RUN useradd --create-home appuser && mkdir -p /data/storage && chown appuser /data/storage
USER appuser

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
