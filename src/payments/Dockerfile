FROM python:3.13-slim AS base

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_NO_DEV=1 \
    UV_PROJECT_ENVIRONMENT=/usr/local

RUN useradd -m payments_user

WORKDIR /payment_service

# Copy dependency files and source code
COPY pyproject.toml uv.lock README.md .
COPY src src/

# Single sync installs everything including local package
RUN uv sync --frozen --no-dev

# Copy remaining files with correct ownership
COPY --chown=payments_user:payments_user . .

# Set permissions on site-packages
RUN chmod -R 755 /usr/local/lib/python3.13/site-packages && \
    chown -R payments_user:payments_user /usr/local/lib/python3.13/site-packages

USER payments_user

CMD ["/bin/sh", "-c", "alembic upgrade head && uv run src/payments/main.py"]
EXPOSE 8000
