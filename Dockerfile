# Use an official Python image as base
FROM python:3.9

# Set working directory
WORKDIR /app

# Copy dependencies first (for better Docker caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Set environment variables from .env file
ENV PYTHONUNBUFFERED=1

# Run the FastAPI server
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]

