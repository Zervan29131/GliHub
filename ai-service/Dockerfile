FROM python:3.11-slim
WORKDIR /app/ai-service

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    fonts-wqy-zenhei \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /app/ai-service/outputs

EXPOSE 8090
CMD ["python", "main.py"]
