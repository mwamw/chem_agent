FROM python:3.11-slim

WORKDIR /workspace
COPY pyproject.toml README.md ./
COPY app ./app
COPY scripts ./scripts
COPY data ./data
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini

RUN pip install --no-cache-dir .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
