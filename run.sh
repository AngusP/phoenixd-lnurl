#!/usr/bin/env bash
exec gunicorn app.wsgi:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --forwarded-allow-ips='*' \
    --bind 127.0.0.1:8000;
