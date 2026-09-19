FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    NEBULA_ROOT=/app \
    NEBULA_SOLVER_WORKERS=2 \
    NEBULA_SOLVER_CONCURRENCY=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY current-problem-statement/PS1/01_data ./current-problem-statement/PS1/01_data
COPY deliverables/official-zero ./deliverables/official-zero

RUN pip install --no-cache-dir .

EXPOSE 8080

CMD ["sh", "-c", "uvicorn nebula_ps1.web:app --host 0.0.0.0 --port ${PORT} --workers 1"]
