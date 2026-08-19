FROM python:3.13-slim

WORKDIR /app

# DejaVu ships full Latin coverage (accents: ñ, á, ¡) for the QR-bundle label
# and message text; the default Pillow font renders those as tofu boxes.
RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv==0.5.21

# Copy dependency files first for layer caching
COPY pyproject.toml ./
COPY uv.loc[k] ./

# Install dependencies. Once uv.lock is committed, change to:
#   RUN uv sync --no-dev --frozen
RUN uv sync --no-dev

# Copy application code
COPY . .

EXPOSE 8000

# Production entrypoint. `fastapi dev` (the previous CMD) is uvicorn with
# --reload: a single unsupervised worker plus a WatchFiles observer over
# /app, so any file touch restarts the serving process and one stalled
# request wedges the whole API. `fastapi run` disables reload and takes
# --workers, so a wedged worker no longer takes the site down with it.
#
# WEB_CONCURRENCY is honoured (the conventional name) so the worker count is
# tunable per environment without rebuilding. --proxy-headers is required for
# the rate limiter: it keys on `request.client.host`, which is the proxy's IP
# unless X-Forwarded-For is trusted.
#
# Migrations are deliberately NOT run here. Chaining them onto the server
# start (`alembic upgrade head && ...`, as docker-compose does for local dev)
# means a transient DB blip exits the container and restart policy turns it
# into a crash loop. Run `alembic upgrade head` as a separate deploy step.
CMD ["sh", "-c", "uv run fastapi run app/main.py --host 0.0.0.0 --port 8000 --workers ${WEB_CONCURRENCY:-2} --proxy-headers"]
