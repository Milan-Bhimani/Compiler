FROM python:3.9-slim

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD service docker start && python app.py