FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY backend ./backend

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

RUN addgroup --system app && \
    adduser --system --ingroup app app && \
    mkdir -p /app/data && \
    chown -R app:app /app

USER app

CMD ["python", "-m", "app.bot"]
