import os
import httpx
import uuid
from typing import Dict, Any, Optional, List
from app.config import settings
from app.core.exceptions import (
    AudioValidationException,
    AudioCorruptedException,
    AudioTooLongException,
    SilentAudioException,
    MusicOnlyAudioException
)
from app.core.security import is_safe_url
from app.core.logging import logger
from app.utils.ffmpeg import inspect_audio, analyze_audio_silence_and_energy


ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a"}
ALLOWED_MIME_PREFIXES = {"audio/", "video/mp4", "application/octet-stream"}


class AudioService:
    def __init__(self, work_dir: str = "./storage_root/tmp_audio"):
        self.work_dir = os.path.abspath(work_dir)
        os.makedirs(self.work_dir, exist_ok=True)

    def validate_file_metadata(self, file_path: str, filename: Optional[str] = None) -> Dict[str, Any]:
        """
        Validates file extension, existence, size, and ffprobe stream metadata.
        """
        if not os.path.exists(file_path):
            raise AudioCorruptedException(f"Audio file '{file_path}' does not exist.")

        size = os.path.getsize(file_path)
        if size == 0:
            raise AudioCorruptedException("Audio file is 0 bytes.")

        if size > settings.MAX_UPLOAD_SIZE_BYTES:
            raise AudioValidationException(
                f"File size {size} bytes exceeds maximum allowed {settings.MAX_UPLOAD_SIZE_BYTES} bytes."
            )

        # Validate extension first if present
        check_name = filename or file_path
        _, ext = os.path.splitext(check_name.lower())
        if ext and ext not in ALLOWED_EXTENSIONS:
            raise AudioValidationException(
                f"Invalid file extension '{ext}'. Allowed extensions are: {sorted(list(ALLOWED_EXTENSIONS))}"
            )

        # Probe file via ffprobe
        info = inspect_audio(file_path)

        # If extension was not present, verify genuine audio codec
        if not ext:
            valid_codecs = {"mp3", "aac", "wav", "pcm_s16le", "flac", "m4a", "vorbis", "opus"}
            if info.get("codec_name") not in valid_codecs:
                raise AudioValidationException("Downloaded file has no recognizable audio format.")

        # Analyze silence and volume levels
        vol_info = analyze_audio_silence_and_energy(file_path)

        # If silence duration covers more than 90% of audio, reject as silent
        if info["duration"] > 3.0 and vol_info["total_silence_duration"] / info["duration"] > 0.90:
            raise SilentAudioException(
                f"Audio is over 90% silent ({vol_info['total_silence_duration']:.1f}s of {info['duration']:.1f}s)."
            )

        return {**info, **vol_info}

    async def download_audio_from_url(self, url: str) -> str:
        """
        Safely downloads audio from URL after SSRF validation.
        """
        is_safe_url(url, allow_local_for_dev=settings.DEBUG or settings.ENVIRONMENT == "development")

        dest_filename = f"downloaded_{uuid.uuid4().hex[:10]}"
        # Try to infer extension
        url_path = url.split("?")[0]
        _, ext = os.path.splitext(url_path.lower())
        if ext in ALLOWED_EXTENSIONS:
            dest_filename += ext
        else:
            dest_filename += ".mp3"

        dest_path = os.path.join(self.work_dir, dest_filename)

        try:
            async with httpx.AsyncClient(timeout=float(settings.REQUEST_TIMEOUT_SECONDS), follow_redirects=True) as client:
                async with client.stream("GET", url) as resp:
                    if resp.status_code >= 400:
                        raise AudioValidationException(f"Failed to download audio from URL: HTTP {resp.status_code}")

                    total_bytes = 0
                    with open(dest_path, "wb") as f:
                        async for chunk in resp.aiter_bytes(chunk_size=65536):
                            total_bytes += len(chunk)
                            if total_bytes > settings.MAX_UPLOAD_SIZE_BYTES:
                                raise AudioValidationException("Downloaded audio exceeds maximum file size limit.")
                            f.write(chunk)
        except httpx.RequestError as e:
            raise AudioValidationException(f"Network error while downloading audio: {str(e)}")

        self.validate_file_metadata(dest_path)
        return dest_path

    def detect_speech_boundaries(
        self,
        file_path: str,
        total_duration: float,
        word_timings: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, float]:
        """
        Detects actual speech termination and trailing silence in audio.
        Prevents captions and visual overlays from continuing past the end of spoken dialogue.
        """
        if word_timings and len(word_timings) > 0:
            last_word_end = max((w.get("end", 0.0) for w in word_timings), default=0.0)
            if last_word_end > 0.2:
                speech_end = min(total_duration, round(last_word_end, 3))
                return {
                    "speech_end": speech_end,
                    "trailing_silence": round(max(0.0, total_duration - speech_end), 3)
                }

        try:
            vol_info = analyze_audio_silence_and_energy(file_path)
            silence_periods = vol_info.get("silence_periods", [])
            if silence_periods:
                last_sil = silence_periods[-1]
                if last_sil["end"] >= total_duration - 0.25 or last_sil["start"] > total_duration - 3.5:
                    trailing_silence = max(0.0, total_duration - last_sil["start"])
                    speech_end = max(0.5, round(last_sil["start"], 3))
                    return {
                        "speech_end": speech_end,
                        "trailing_silence": round(trailing_silence, 3)
                    }
        except Exception as e:
            logger.debug(f"Audio trailing silence detection note: {e}")

        speech_end = round(max(0.5, total_duration - 0.3), 3)
        return {
            "speech_end": speech_end,
            "trailing_silence": round(max(0.0, total_duration - speech_end), 3)
        }


audio_service = AudioService()
