# Vocabulary Reels Generator - Dockerfile
# =========================================
# Generates YouTube Shorts-style vocabulary videos
# with AI images (ComfyUI) and AI voice (Local TTS)

FROM python:3.11-slim

# Set labels
LABEL maintainer="VocabReelsGenerator"
LABEL description="YouTube Shorts Vocabulary Video Generator with Web UI and API"
LABEL version="1.0"

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Set working directory
WORKDIR /app

# Install system dependencies including FFmpeg and fonts
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    fonts-dejavu-core \
    fonts-liberation \
    fonts-noto \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy requirements first (for Docker layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories with proper permissions
RUN mkdir -p /app/output /app/temp /app/uploads && \
    chmod -R 777 /app/output /app/temp /app/uploads

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/api/health || exit 1

# Run the application with gunicorn for production
CMD ["python", "app.py"]
