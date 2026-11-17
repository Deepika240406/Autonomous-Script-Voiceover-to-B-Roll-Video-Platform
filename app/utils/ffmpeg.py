import subprocess
import json
import os
import re
from typing import Dict, Any, Optional, Tuple
from app.config import settings
from app.core.exceptions import AudioCorruptedException, AudioValidationException, SilentAudioException, AudioTooLongException
from app.core.logging import logger


def run_command_sync(cmd: list, timeout: int = 120) -> Tuple[int, str, str]:
    logger.debug(f"Executing: {' '.join(cmd)}")
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout
    )
    return proc.returncode, proc.stdout, proc.stderr


def probe_media_file(file_path: str) -> Dict[str, Any]:
    """
    Runs ffprobe on a media file to inspect formats, streams, codecs, and durations.
    """
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        raise AudioCorruptedException(f"File {file_path} is missing or zero bytes.")

    cmd = [
        settings.FFPROBE_BINARY,
        "-v", "error",
        "-show_entries", "format=duration,size,bit_rate,format_name:stream=index,codec_type,codec_name,width,height,r_frame_rate,sample_rate,channels",
        "-of", "json",
        file_path
    ]
    code, stdout, stderr = run_command_sync(cmd, timeout=30)
    if code != 0:
        raise AudioCorruptedException(f"ffprobe failed to inspect file: {stderr.strip()}")

    try:
        data = json.loads(stdout)
        return data
    except Exception as e:
        raise AudioCorruptedException(f"Failed to parse ffprobe output: {e}")


def inspect_audio(file_path: str) -> Dict[str, Any]:
    """
    Inspects audio file and returns duration, sample_rate, channels, format.
    Validates duration against max limit.
    """
    info = probe_media_file(file_path)
    fmt = info.get("format", {})
    streams = info.get("streams", [])

    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
    if not audio_stream:
        raise AudioValidationException("No audio stream found in media file.")

    try:
        duration = float(fmt.get("duration", audio_stream.get("duration", 0)))
    except (TypeError, ValueError):
        duration = 0.0

    if duration <= 0:
        raise AudioCorruptedException("Audio stream has invalid or zero duration.")

    if duration > settings.MAX_AUDIO_DURATION_SECONDS:
        raise AudioTooLongException(
            f"Audio duration of {duration:.1f}s exceeds maximum allowed {settings.MAX_AUDIO_DURATION_SECONDS}s."
        )

    return {
        "duration": duration,
        "sample_rate": int(audio_stream.get("sample_rate", 44100)),
        "channels": int(audio_stream.get("channels", 2)),
        "codec_name": audio_stream.get("codec_name", "unknown"),
        "format_name": fmt.get("format_name", "unknown"),
        "size_bytes": int(fmt.get("size", os.path.getsize(file_path))),
    }


def analyze_audio_silence_and_energy(file_path: str) -> Dict[str, Any]:
    """
    Detects silence coverage and audio RMS volume levels using ffmpeg.
    Detects if the file is silent or purely non-speech noise.
    """
    # 1. Measure volume levels
    vol_cmd = [
        settings.FFMPEG_BINARY,
        "-i", file_path,
        "-af", "volumedetect",
        "-vn", "-sn", "-dn",
        "-f", "null",
        "-" if os.name != "nt" else "NUL"
    ]
    _, _, stderr = run_command_sync(vol_cmd, timeout=45)

    mean_volume = -99.0
    max_volume = -99.0

    mean_match = re.search(r"mean_volume:\s*(-?[\d\.]+)\s*dB", stderr)
    if mean_match:
        mean_volume = float(mean_match.group(1))

    max_match = re.search(r"max_volume:\s*(-?[\d\.]+)\s*dB", stderr)
    if max_match:
        max_volume = float(max_match.group(1))

    # Completely silent audio check
    if max_volume <= -60.0 or mean_volume <= -70.0:
        raise SilentAudioException(
            f"Audio is completely silent (max volume: {max_volume} dB, mean: {mean_volume} dB)."
        )

    # 2. Silence detection for coverage
    silence_cmd = [
        settings.FFMPEG_BINARY,
        "-i", file_path,
        "-af", "silencedetect=noise=-35dB:d=0.5",
        "-vn", "-sn", "-dn",
        "-f", "null",
        "-" if os.name != "nt" else "NUL"
    ]
    _, _, sil_stderr = run_command_sync(silence_cmd, timeout=45)

    silence_periods = []
    current_start = None
    for line in sil_stderr.splitlines():
        start_match = re.search(r"silence_start:\s*([\d\.]+)", line)
        if start_match:
            current_start = float(start_match.group(1))
        end_match = re.search(r"silence_end:\s*([\d\.]+)\s*\|\s*silence_duration:\s*([\d\.]+)", line)
        if end_match and current_start is not None:
            silence_periods.append({
                "start": current_start,
                "end": float(end_match.group(1)),
                "duration": float(end_match.group(2))
            })
            current_start = None

    total_silence = sum(p["duration"] for p in silence_periods)
    return {
        "mean_volume_db": mean_volume,
        "max_volume_db": max_volume,
        "total_silence_duration": total_silence,
        "silence_periods": silence_periods,
    }
