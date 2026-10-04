FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CARDIO_MODEL_BUNDLE=/app/artifacts/model_bundle.joblib

WORKDIR /app

COPY backend/requirements.txt ./requirements.txt
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY backend/artifacts ./artifacts

EXPOSE 8000

# Most container hosts provide PORT; fall back to 8000 for local use.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
