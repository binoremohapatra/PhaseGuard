"""
dsp/hf_ml.py — Hugging Face Inference API integration for deepfake detection.

Uses a pre-trained Audio Classification model on HuggingFace to detect
spoofed/AI-generated audio as a replacement for pure DSP.
"""
import io
import time
import logging
import httpx
import numpy as np
import scipy.io.wavfile

from core.config import get_settings

logger = logging.getLogger(__name__)

# A public model for spoofing/deepfake detection on HF
# Note: You can replace this with any specific ASVspoof model URL
HF_API_URL = "https://api-inference.huggingface.co/models/aalimamac/hubert-base-ls960-asvspoof"

async def analyze_audio_hf(window: np.ndarray, fs: int = 16_000) -> dict:
    """
    Send the audio window to Hugging Face Inference API.
    Returns a dictionary with the ML analysis result.
    """
    cfg = get_settings()
    if not cfg.hf_api_token:
        return {"error": "No HF token"}

    t0 = time.perf_counter()

    # Convert float32 numpy array to 16-bit PCM WAV in memory
    buf = io.BytesIO()
    audio_int16 = (window * 32767).astype(np.int16)
    scipy.io.wavfile.write(buf, fs, audio_int16)
    audio_bytes = buf.getvalue()

    headers = {
        "Authorization": f"Bearer {cfg.hf_api_token}",
        "Content-Type": "audio/wav"
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(HF_API_URL, headers=headers, content=audio_bytes)
            
            # 503 means model is loading
            if resp.status_code == 503:
                return {"status": "loading", "compute_ms": (time.perf_counter() - t0) * 1000}
                
            resp.raise_for_status()
            data = resp.json()
            
            # Format expected from HF Audio Classification
            # e.g., [{"label": "fake", "score": 0.98}, {"label": "real", "score": 0.02}]
            if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                # Map ASVspoof labels (e.g. "spoof", "fake") to boolean
                top_label = data[0].get("label", "unknown").lower()
                score = data[0].get("score", 0.0)
                is_synthetic = score > 0.5 if ("fake" in top_label or "spoof" in top_label) else False
                
                return {
                    "status": "success",
                    "is_synthetic": is_synthetic,
                    "top_label": top_label,
                    "score": score,
                    "compute_ms": (time.perf_counter() - t0) * 1000,
                    "raw_output": data
                }
            return {"status": "error", "message": "Unexpected HF response format"}
            
    except Exception as e:
        logger.warning(f"HF API Error: {e}")
        return {"status": "error", "message": str(e)}
