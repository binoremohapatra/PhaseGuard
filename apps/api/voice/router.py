"""
voice/router.py — FastAPI router for voice/TTS endpoints.

Provides REST endpoints for:
- TTS synthesis: POST /api/v1/voice/tts
- Voice enrollment: POST /api/v1/voice/enroll
- Health check: GET /api/v1/voice/health
"""

from __future__ import annotations

import io
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

from core.auth import require_call_token
from core.config import get_settings
from database import get_db_session
from voice.models import (
    TTSError,
    TTSErrorCode,
    TTSRequest,
    TTSResponse,
    VoiceEnrollRequest,
    VoiceEnrollResponse,
    VoiceProfile,
)
from voice.provider import FishTTSProvider
from voice.service import get_voice_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/voice", tags=["voice"])


# ── Dependency: Auth (reuse existing PhaseGuard auth) ────────────────────────

async def get_current_user():
    """
    Get current user from token.

    For now, we use the existing call token auth.
    In a full implementation, this would validate user/tenant claims.
    """
    # For MVP, we don't enforce user-level auth
    # TODO: Add proper user authentication
    return None


# ── POST /api/v1/voice/tts ─────────────────────────────────────────────────────

@router.post("/tts")
async def text_to_speech(
    request: TTSRequest,
    db = Depends(get_db_session),
    current_user = Depends(get_current_user),
):
    """
    Synthesize text to speech using the configured TTS provider.

    Accepts:
    - text: Text to synthesize
    - voice_id: Optional internal voice profile ID
    - format: Output format (mp3, wav, opus)
    - stream: Whether to stream response (not yet implemented)

    Returns audio data in the requested format.
    """
    cfg = get_settings()
    service = get_voice_service(db_session=db)

    # Initialize provider if not set
    if request.provider == "fish":
        if not cfg.fish_api_key:
            raise HTTPException(
                status_code=503,
                detail="Fish Audio not configured (missing FISH_API_KEY)",
            )
        try:
            service.get_provider()
        except TTSError:
            service.set_provider(FishTTSProvider())
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported provider: {request.provider}",
        )

    try:
        # Resolve voice ID if provided
        provider_voice_id = None
        if request.voice_id:
            provider_voice_id = await service.resolve_provider_voice_id(request.voice_id)
            if not provider_voice_id:
                raise TTSError(
                    code=TTSErrorCode.VOICE_NOT_FOUND,
                    message=f"Voice profile not found: {request.voice_id}",
                )

        audio_bytes = await service.synthesize(
            text=request.text,
            voice_id=provider_voice_id,
            format=request.format,
        )

        # Return audio as StreamingResponse
        media_type = "audio/mpeg" if request.format == "mp3" else "audio/wav"
        return StreamingResponse(
            io.BytesIO(audio_bytes),
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename=speech.{request.format}"
            }
        )

    except TTSError as e:
        # Map TTSError to HTTP status codes
        status_code = 500
        if e.code in [
            TTSErrorCode.PROVIDER_NOT_CONFIGURED,
            TTSErrorCode.VOICE_NOT_FOUND,
            TTSErrorCode.INVALID_TEXT,
        ]:
            status_code = 400
        elif e.code == TTSErrorCode.FISH_AUTHENTICATION_ERROR:
            status_code = 401
        elif e.code == TTSErrorCode.FISH_RATE_LIMITED:
            status_code = 429
        elif e.code == TTSErrorCode.FISH_UNAVAILABLE:
            status_code = 503

        raise HTTPException(
            status_code=status_code,
            detail={
                "code": e.code.value,
                "message": e.message,
                "provider_detail": e.provider_detail,
            },
        )


# ── POST /api/v1/voice/enroll ───────────────────────────────────────────────────

@router.post("/enroll", response_model=VoiceEnrollResponse)
async def enroll_voice(
    audio: UploadFile = File(..., description="Audio file for voice enrollment"),
    display_name: str = Form(..., description="Display name for the voice"),
    enhance_quality: bool = Form(True, description="Enhance audio quality"),
    db = Depends(get_db_session),
    current_user = Depends(get_current_user),
) -> VoiceEnrollResponse:
    """
    Enroll a voice sample for cloning.

    Accepts an audio file and creates a voice profile using the provider's
    voice cloning capability.

    Supported audio formats: WAV, MP3, OGG, etc.
    Recommended duration: 10-30 seconds.
    """
    cfg = get_settings()

    # Validate file - check filename extension (content-type may not be set by curl)
    filename = audio.filename.lower() if audio.filename else ""
    valid_extensions = ['.wav', '.mp3', '.ogg', '.m4a', '.flac']

    # Debug log
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Voice enrollment attempt: filename='{audio.filename}', content_type='{audio.content_type}'")

    # Simply check if filename contains audio extension
    is_audio = any(ext in filename for ext in valid_extensions)

    if not is_audio:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Expected audio file (WAV, MP3, OGG, etc.). Got filename={audio.filename}",
        )

    # Read audio data
    audio_data = await audio.read()

    # Validate size (max 10MB)
    if len(audio_data) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="Audio file too large. Maximum size is 10MB.",
        )

    # Validate minimum size (at least 1KB)
    if len(audio_data) < 1024:
        raise HTTPException(
            status_code=400,
            detail="Audio file too small or empty.",
        )

    # Initialize Fish provider directly
    if not cfg.fish_api_key:
        raise HTTPException(
            status_code=503,
            detail="Fish Audio not configured (missing FISH_API_KEY)",
        )

    provider = FishTTSProvider()

    if not provider.supports_voice_cloning():
        raise HTTPException(
            status_code=400,
            detail="Provider does not support voice cloning",
        )

    try:
        # Create voice reference via provider
        voice_profile = await provider.create_voice_reference(
            audio_data=audio_data,
            display_name=display_name,
            user_id=current_user.get("id") if current_user else None,
        )

        # Store profile in service for later use
        service = get_voice_service(db_session=db)
        service.set_provider(FishTTSProvider())  # Set provider for future TTS calls
        await service.create_voice_profile(voice_profile)

        return VoiceEnrollResponse(
            voice_profile=voice_profile,
            status="enrolled",
        )

    except TTSError as e:
        status_code = 500
        if e.code in [
            TTSErrorCode.PROVIDER_NOT_CONFIGURED,
            TTSErrorCode.INVALID_AUDIO,
        ]:
            status_code = 400
        elif e.code == TTSErrorCode.FISH_AUTHENTICATION_ERROR:
            status_code = 401
        elif e.code == TTSErrorCode.FISH_RATE_LIMITED:
            status_code = 429

        raise HTTPException(
            status_code=status_code,
            detail={
                "code": e.code.value,
                "message": e.message,
                "provider_detail": e.provider_detail,
            },
        )


# ── GET /api/v1/voice/health ────────────────────────────────────────────────────

@router.get("/health")
async def health_check(db = Depends(get_db_session)):
    """
    Health check for the voice service.

    Returns status of the voice service and configured provider.
    """
    cfg = get_settings()
    service = get_voice_service(db_session=db)

    # Initialize provider if configured
    if cfg.fish_api_key:
        try:
            service.get_provider()
        except TTSError:
            service.set_provider(FishTTSProvider())

    health = await service.health_check()
    return health


# ── GET /api/v1/voice/voices ────────────────────────────────────────────────────

@router.get("/voices", response_model=list[VoiceProfile])
async def list_voices(
    db = Depends(get_db_session),
    current_user = Depends(get_current_user),
) -> list[VoiceProfile]:
    """
    List enrolled voice profiles.

    Returns all voice profiles, optionally filtered by user.
    """
    service = get_voice_service(db_session=db)
    user_id = current_user.get("id") if current_user else None
    return await service.list_voice_profiles(user_id=user_id)


# ── DELETE /api/v1/voice/voices/{voice_id} ───────────────────────────────────────

@router.delete("/voices/{voice_id}")
async def delete_voice(
    voice_id: str,
    db = Depends(get_db_session),
    current_user = Depends(get_current_user),
):
    """
    Delete a voice profile.

    Parameters
    ----------
    voice_id : str
        Internal voice profile ID.
    """
    service = get_voice_service(db_session=db)

    # Verify ownership if user is authenticated
    profile = await service.get_voice_profile(voice_id)
    if profile:
        if current_user and profile.user_id and profile.user_id != current_user.get("id"):
            raise HTTPException(
                status_code=403,
                detail="You do not own this voice profile",
            )

    deleted = await service.delete_voice_profile(voice_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Voice profile not found",
        )

    return {"status": "deleted", "voice_id": voice_id}
