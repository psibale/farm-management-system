# Use an official Python slim image
FROM python:3.13-slim

# Prevent Python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install wkhtmltopdf and dependencies
RUN apt-get update && \
    apt-get install -y \
        wkhtmltopdf \
        xfonts-75dpi \
        xfonts-base \
        libjpeg62-turbo && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy project files
COPY . /app

# Upgrade pip and install dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Expose the port your Flask app uses
EXPOSE 5000

# Command to run your app
CMD ["python", "app.py"]
