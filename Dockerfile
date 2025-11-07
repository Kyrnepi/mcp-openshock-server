FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .

# Expose the port
EXPOSE 8000

# Default environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Startup command
CMD ["python", "app.py"]
