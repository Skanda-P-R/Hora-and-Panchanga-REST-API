"""Production-safe Gunicorn defaults for Swiss Ephemeris global state."""

import os


bind = os.getenv("BIND", "0.0.0.0:8000")
workers = int(os.getenv("WEB_CONCURRENCY", "2"))
worker_class = "sync"
threads = 1
timeout = int(os.getenv("GUNICORN_TIMEOUT", "30"))
accesslog = "-"
errorlog = "-"
