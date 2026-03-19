FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MEDIA_TOOL_STORAGE_ROOT=/app/runtime/storage \
    MEDIA_TOOL_LOG_ROOT=/app/runtime/logs

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg nodejs \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt

RUN python -m pip install --upgrade pip \
    && python -m pip install -r /app/requirements.txt

COPY . /app

RUN mkdir -p /app/runtime/storage /app/runtime/logs

EXPOSE 8051

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8051"]
