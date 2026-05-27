FROM python:3.13-slim-bullseye

COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
CMD gunicorn main:app \
    --workers 2 \
    --bind 0.0.0.0:8020 \
    --max-requests 1000 \
    --timeout 30 \
    --graceful-timeout 30 \
    --keep-alive 75 \
    --worker-class uvicorn.workers.UvicornWorker
