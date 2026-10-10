#!/bin/bash
set -e

echo "=== Démarrage du Copilote liO Occitanie Backend ==="

# 1. Vérification de la base SQLite et initialisation des données si nécessaire
DB_PATH="/app/data/lio.db"
EXCEL_PATH="/app/data/occitanie-hebergements-scolaires.xlsx"

echo "Vérification de la base de données : ${DATABASE_URL:-$DB_PATH}..."

# Importer les hébergements si la base n'est pas encore initialisée
if [ -f "$EXCEL_PATH" ]; then
    echo "Initialisation et vérification des données d'hébergement..."
    python scripts/import_accommodations.py --file "$EXCEL_PATH" || true
fi

# 2. Vérification et téléchargement de secours du modèle Whisper
MODEL_PATH="${WHISPER_MODEL_PATH:-/app/models/ggml-base-q5_1.bin}"
if [ ! -f "$MODEL_PATH" ]; then
    echo "Modèle Whisper absent à $MODEL_PATH. Téléchargement en cours..."
    mkdir -p "$(dirname "$MODEL_PATH")"
    curl -L -f -o "$MODEL_PATH" "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base-q5_1.bin" || {
        echo "⚠️ Échec du téléchargement automatique du modèle Whisper."
    }
fi

if [ -f "$MODEL_PATH" ]; then
    echo "Modèle WhisperAI prêt : $MODEL_PATH ($(du -h "$MODEL_PATH" | cut -f1))"
else
    echo "⚠️ Avertissement : modèle Whisper introuvable. Les fonctionnalités STT seront en mode dégradé."
fi

# 3. Lancement du serveur uvicorn
echo "Lancement du serveur Uvicorn sur 0.0.0.0:8000..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
