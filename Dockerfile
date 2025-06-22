# Use Python 3.11 slim image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    DEBIAN_FRONTEND=noninteractive

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    wget \
    curl \
    git \
    build-essential \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Create necessary directories
RUN mkdir -p /tmp/videos /tmp/processed && \
    chmod 755 /tmp/videos /tmp/processed

# Copy application code
COPY app/ ./app/

# Copy fonts directory
COPY fonts/ ./fonts/

# Create non-root user for security
RUN groupadd -r videobot && useradd -r -g videobot videobot && \
    chown -R videobot:videobot /app /tmp/videos /tmp/processed

# Switch to non-root user
USER videobot

# Expose port for webhook mode
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)" || exit 1

# Default command
CMD ["python", "app/main.py"]