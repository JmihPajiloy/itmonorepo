FROM python:3.12.12-slim-bookworm AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt constraints.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY alembic.ini .
COPY migrations ./migrations
RUN useradd --create-home lab4
USER lab4
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --no-access-log"]

FROM base AS test
USER root
COPY requirements-test.txt .
RUN pip install --no-cache-dir -r requirements-test.txt
COPY tests ./tests
USER lab4
CMD ["pytest", "-q", "-p", "no:cacheprovider", "--junitxml=/results/pytest.xml"]

FROM base AS runtime
