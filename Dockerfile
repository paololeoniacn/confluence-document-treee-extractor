FROM python:3.11-slim

WORKDIR /app

# Installiamo ping e strumenti di rete per il debug
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libc-dev \
    libffi-dev \
    libcairo2-dev \
    pkg-config \
    libpango-1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0 \
    iputils-ping \
    dnsutils \
    && rm -rf /var/lib/apt/lists/*
    
# Copia e installazione dipendenze Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Script
COPY export_confluence.py .

# Variabili d'ambiente attese
ENV CONFLUENCE_URL=""
ENV CONFLUENCE_USER=""
ENV CONFLUENCE_TOKEN=""
ENV PARENT_PAGE_ID=""
ENV SPACE_KEY=""

# Cartella di output
RUN mkdir -p /app/downloaded_pages

CMD ["python", "export_confluence.py"]