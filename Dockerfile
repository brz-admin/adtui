FROM python:3.11-slim

# Metadata
LABEL maintainer="Brz <brz@brznet.fr>"
LABEL description="ADTUI - Active Directory Terminal User Interface"
LABEL version="2.1.0"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Install the package
RUN pip install -e .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash adtui \
    && chown -R adtui:adtui /app
USER adtui
WORKDIR /home/adtui

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV TERM=xterm-256color

# Copy config example to user home
RUN cp /app/config.ini.example /home/adtui/config.ini.example

# Display version and help by default
ENTRYPOINT ["adtui"]
CMD ["--help"]