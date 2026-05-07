# Use Python 3.12 slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies (gcc/g++ kept in case any wheel falls back to source build)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy project metadata first for better Docker layer caching
COPY pyproject.toml ./
COPY README.md ./

# Copy entry points
COPY app.py ./
COPY asgi_app.py ./
COPY mcp_server_main.py ./

# Copy MCP modules and shared packages
COPY anayasa_mcp_module ./anayasa_mcp_module
COPY bddk_mcp_module ./bddk_mcp_module
COPY bedesten_mcp_module ./bedesten_mcp_module
COPY danistay_mcp_module ./danistay_mcp_module
COPY emsal_mcp_module ./emsal_mcp_module
COPY gib_mcp_module ./gib_mcp_module
COPY kik_mcp_module ./kik_mcp_module
COPY kvkk_mcp_module ./kvkk_mcp_module
COPY rekabet_mcp_module ./rekabet_mcp_module
COPY sayistay_mcp_module ./sayistay_mcp_module
COPY sigorta_tahkim_mcp_module ./sigorta_tahkim_mcp_module
COPY uyusmazlik_mcp_module ./uyusmazlik_mcp_module
COPY yargitay_mcp_module ./yargitay_mcp_module
COPY semantic_search ./semantic_search

# Install the package with ASGI extras (uvicorn + starlette)
RUN pip install --no-cache-dir -e ".[asgi]"

# Expose port
EXPOSE 8000

# Set environment variables
ENV PORT=8000
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health', timeout=5)" || exit 1

# Run the ASGI application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
