"""
voice/service.py — Voice service for TTS routing and voice profile management.

Manages voice profiles using PostgreSQL database for persistence
and routes TTS requests to the appropriate provider.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from database import VoiceProfileDB
from voice.models import TTSError, TTSErrorCode, VoiceProfile
from voice.provider import FishTTSProvider, TTSProvider

logger = logging.getLogger(__name__)


class VoiceService:
    """
    Service for managing voice profiles and TTS operations.

    - Stores voice profiles in PostgreSQL database
    - Routes TTS requests to configured provider
    - Resolves internal voice IDs to provider-specific IDs
    """

    def __init__(self, db_session: Optional[AsyncSession] = None):
        self._provider: Optional[TTSProvider] = None
        self._db_session: Optional[AsyncSession] = db_session

    def set_provider(self, provider: TTSProvider):
        """Set the active TTS provider."""
        self._provider = provider
        logger.info(f"VoiceService: Provider set to {type(provider).__name__}")

    def get_provider(self) -> TTSProvider:
        """Get the active TTS provider."""
        if self._provider is None:
            raise TTSError(
                code=TTSErrorCode.PROVIDER_NOT_CONFIGURED,
                message="No TTS provider configured",
            )
        return self._provider

    async def create_voice_profile(
        self,
        profile: VoiceProfile,
    ) -> VoiceProfile:
        """
        Store a voice profile in database.

        Parameters
        ----------
        profile : VoiceProfile
            Voice profile to store.

        Returns
        -------
        VoiceProfile
            Stored profile.
        """
        if self._db_session:
            # Save to database
            db_profile = VoiceProfileDB(
                id=profile.id,
                provider=profile.provider,
                provider_voice_id=profile.provider_voice_id,
                display_name=profile.display_name,
                status=profile.status,
                user_id=profile.user_id,
                profile_metadata=json.dumps(profile.metadata) if profile.metadata else None,
            )
            self._db_session.add(db_profile)
            await self._db_session.commit()
            await self._db_session.refresh(db_profile)
            logger.info(
                f"VoiceService: Created voice profile {profile.id} in database "
                f"(provider={profile.provider}, display_name={profile.display_name})"
            )
        else:
            # Fallback to in-memory (should not happen in production)
            logger.warning("VoiceService: No database session, using in-memory storage")
            if not hasattr(self, '_voice_profiles'):
                self._voice_profiles = {}
            self._voice_profiles[profile.id] = profile
            logger.info(
                f"VoiceService: Created voice profile {profile.id} in memory "
                f"(provider={profile.provider}, display_name={profile.display_name})"
            )
        return profile

    async def get_voice_profile(self, voice_id: str) -> Optional[VoiceProfile]:
        """
        Retrieve a voice profile by internal ID from database.

        Parameters
        ----------
        voice_id : str
            Internal voice profile ID.

        Returns
        -------
        VoiceProfile or None
            Voice profile if found.
        """
        if self._db_session:
            # Query from database
            from sqlalchemy import select
            result = await self._db_session.execute(
                select(VoiceProfileDB).where(VoiceProfileDB.id == voice_id)
            )
            db_profile = result.scalar_one_or_none()
            if db_profile:
                return VoiceProfile(
                    id=db_profile.id,
                    provider=db_profile.provider,
                    provider_voice_id=db_profile.provider_voice_id,
                    display_name=db_profile.display_name,
                    status=db_profile.status,
                    user_id=db_profile.user_id,
                    created_at=db_profile.created_at,
                    metadata=json.loads(db_profile.profile_metadata) if db_profile.profile_metadata else None,
                )
        else:
            # Fallback to in-memory
            if not hasattr(self, '_voice_profiles'):
                self._voice_profiles = {}
            return self._voice_profiles.get(voice_id)
        return None

    async def resolve_provider_voice_id(self, voice_id: str) -> Optional[str]:
        """
        Resolve internal voice ID to provider-specific voice ID.

        Parameters
        ----------
        voice_id : str
            Internal voice profile ID (or raw provider ID if not found).

        Returns
        -------
        str or None
            Provider-specific voice ID.
        """
        profile = await self.get_voice_profile(voice_id)
        if profile:
            return profile.provider_voice_id
        # If not found, assume it's already a provider ID
        return voice_id

    async def delete_voice_profile(self, voice_id: str) -> bool:
        """
        Delete a voice profile from database.

        Parameters
        ----------
        voice_id : str
            Internal voice profile ID.

        Returns
        -------
        bool
            True if deleted, False if not found.
        """
        if self._db_session:
            # Delete from database
            from sqlalchemy import delete
            result = await self._db_session.execute(
                delete(VoiceProfileDB).where(VoiceProfileDB.id == voice_id)
            )
            await self._db_session.commit()
            deleted = result.rowcount > 0
            if deleted:
                logger.info(f"VoiceService: Deleted voice profile {voice_id} from database")
            return deleted
        else:
            # Fallback to in-memory
            if not hasattr(self, '_voice_profiles'):
                self._voice_profiles = {}
            if voice_id in self._voice_profiles:
                del self._voice_profiles[voice_id]
                logger.info(f"VoiceService: Deleted voice profile {voice_id} from memory")
                return True
        return False

    async def list_voice_profiles(self, user_id: Optional[str] = None) -> list[VoiceProfile]:
        """
        List voice profiles from database, optionally filtered by user.

        Parameters
        ----------
        user_id : str, optional
            Filter by user ID.

        Returns
        -------
        list[VoiceProfile]
            List of voice profiles.
        """
        if self._db_session:
            # Query from database
            from sqlalchemy import select
            query = select(VoiceProfileDB)
            if user_id:
                query = query.where(VoiceProfileDB.user_id == user_id)
            result = await self._db_session.execute(query)
            db_profiles = result.scalars().all()
            profiles = []
            for db_profile in db_profiles:
                profiles.append(VoiceProfile(
                    id=db_profile.id,
                    provider=db_profile.provider,
                    provider_voice_id=db_profile.provider_voice_id,
                    display_name=db_profile.display_name,
                    status=db_profile.status,
                    user_id=db_profile.user_id,
                    created_at=db_profile.created_at,
                    metadata=json.loads(db_profile.profile_metadata) if db_profile.profile_metadata else None,
                ))
            return profiles
        else:
            # Fallback to in-memory
            if not hasattr(self, '_voice_profiles'):
                self._voice_profiles = {}
            profiles = list(self._voice_profiles.values())
            if user_id:
                profiles = [p for p in profiles if p.user_id == user_id]
            return profiles

    async def synthesize(
        self,
        text: str,
        voice_id: Optional[str] = None,
        format: str = "mp3",
    ) -> bytes:
        """
        Synthesize text to audio using the configured provider.

        Parameters
        ----------
        text : str
            Text to synthesize.
        voice_id : str, optional
            Internal voice profile ID.
        format : str
            Output format.

        Returns
        -------
        bytes
            Audio data.

        Raises
        ------
        TTSError
            If synthesis fails.
        """
        provider = self.get_provider()

        # Resolve internal voice ID to provider-specific ID
        provider_voice_id = None
        if voice_id:
            provider_voice_id = await self.resolve_provider_voice_id(voice_id)
            if not provider_voice_id:
                raise TTSError(
                    code=TTSErrorCode.VOICE_NOT_FOUND,
                    message=f"Voice profile not found: {voice_id}",
                )

        return await provider.synthesize(text, provider_voice_id, format)

    async def stream(
        self,
        text: str,
        voice_id: Optional[str] = None,
        format: str = "mp3",
    ):
        """
        Stream synthesized audio.

        Parameters
        ----------
        text : str
            Text to synthesize.
        voice_id : str, optional
            Internal voice profile ID.
        format : str
            Output format.

        Yields
        ------
        bytes
            Audio chunks.
        """
        provider = self.get_provider()

        # Resolve internal voice ID to provider-specific ID
        provider_voice_id = None
        if voice_id:
            provider_voice_id = await self.resolve_provider_voice_id(voice_id)
            if not provider_voice_id:
                raise TTSError(
                    code=TTSErrorCode.VOICE_NOT_FOUND,
                    message=f"Voice profile not found: {voice_id}",
                )

        async for chunk in provider.stream(text, provider_voice_id, format):
            yield chunk

    async def health_check(self) -> dict:
        """
        Check health of the voice service and provider.

        Returns
        -------
        dict
            Health status.
        """
        provider_healthy = False
        provider_name = "none"

        if self._provider:
            provider_name = type(self._provider).__name__
            provider_healthy = await self._provider.health_check()

        # Count profiles from database or in-memory
        if self._db_session:
            from sqlalchemy import select, func
            result = await self._db_session.execute(
                select(func.count()).select_from(VoiceProfileDB)
            )
            profiles_count = result.scalar()
        else:
            if not hasattr(self, '_voice_profiles'):
                self._voice_profiles = {}
            profiles_count = len(self._voice_profiles)

        return {
            "service": "voice",
            "provider": provider_name,
            "provider_healthy": provider_healthy,
            "voice_profiles_count": profiles_count,
        }


# Global singleton instance
_voice_service: Optional[VoiceService] = None


def get_voice_service(db_session: Optional[AsyncSession] = None) -> VoiceService:
    """
    Get the global VoiceService instance.

    Parameters
    ----------
    db_session : AsyncSession, optional
        Database session for persistence. If provided, service will use database.
        If not provided, falls back to in-memory storage.

    Returns
    -------
    VoiceService
        Voice service instance.
    """
    global _voice_service
    if _voice_service is None:
        _voice_service = VoiceService(db_session=db_session)
    elif db_session and _voice_service._db_session != db_session:
        # Update session if provided
        _voice_service._db_session = db_session
    return _voice_service
