import os
from typing import Dict, Any, Optional
from app.config import settings
from app.providers.tts.base import BaseTTSProvider
from app.providers.tts.edge_tts_provider import EdgeTTSProvider
from app.providers.tts.pyttsx3_provider import Pyttsx3TTSProvider
from app.providers.tts.mock_provider import MockTTSProvider
from app.core.logging import logger


class TTSService:
    def __init__(self, default_provider_name: Optional[str] = None):
        self.provider_name = default_provider_name or settings.DEFAULT_TTS_PROVIDER
        self._providers = {
            "edge_tts": EdgeTTSProvider(),
            "pyttsx3": Pyttsx3TTSProvider(),
            "mock": MockTTSProvider(),
        }

    def get_provider(self, name: Optional[str] = None) -> BaseTTSProvider:
        key = name or self.provider_name
        return self._providers.get(key, self._providers["mock"])

    async def generate_narration(
        self,
        text: str,
        voice: Optional[str] = None,
        output_path: Optional[str] = None,
        force_provider: Optional[str] = None
    ) -> Dict[str, Any]:
        voice_id = voice or settings.DEFAULT_VOICE
        out = output_path or f"./storage_root/tmp_audio/tts_{os.urandom(6).hex()}.mp3"
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)

        provider_order = [force_provider] if force_provider else [self.provider_name, "pyttsx3", "mock"]

        last_error = None
        for prov_key in provider_order:
            if not prov_key or prov_key not in self._providers:
                continue
            prov = self._providers[prov_key]
            try:
                logger.info(f"Attempting TTS synthesis using provider '{prov_key}' for voice '{voice_id}'")
                result = await prov.synthesize(text, voice_id, out)
                result["provider"] = prov_key
                return result
            except Exception as e:
                logger.warning(f"TTS provider '{prov_key}' failed: {e}. Trying fallback...")
                last_error = e

        raise RuntimeError(f"All TTS providers failed: {last_error}")


tts_service = TTSService()
