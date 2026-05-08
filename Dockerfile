FROM python:3.12-slim

WORKDIR /app

# Install system dependencies needed by tree-sitter, chromadb, etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install all Python dependencies (includes pathspec, tree-sitter, chromadb, etc.)
RUN pip install --no-cache-dir -r requirements.txt

# Also install lokr_core's own requirements if it has them
COPY lokr_core/requirements.txt ./lokr_core_requirements.txt
RUN pip install --no-cache-dir -r lokr_core_requirements.txt || true

# Copy the full application
COPY . .

# Expose Streamlit port
EXPOSE 8501

# Streamlit config: disable telemetry, enable headless mode
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_PORT=8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8501/_stcore/health')" || exit 1

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
