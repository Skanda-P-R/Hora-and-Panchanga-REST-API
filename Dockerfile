FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SWISS_EPHEMERIS_STRICT=true \
    SE_EPHEMERIS_PATH=/app/hora_server/ephe

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py gunicorn.conf.py ./
COPY hora_server ./hora_server
COPY fonts ./fonts

RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
CMD ["gunicorn", "--config", "gunicorn.conf.py", "app:app"]
