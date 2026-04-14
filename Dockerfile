FROM python:3.11-slim

WORKDIR /app

# Installer kubectl
RUN apt-get update && apt-get install -y \
    curl \
    && curl -LO "https://dl.k8s.io/release/v1.34.1/bin/linux/amd64/kubectl" \
    && chmod +x kubectl \
    && mv kubectl /usr/local/bin/ \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Installer dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code source
COPY main.py .
COPY core/ ./core/
COPY reports/ ./reports/
COPY utils/ ./utils/

# Créer dossier models
RUN mkdir -p models

EXPOSE 5000

CMD ["python", "main.py"]