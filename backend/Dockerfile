FROM python:3.13-slim

WORKDIR /app

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
