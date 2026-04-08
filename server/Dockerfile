FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir "openenv-core>=0.2.0" "fastapi>=0.115.0" "uvicorn>=0.24.0" "openai>=1.0.0"

RUN pip install -e .

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"]