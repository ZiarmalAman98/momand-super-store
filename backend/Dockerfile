FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev libjpeg62-turbo-dev zlib1g-dev gettext \
    && rm -rf /var/lib/apt/lists/*
COPY . /app
RUN python -m pip install --upgrade pip && python -m pip install -r backend/requirements.txt
EXPOSE 8000
