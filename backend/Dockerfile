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

CMD ["uv", "run", "fastapi", "dev", "--host", "0.0.0.0", "--port", "8000"]
