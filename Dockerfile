FROM ghcr.io/astral-sh/uv:0.10.0 AS uv

FROM python:3.14-slim
COPY --from=uv /uv /uvx /usr/local/bin/

ENV UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-dev --no-install-project
COPY godot_rss_tg ./godot_rss_tg

RUN groupadd --gid 10001 bot \
    && useradd --uid 10001 --gid bot --no-create-home bot \
    && mkdir /data \
    && chown bot:bot /data
USER bot
ENV PATH="/app/.venv/bin:${PATH}"
CMD ["python", "-m", "godot_rss_tg"]
