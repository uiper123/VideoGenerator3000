# Use Python 3.11 slim image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    DEBIAN_FRONTEND=noninteractive \
    HOME=/tmp \
    HF_HOME=/tmp/.cache/huggingface \
    TRANSFORMERS_CACHE=/tmp/.cache/transformers \
    NUMBA_CACHE_DIR=/tmp/.cache/numba \
    OMP_NUM_THREADS=4 \
    OPENBLAS_NUM_THREADS=4 \
    MKL_NUM_THREADS=4 \
    VECLIB_MAXIMUM_THREADS=4 \
    NUMEXPR_NUM_THREADS=4 \
    WHISPER_CPU_THREADS=4 \
    WHISPER_NUM_WORKERS=2

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    build-essential \
    wget \
    curl \
    pkg-config \
    imagemagick \
    python3-dev \
    libmagic1 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy the custom ImageMagick policy to fix MoviePy text rendering issues.
COPY policy.xml /etc/ImageMagick-6/policy.xml

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir --upgrade yt-dlp

# Create necessary directories
RUN mkdir -p /tmp/videos /tmp/processed /tmp/.cache/huggingface /tmp/.cache/transformers /tmp/.cache/numba && \
    chmod -R 777 /tmp/.cache

# Copy application code
COPY app/ ./app/

# Copy fonts directory
COPY fonts/ ./fonts/

COPY run_bot.py .
COPY entrypoint.sh .

# Create non-root user for security
RUN chmod +x /app/entrypoint.sh && \
    groupadd -r videobot && useradd -r -g videobot videobot && \
    chown -R videobot:videobot /app /tmp/videos /tmp/processed

# Switch to non-root user
USER videobot

# Expose port for webhook mode
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)" || exit 1

# Set the entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

# The default command will be overridden by Railway's start command
CMD ["bot"]