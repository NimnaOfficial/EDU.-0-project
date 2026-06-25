# Use a lightweight, official Python image
FROM python:3.11-slim

# Set environment variables to prevent Python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create a secure, non-root user
RUN adduser --disabled-password --gecos "" eduuser

# Set the working directory
WORKDIR /app

# Install dependencies first (to leverage Docker caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY ./app .

# Switch to the non-root user
USER eduuser

# Command to run the bot
CMD ["python", "main.py"]