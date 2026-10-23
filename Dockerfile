FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for PyMuPDF, FAISS, and OCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Expose API port
EXPOSE 8000

# Run Uvicorn server
CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000"]
