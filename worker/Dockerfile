FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends docker-cli && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock
COPY pyproject.toml ./
COPY backend ./backend
COPY worker ./worker
RUN pip install --no-cache-dir --no-deps . && useradd --uid 10001 --create-home app
USER 10001:10001
CMD ["uvicorn", "worker.main:app", "--host", "0.0.0.0", "--port", "8001"]
