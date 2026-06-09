FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    && curl -LO "https://dl.k8s.io/release/v1.32.0/bin/linux/amd64/kubectl" \
    && chmod +x kubectl \
    && mv kubectl /usr/local/bin/ \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY config.py .
COPY core/ ./core/
COPY reports/ ./reports/
COPY utils/ ./utils/
COPY dashboard/ ./dashboard/

RUN mkdir -p models

EXPOSE 5000
EXPOSE 8501

ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]