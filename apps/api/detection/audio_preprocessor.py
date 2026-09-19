"""
Audio Preprocessor for PhaseGuard Deepfake Detection
Shared preprocessing pipeline for all detection models
"""
import numpy as np
import librosa
import io
from typing import Tuple, Optional
import soundfile as sf


class AudioPreprocessor:
    """Standardized audio preprocessing for deepfake detection."""

    def __init__(self, target_sr: int = 16000, target_duration: float = 3.0):
        """
        Initialize audio preprocessor.

        Args:
            target_sr: Target sample rate (default 16000 Hz)
            target_duration: Target duration in seconds (default 3.0)
        """
        self.target_sr = target_sr
        self.target_duration = target_duration
        self.target_samples = int(target_sr * target_duration)

    def preprocess_audio_bytes(self, audio_bytes: bytes) -> np.ndarray:
        """
        Preprocess audio bytes to standardized format.

        Args:
            audio_bytes: Raw audio bytes

        Returns:
            Preprocessed audio array (float32, 16kHz, mono)
        """
        try:
            # Load audio from bytes
            audio, sr = librosa.load(io.BytesIO(audio_bytes), sr=None, mono=True)

            # Resample to target sample rate
            if sr != self.target_sr:
                audio = librosa.resample(audio, orig_sr=sr, target_sr=self.target_sr)

            # Pad or crop to target duration
            audio = self._pad_or_crop(audio)

            # Normalize safely
            audio = self._normalize_audio(audio)

            return audio.astype(np.float32)

        except Exception as e:
            print(f"Error preprocessing audio: {e}")
            raise

    def preprocess_audio_file(self, file_path: str) -> np.ndarray:
        """
        Preprocess audio file to standardized format.

        Args:
            file_path: Path to audio file

        Returns:
            Preprocessed audio array (float32, 16kHz, mono)
        """
        try:
            # Load audio file
            audio, sr = librosa.load(file_path, sr=None, mono=True)

            # Resample to target sample rate
            if sr != self.target_sr:
                audio = librosa.resample(audio, orig_sr=sr, target_sr=self.target_sr)

            # Pad or crop to target duration
            audio = self._pad_or_crop(audio)

            # Normalize safely
            audio = self._normalize_audio(audio)

            return audio.astype(np.float32)

        except Exception as e:
            print(f"Error preprocessing audio file: {e}")
            raise

    def _pad_or_crop(self, audio: np.ndarray) -> np.ndarray:
        """Pad or crop audio to target duration."""
        if len(audio) > self.target_samples:
            return audio[:self.target_samples]
        elif len(audio) < self.target_samples:
            return np.pad(audio, (0, self.target_samples - len(audio)))
        return audio

    def _normalize_audio(self, audio: np.ndarray) -> np.ndarray:
        """Safely normalize audio (avoid division by zero)."""
        max_val = np.max(np.abs(audio))
        if max_val > 1e-8:
            return audio / max_val
        return audio

    def detect_low_energy(self, audio: np.ndarray, threshold: float = 0.01) -> bool:
        """
        Detect if audio has extremely low energy (silence).

        Args:
            audio: Audio array
            threshold: Energy threshold

        Returns:
            True if audio has low energy
        """
        energy = np.mean(audio ** 2)
        return energy < threshold

    def apply_window(self, audio: np.ndarray, window_seconds: float = 3.0,
                    hop_seconds: float = 1.0) -> list:
        """
        Apply sliding window to audio.

        Args:
            audio: Audio array
            window_seconds: Window duration in seconds
            hop_seconds: Hop duration in seconds

        Returns:
            List of audio windows
        """
        window_samples = int(window_seconds * self.target_sr)
        hop_samples = int(hop_seconds * self.target_sr)

        windows = []
        for start in range(0, len(audio) - window_samples + 1, hop_samples):
            window = audio[start:start + window_samples]
            windows.append(window)

        return windows


# Global preprocessor instance
_audio_preprocessor: Optional[AudioPreprocessor] = None


def get_audio_preprocessor() -> AudioPreprocessor:
    """Get or create global audio preprocessor instance."""
    global _audio_preprocessor
    if _audio_preprocessor is None:
        _audio_preprocessor = AudioPreprocessor()
    return _audio_preprocessor
