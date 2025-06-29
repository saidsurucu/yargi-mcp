# -------- BASE IMAGE (includes Chromium & deps) ----------------------------
FROM mcr.microsoft.com/playwright/python:v1.52.0-jammy        # Playwright docs

# -------- Runtime setup ----------------------------------------------------
WORKDIR /app

# Copy dependency manifests first for layer-cache
COPY pyproject.toml poetry.lock* requirements*.txt* ./

# Fast, deterministic install with `uv`
RUN pip install --no-cache-dir uv && \
    uv pip install --system --no-cache-dir .[asgi]             # installs FastMCP, FastAPI

# Copy application source
COPY . .

# -------- Environment ------------------------------------------------------
ENV PYTHONUNBUFFERED=1
ENV ENABLE_AUTH=true        # Clerk JWT validation ON by default
ENV PORT=8000

# -------- Health check -----------------------------------------------------
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD python - <<'PY'
import httpx, os, sys; \
r=httpx.get(f"http://localhost:{os.getenv('PORT','8000')}/health"); \
sys.exit(0 if r.status_code==200 else 1)
PY

EXPOSE 8000

# -------- Entrypoint -------------------------------------------------------
CMD ["uvicorn", "asgi_app:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]