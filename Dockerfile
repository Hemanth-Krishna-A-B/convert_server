# Use an official Python image as base
FROM python:3.9

# Install system dependencies for PDF & PPTX conversion
RUN apt-get update && apt-get install -y \
    poppler-utils \
    libreoffice \
    unoconv

# Set working directory
WORKDIR /app

# Copy dependencies
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Expose the port FastAPI runs on
EXPOSE 8000

# Run the FastAPI application
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
