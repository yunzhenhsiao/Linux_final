# skeleton/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (postgresql-client for pg_isready/utilities, curl for checking APIs)
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Gradio UI Port
EXPOSE 7860

# Default command runs the UI
CMD ["python", "skeleton/ui.py"]
