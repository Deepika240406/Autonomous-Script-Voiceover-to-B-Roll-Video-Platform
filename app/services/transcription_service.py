import os
from typing import Dict, Any, Optional
from app.config import settings
from app.providers.speech.base import BaseSpeechProvider
from app.providers.speech.whisper_provider import WhisperSpeechProvider
from app.providers.speech.mock_provider import MockSpeechProvider
from app.core.logging import logger


class TranscriptionService:
    def __init__(self):
        self._whisper_provider = None
        self._mock_provider = MockSpeechProvider()

    def get_provider(self, force_mock: bool = False) -> BaseSpeechProvider:
        if force_mock:
            return self._mock_provider
        if self._whisper_provider is None:
            self._whisper_provider = WhisperSpeechProvider()
        return self._whisper_provider

    def transcribe_audio(self, audio_path: str, force_mock: bool = False) -> Dict[str, Any]:
        provider = self.get_provider(force_mock)
        logger.info(f"Starting audio transcription for {audio_path} using {provider.__class__.__name__}")
        return provider.transcribe(audio_path)


transcription_service = TranscriptionService()
