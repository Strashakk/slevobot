FROM python:3.12.3-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.15 /uv /uvx /bin/

COPY . /app

ENV UV_NO_DEV=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app
RUN uv sync --locked --no-dev

CMD ["uv", "run", "python", "bot.py"]
