"""
voice/provider.py — TTS provider abstraction and Fish Audio implementation.

Defines the TTSProvider interface and implements FishTTSProvider using the
official Fish Audio API (https://api.fish.audio).

Fish API documentation verified:
- TTS endpoint: POST /v1/tts
- Model creation: POST /model
- Model: s2.1-pro-free (free tier)
- Authentication: Bearer token in Authorization header
- Model selection via `model` header
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Optional

import httpx

from core.config import get_settings
from voice.models import TTSError, TTSErrorCode, VoiceProfile

logger = logging.getLogger(__name__)


class TTSProvider(ABC):
    """
    Abstract base class for TTS providers.

    All provider implementations must implement these methods.
    This allows PhaseGuard to switch between providers without changing
    the rest of the application.
    """

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice_id: Optional[str] = None,
        format: str = "mp3",
    ) -> bytes:
        """
        Synthesize text to audio.

        Parameters
        ----------
        text : str
            Text to synthesize.
        voice_id : str, optional
            Provider-specific voice ID or internal voice profile ID.
        format : str
            Output format (mp3, wav, opus).

        Returns
        -------
        bytes
            Audio data.
        """
        pass

    @abstractmethod
    async def stream(
        self,
        text: str,
        voice_id: Optional[str] = None,
        format: str = "mp3",
    ):
        """
        Stream synthesized audio.

        Yields audio chunks as they are generated.

        Parameters
        ----------
        text : str
            Text to synthesize.
        voice_id : str, optional
            Provider-specific voice ID.
        format : str
            Output format.

        Yields
        ------
        bytes
            Audio chunks.
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the provider is available.

        Returns
        -------
        bool
            True if provider is healthy.
        """
        pass

    @abstractmethod
    def supports_voice_cloning(self) -> bool:
        """
        Check if provider supports voice cloning.

        Returns
        -------
        bool
            True if voice cloning is supported.
        """
        pass

    @abstractmethod
    async def create_voice_reference(
        self,
        audio_data: bytes,
        display_name: str,
        user_id: Optional[str] = None,
    ) -> VoiceProfile:
        """
        Create a voice reference from audio sample.

        Parameters
        ----------
        audio_data : bytes
            Audio sample data.
        display_name : str
            Display name for the voice.
        user_id : str, optional
            User/tenant ID for ownership tracking.

        Returns
        -------
        VoiceProfile
            Created voice profile.
        """
        pass


class FishTTSProvider(TTSProvider):
    """
    Fish Audio TTS provider implementation.

    Uses the Fish Audio API for TTS and voice cloning.
    Documentation: https://docs.fish.audio

    Configuration:
    - FISH_API_KEY: API key from Fish Audio
    - FISH_MODEL: Model to use (default: s2.1-pro-free)
    - FISH_BASE_URL: API base URL (default: https://api.fish.audio)
    """

    def __init__(self):
        self.cfg = get_settings()
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Lazy-initialize HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.cfg.fish_base_url,
                timeout=30.0,
            )
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _get_headers(self, model: Optional[str] = None) -> dict:
        """Build request headers with authentication."""
        headers = {
            "Authorization": f"Bearer {self.cfg.fish_api_key}",
            "Content-Type": "application/json",
        }
        if model:
            headers["model"] = model
        return headers

    async def synthesize(
        self,
        text: str,
        voice_id: Optional[str] = None,
        format: str = "mp3",
    ) -> bytes:
        """
        Synthesize text using Fish Audio TTS.

        Parameters
        ----------
        text : str
            Text to synthesize.
        voice_id : str, optional
            Fish Audio model ID (reference_id) or internal voice profile ID.
        format : str
            Output format (mp3, wav, opus).

        Returns
        -------
        bytes
            Audio data in requested format.

        Raises
        ------
        TTSError
            If synthesis fails.
        """
        if not self.cfg.fish_api_key:
            raise TTSError(
                code=TTSErrorCode.PROVIDER_NOT_CONFIGURED,
                message="Fish Audio API key not configured",
            )

        # Build request body per Fish API spec
        request_body = {
            "text": text,
            "format": format,
            "normalize": True,
        }

        # Add voice reference if provided
        if voice_id:
            request_body["reference_id"] = voice_id

        try:
            response = await self.client.post(
                "/v1/tts",
                headers=self._get_headers(model=self.cfg.fish_model),
                json=request_body,
            )
            response.raise_for_status()
            return response.content

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            if status_code == 401:
                raise TTSError(
                    code=TTSErrorCode.FISH_AUTHENTICATION_ERROR,
                    message="Fish Audio authentication failed",
                    provider_detail=str(e),
                )
            elif status_code == 402:
                raise TTSError(
                    code=TTSErrorCode.FISH_RATE_LIMITED,
                    message="Fish Audio rate limit or payment required",
                    provider_detail=str(e),
                )
            elif status_code == 503:
                raise TTSError(
                    code=TTSErrorCode.FISH_UNAVAILABLE,
                    message="Fish Audio service unavailable",
                    provider_detail=str(e),
                )
            else:
                raise TTSError(
                    code=TTSErrorCode.FISH_INVALID_REQUEST,
                    message=f"Fish Audio request failed: {status_code}",
                    provider_detail=str(e),
                )

        except httpx.TimeoutException as e:
            raise TTSError(
                code=TTSErrorCode.FISH_TIMEOUT,
                message="Fish Audio request timeout",
                provider_detail=str(e),
            )

        except Exception as e:
            logger.error(f"Fish Audio synthesis error: {e}")
            raise TTSError(
                code=TTSErrorCode.FISH_GENERATION_ERROR,
                message="Fish Audio synthesis failed",
                provider_detail=str(e),
            )

    async def stream(
        self,
        text: str,
        voice_id: Optional[str] = None,
        format: str = "mp3",
    ):
        """
        Stream synthesized audio from Fish Audio.

        Note: Fish Audio's REST API returns the full audio at once.
        For true streaming, use their WebSocket endpoint.
        This implementation yields the full response as a single chunk.

        Parameters
        ----------
        text : str
            Text to synthesize.
        voice_id : str, optional
            Fish Audio model ID.
        format : str
            Output format.

        Yields
        ------
        bytes
            Audio chunks.
        """
        audio_bytes = await self.synthesize(text, voice_id, format)
        yield audio_bytes

    async def health_check(self) -> bool:
        """
        Check Fish Audio service health.

        Attempts a simple TTS request with minimal text.

        Returns
        -------
        bool
            True if service is healthy.
        """
        if not self.cfg.fish_api_key:
            return False

        try:
            # Use a minimal text for health check
            await self.synthesize("Hi", format="mp3")
            return True
        except Exception as e:
            logger.warning(f"Fish Audio health check failed: {e}")
            return False

    def supports_voice_cloning(self) -> bool:
        """
        Fish Audio supports voice cloning via the /model endpoint.

        Returns
        -------
        bool
            True.
        """
        return True

    async def create_voice_reference(
        self,
        audio_data: bytes,
        display_name: str,
        user_id: Optional[str] = None,
    ) -> VoiceProfile:
        """
        Create a voice model in Fish Audio from audio sample.

        Uses the Fish Audio /model endpoint with train_mode=fast.

        Parameters
        ----------
        audio_data : bytes
            Audio sample data (WAV, MP3, etc.).
        display_name : str
            Display name for the voice.
        user_id : str, optional
            User/tenant ID for ownership tracking.

        Returns
        -------
        VoiceProfile
            Created voice profile with Fish Audio model ID.

        Raises
        ------
        TTSError
            If voice creation fails.
        """
        if not self.cfg.fish_api_key:
            raise TTSError(
                code=TTSErrorCode.PROVIDER_NOT_CONFIGURED,
                message="Fish Audio API key not configured",
            )

        # Prepare multipart form data per Fish API spec
        files = {
            "voices": ("voice_sample.wav", audio_data, "audio/wav"),
        }

        data = {
            "type": "tts",
            "title": display_name,
            "train_mode": "fast",
            "visibility": "private",
            "enhance_audio_quality": "true",
        }

        try:
            response = await self.client.post(
                "/model",
                headers={"Authorization": f"Bearer {self.cfg.fish_api_key}"},
                files=files,
                data=data,
            )
            response.raise_for_status()

            result = response.json()
            fish_model_id = result.get("_id") or result.get("id")

            if not fish_model_id:
                raise TTSError(
                    code=TTSErrorCode.FISH_GENERATION_ERROR,
                    message="Fish Audio did not return a model ID",
                    provider_detail=str(result),
                )

            return VoiceProfile(
                provider="fish",
                provider_voice_id=fish_model_id,
                display_name=display_name,
                user_id=user_id,
                metadata={"fish_response": result},
            )

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            if status_code == 401:
                raise TTSError(
                    code=TTSErrorCode.FISH_AUTHENTICATION_ERROR,
                    message="Fish Audio authentication failed",
                    provider_detail=str(e),
                )
            elif status_code == 402:
                raise TTSError(
                    code=TTSErrorCode.FISH_RATE_LIMITED,
                    message="Fish Audio rate limit or payment required",
                    provider_detail=str(e),
                )
            else:
                raise TTSError(
                    code=TTSErrorCode.FISH_INVALID_REQUEST,
                    message=f"Fish Audio voice creation failed: {status_code}",
                    provider_detail=str(e),
                )

        except Exception as e:
            logger.error(f"Fish Audio voice creation error: {e}")
            raise TTSError(
                code=TTSErrorCode.FISH_GENERATION_ERROR,
                message="Fish Audio voice creation failed",
                provider_detail=str(e),
            )
