import multiprocessing
import os

# Gunicorn configuration for Render
bind = "0.0.0.0:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
keepalive = 5
timeout = 120
graceful_timeout = 30
max_requests = 1000
max_requests_jitter = 50
preload_app = True

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Environment
env = {
    "SECRET_KEY": os.getenv("SECRET_KEY", "your-secret-key-change-this"),
}
