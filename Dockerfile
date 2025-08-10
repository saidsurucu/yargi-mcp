FROM mcr.microsoft.com/playwright/python:v1.53.0-noble

WORKDIR /app

COPY pyproject.toml poetry.lock* requirements*.txt* ./

RUN pip install --no-cache-dir uv && \
    uv pip install --system --no-cache-dir .[asgi,saas]

ARG CACHE_BUST=202507221015
RUN echo "Cache bust: $CACHE_BUST"

COPY . .

ENV PYTHONUNBUFFERED=1
ENV ENABLE_AUTH=true
ENV PORT=8765

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD python -c "import httpx, os, sys; r=httpx.get(f'http://localhost:{os.getenv(\"PORT\",\"8765\")}/health'); sys.exit(0 if r.status_code==200 else 1)"

EXPOSE 8765

CMD ["uvicorn", "asgi_app:app", "--host", "0.0.0.0", "--port", "8765", "--proxy-headers"]
