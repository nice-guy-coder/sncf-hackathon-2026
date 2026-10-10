#!/bin/sh
# Télécharge le modèle GGUF Qwen2.5 dans le volume partagé s'il n'est pas déjà présent.
set -eu

MODEL_URL="${MODEL_URL:-https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf}"
MODEL_FILE="${MODEL_FILE:-qwen2.5-1.5b-instruct-q4_k_m.gguf}"
TARGET="/models/${MODEL_FILE}"

if [ -s "$TARGET" ]; then
  echo "[model-downloader] Modèle LLM déjà présent : $TARGET ($(du -h "$TARGET" | cut -f1)) - rien à faire."
  exit 0
fi

echo "[model-downloader] Téléchargement du modèle LLM depuis $MODEL_URL"
echo "[model-downloader] -> $TARGET"
curl -fL --retry 5 --retry-delay 5 -C - --progress-bar -o "${TARGET}.part" "$MODEL_URL"

if [ -n "${MODEL_SHA256:-}" ]; then
  echo "[model-downloader] Vérification SHA256..."
  echo "${MODEL_SHA256}  ${TARGET}.part" | sha256sum -c -
fi

mv "${TARGET}.part" "$TARGET"
echo "[model-downloader] Terminé : $(du -h "$TARGET" | cut -f1)"
