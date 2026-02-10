# Use official Python image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set workdir
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    autoconf \
    automake \
    libtool \
    ffmpeg \
    wget \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Build RNNoise
WORKDIR /opt
RUN git clone https://github.com/xiph/rnnoise.git
WORKDIR /opt/rnnoise
RUN ./autogen.sh && ./configure && make 

# Manually install the demo binary as it is not installed by make install usually
RUN cp examples/.libs/rnnoise_demo /usr/local/bin/rnnoise_demo
RUN make install && ldconfig

# Install dependencies
WORKDIR /app
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy project
COPY . .

# Create folder for static files
RUN mkdir -p /app/staticfiles

# Collect static files
RUN python manage.py collectstatic --noinput

# Command to run Gunicorn with Uvicorn workers
CMD ["gunicorn", "core.asgi:application", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--workers", "4"]
