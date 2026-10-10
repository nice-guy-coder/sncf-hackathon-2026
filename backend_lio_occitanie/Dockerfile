# Image de base Python 3.11 Debian Slim (optimisée pour la compilation C++ de whisper.cpp)
FROM python:3.11-slim

# Variables d'environnement pour l'exécution Python et l'application
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DATABASE_URL=sqlite:////app/data/lio.db \
    WHISPER_MODEL_PATH=/app/models/ggml-base-q5_1.bin \
    WHISPER_THREADS=4 \
    PORT=8000

# Installation des dépendances système nécessaires :
# - build-essential & cmake : compilation C++ de pywhispercpp / whisper.cpp
# - ffmpeg : conversion universelle des flux audio (WebM, OGG, MP3 vers WAV 16kHz)
# - libsndfile1 : décodage audio
# - curl : pour le téléchargement du modèle et le healthcheck Docker
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    ffmpeg \
    libsndfile1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Répertoire de travail de l'application
WORKDIR /app

# Installation des dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Téléchargement automatique du modèle Whisper quantifié (ggml-base-q5_1.bin)
# Permet une initialisation 100% autonome du conteneur sans fichiers binaires locaux
RUN mkdir -p /app/models && \
    echo "Téléchargement du modèle Whisper Base (GGML Q5_1)..." && \
    curl -L -f -o /app/models/ggml-base-q5_1.bin \
    "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base-q5_1.bin"

# Copie du code applicatif, des données et des scripts
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY data/ ./data/
COPY models/ ./models/
COPY test_frontend/ ./test_frontend/
COPY entrypoint.sh ./entrypoint.sh

# Rendre l'entrypoint exécutable
RUN chmod +x /app/entrypoint.sh

# Volume pour persister la base de données SQLite et les données
VOLUME ["/app/data"]

# Port exposé
EXPOSE 8000

# Vérification d'état (Healthcheck)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Point d'entrée
ENTRYPOINT ["/app/entrypoint.sh"]
