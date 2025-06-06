# Multi-stage build for Frame.io to Google Drive Automation

# Stage 1: Builder - install dependencies and prepare the app
FROM python:3.12-slim AS builder

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime - create clean image with only necessary components
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies for Playwright and basic utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    ca-certificates \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libatspi2.0-0 \
    fonts-liberation \
    fonts-noto-color-emoji \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder stage
COPY --from=builder /root/.local /root/.local

# Make sure scripts in .local are usable:
ENV PATH=/root/.local/bin:$PATH

# Create necessary directories
RUN mkdir -p /app/tmp/downloads /app/tmp/processing /app/logs

# Set proper permissions
RUN chmod -R 755 /app/tmp /app/logs

# Copy application code
COPY . /app/

# Install Playwright browsers
RUN playwright install chromium --with-deps

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8000/health || exit 1

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "${API_HOST:-0.0.0.0}", "--port", "${API_PORT:-8000}", "--workers", "${WORKERS:-1}"]
