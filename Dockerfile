# -------- BASE IMAGE ---------------------------------------------------------
FROM python:3.12-slim

# -------- Runtime setup ----------------------------------------------------
WORKDIR /app

# Copy dependency manifests first for layer-cache
COPY pyproject.toml poetry.lock* requirements*.txt* ./

# Fast, deterministic install with `uv`
RUN pip install --no-cache-dir uv && \
    uv pip install --system --no-cache-dir . && \
    uv pip install --system --no-cache-dir .[asgi,saas]

# Cache buster - force rebuild
ARG CACHE_BUST=202510061202
RUN echo "Cache bust: $CACHE_BUST"

# Copy application source
COPY . .

# -------- Environment ------------------------------------------------------
ENV PYTHONUNBUFFERED=1
ENV ENABLE_AUTH=true
ENV PORT=8000

# -------- Health check -----------------------------------------------------
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD python -c "import httpx, os, sys; r=httpx.get(f'http://localhost:{os.getenv(\"PORT\",\"8000\")}/health'); sys.exit(0 if r.status_code==200 else 1)"

EXPOSE 8000

# -------- Entrypoint -------------------------------------------------------
CMD ["uvicorn", "asgi_app:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]