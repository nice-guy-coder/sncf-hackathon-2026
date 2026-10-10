import os
import math
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
DEFAULT_MODEL_PATH = MODELS_DIR / "ggml-base-q5_1.bin"

_MODEL_INSTANCE = None

def get_model_path() -> Path:
    env_path = os.getenv("WHISPER_MODEL_PATH")
    if env_path:
        p = Path(env_path)
        if p.is_file():
            return p
    if DEFAULT_MODEL_PATH.is_file():
        return DEFAULT_MODEL_PATH
    # Fallback tiny si base n'est pas disponible
    tiny_path = MODELS_DIR / "ggml-tiny-q5_1.bin"
    if tiny_path.is_file():
        return tiny_path
    return DEFAULT_MODEL_PATH

def get_whisper_model():
    """Charge le modèle Whisper en mémoire (singleton) pour des performances optimales."""
    global _MODEL_INSTANCE
    if _MODEL_INSTANCE is None:
        model_path = get_model_path()
        if not model_path.is_file():
            raise FileNotFoundError(
                f"Modèle Whisper introuvable à l'emplacement : {model_path}. "
                "Assurez-vous que le modèle GGML est bien présent dans le dossier models/."
            )
        try:
            from pywhispercpp.model import Model
            threads = int(os.getenv("WHISPER_THREADS", min(4, os.cpu_count() or 1)))
            _MODEL_INSTANCE = Model(
                str(model_path),
                context_params={"use_gpu": False},
                params_sampling_strategy=1,
                beam_search={"beam_size": 5, "patience": -1.0},
                n_threads=threads,
                language="fr",
                translate=False,
                no_context=True,
                temperature=0.0,
                temperature_inc=0.0,
                print_progress=False,
                print_realtime=False,
                print_timestamps=False,
                suppress_blank=True,
                suppress_non_speech_tokens=True,
                redirect_whispercpp_logs_to=None
            )
        except ImportError:
            raise RuntimeError(
                "La bibliothèque 'pywhispercpp' n'est pas installée. "
                "Dans l'environnement Docker, elle est installée automatiquement."
            )
    return _MODEL_INSTANCE

def to_mono_16k(samples, rate: int):
    """Convertit n'importe quel signal audio en float32 mono à 16 000 Hz pour Whisper."""
    import numpy as np
    from scipy.signal import resample_poly

    if rate <= 0 or samples.size == 0:
        raise ValueError("Flux audio vide ou fréquence d’échantillonnage invalide.")

    # Normalisation vers [-1.0, 1.0]
    if samples.dtype.kind == "i":
        samples = samples.astype(np.float32) / (2 ** (samples.dtype.itemsize * 8 - 1))
    elif samples.dtype == np.uint8:
        samples = (samples.astype(np.float32) - 128) / 128
    elif samples.dtype.kind == "f":
        samples = samples.astype(np.float32)
    else:
        raise ValueError("Format d'échantillonnage audio non pris en charge.")

    # Mixage stéréo vers mono
    if samples.ndim == 2:
        samples = samples.mean(axis=1)

    if samples.ndim != 1 or not np.isfinite(samples).all():
        raise ValueError("Données audio corrompues ou non finies.")

    # Rééchantillonnage à 16 kHz
    if rate != 16000:
        divisor = math.gcd(int(rate), 16000)
        samples = resample_poly(samples, 16000 // divisor, int(rate) // divisor)

    return np.ascontiguousarray(np.clip(samples, -1.0, 1.0), dtype=np.float32)

def read_audio_file(file_path: Path):
    """Lit un fichier audio WAV ou le convertit via ffmpeg s'il est au format webm/mp3/ogg."""
    from scipy.io import wavfile

    suffix = file_path.suffix.lower()
    if suffix == ".wav":
        try:
            rate, samples = wavfile.read(str(file_path))
            return samples, rate
        except Exception:
            pass # Essayer avec ffmpeg si le wav a un encodage exotique

    # Conversion avec ffmpeg vers un WAV PCM standard temporaire
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
        tmp_wav_path = tmp_wav.name

    try:
        cmd = [
            "ffmpeg", "-y", "-i", str(file_path),
            "-ar", "16000", "-ac", "1", "-f", "wav", tmp_wav_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode != 0:
            raise RuntimeError(f"Échec de la conversion audio ffmpeg : {res.stderr.decode('utf-8', errors='ignore')}")
        rate, samples = wavfile.read(tmp_wav_path)
        return samples, rate
    finally:
        if os.path.exists(tmp_wav_path):
            os.remove(tmp_wav_path)

def transcribe_audio_bytes(audio_bytes: bytes, filename: str = "audio.wav", language: str = "fr") -> str:
    """Point d'entrée principal pour transcrire des octets audio reçus via HTTP."""
    import numpy as np

    suffix = Path(filename).suffix or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp_file:
        tmp_file.write(audio_bytes)
        tmp_path = Path(tmp_file.name)

    try:
        samples, rate = read_audio_file(tmp_path)
        mono_16k = to_mono_16k(samples, rate)

        # Détection du silence
        rms = float(np.sqrt(np.mean(mono_16k.astype(np.float64) ** 2)))
        if rms < 0.0001:
            return ""

        model = get_whisper_model()
        segments = model.transcribe(mono_16k, language=language)
        return " ".join(segment.text.strip() for segment in segments).strip()
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

