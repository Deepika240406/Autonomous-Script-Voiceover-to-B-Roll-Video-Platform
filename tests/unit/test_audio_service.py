import os
import pytest
from app.services.audio_service import audio_service
from app.core.exceptions import (
    AudioValidationException,
    AudioCorruptedException,
    AudioTooLongException,
    SilentAudioException
)
from app.utils.ffmpeg import run_command_sync


@pytest.fixture(scope="module")
def sample_wav(tmp_path_factory):
    fn = tmp_path_factory.mktemp("audio") / "valid_tone.wav"
    cmd = ["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=3", str(fn)]
    run_command_sync(cmd)
    return str(fn)


@pytest.fixture(scope="module")
def silent_wav(tmp_path_factory):
    fn = tmp_path_factory.mktemp("audio") / "silent.wav"
    cmd = ["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", "3", str(fn)]
    run_command_sync(cmd)
    return str(fn)


def test_valid_audio_metadata(sample_wav):
    info = audio_service.validate_file_metadata(sample_wav)
    assert info["duration"] >= 2.9
    assert info["sample_rate"] > 0
    assert info["format_name"] == "wav"


def test_corrupted_audio_file(tmp_path):
    corrupt = tmp_path / "corrupt.mp3"
    corrupt.write_bytes(b"garbage bytes that do not form a valid mp3 audio stream")
    with pytest.raises(AudioCorruptedException):
        audio_service.validate_file_metadata(str(corrupt), filename="corrupt.mp3")


def test_silent_audio_rejection(silent_wav):
    with pytest.raises(SilentAudioException):
        audio_service.validate_file_metadata(silent_wav)


def test_invalid_extension(tmp_path):
    txt_file = tmp_path / "not_audio.txt"
    txt_file.write_text("hello")
    with pytest.raises(AudioValidationException):
        audio_service.validate_file_metadata(str(txt_file), filename="not_audio.txt")
