import pytest
import asyncio
from app.services.semantic_service import semantic_service
from app.services.audio_service import audio_service
from app.services.footage_service import footage_service
from app.services.rendering_service import ASPECT_RATIO_CONFIGS
from app.core.exceptions import (
    AudioValidationException,
    AudioCorruptedException,
    SilentAudioException,
    InvalidInputException
)
from app.models.job import JobRecord, SceneData
from app.workers.task_runner import process_job
from app.workers.queue import job_repo


def test_hidden_test_1_abstract_concepts_and_statistics():
    # "Trust is earned slowly."
    analysis_trust = semantic_service.analyze_hard_cases("Trust is earned slowly.")
    assert any("handshake" in q or "foundation" in q or "partnership" in q for q in analysis_trust["all_queries"])
    assert analysis_trust["detected_concept"] == "trust"

    # "Sales grew 40% in 2025."
    analysis_stats = semantic_service.analyze_hard_cases("Sales grew 40% in 2025.")
    assert analysis_stats["detected_concept"] == "statistics_growth"
    assert any("chart" in q or "analytics" in q or "graph" in q for q in analysis_stats["all_queries"])


def test_hidden_test_2_named_entities_and_ambiguous_words():
    # Named person & brand
    analysis_celeb = semantic_service.analyze_hard_cases("Elon Musk announced a new Apple iPhone.")
    assert len(analysis_celeb["warnings"]) >= 2
    assert "elon musk" in analysis_celeb["neutralized_entities"]
    assert "apple" in analysis_celeb["neutralized_entities"]

    # Ambiguous terms
    cloud_tech = semantic_service.analyze_hard_cases("Cloud computing servers and database infrastructure.")
    assert "data center" in cloud_tech["primary_query"] or "server" in cloud_tech["primary_query"]

    python_code = semantic_service.analyze_hard_cases("Python programming language syntax and functions.")
    assert "programming" in python_code["primary_query"] or "code" in python_code["primary_query"]

    bank_fin = semantic_service.analyze_hard_cases("Save money in your bank account.")
    assert "financial" in bank_fin["primary_query"] or "bank" in bank_fin["primary_query"]


def test_hidden_test_3_sensitive_news_and_9_16_framing():
    # Sensitive news
    analysis_sad = semantic_service.analyze_hard_cases("A tragic accident occurred and people gathered in mourning.")
    assert analysis_sad["is_sensitive"] is True
    assert len(analysis_sad["warnings"]) > 0
    assert "memorial" in analysis_sad["primary_query"] or "dawn" in analysis_sad["primary_query"]

    # 9:16 portrait framing: verify blurred background composite filter exists
    cfg_9_16 = ASPECT_RATIO_CONFIGS["9:16"]
    assert "boxblur" in cfg_9_16["complex_filter"]
    assert "overlay" in cfg_9_16["complex_filter"]


def test_hidden_test_4_input_validation(tmp_path):
    # Corrupt audio
    corrupt_file = tmp_path / "bad.mp3"
    corrupt_file.write_bytes(b"not an mp3")
    with pytest.raises(AudioCorruptedException):
        audio_service.validate_file_metadata(str(corrupt_file), filename="bad.mp3")

    # Invalid extension
    bad_ext = tmp_path / "song.flac"
    bad_ext.write_bytes(b"dummy")
    with pytest.raises(AudioValidationException):
        audio_service.validate_file_metadata(str(bad_ext), filename="song.flac")


@pytest.mark.asyncio
async def test_hidden_test_5_provider_fallback_and_no_duplicate_clips(tmp_path):
    # Test that footage selection never uses duplicate clips and falls back safely
    scenes = [
        SceneData(0, "First cloud computing scene.", 0.0, 4.0, 4.0, "cloud", None, "cloud", "cloud"),
        SceneData(1, "Second cloud computing scene.", 4.0, 8.0, 4.0, "cloud", None, "cloud", "cloud"),
    ]
    job_dir = str(tmp_path / "job_fallback_test")

    await footage_service.select_footage_for_scenes(
        scenes=scenes,
        job_dir=job_dir,
        forced_provider="mock"
    )

    # Must-have 5: No clip is used twice in one video
    clip0 = scenes[0].selected_clip
    clip1 = scenes[1].selected_clip
    assert clip0 is not None
    assert clip1 is not None
    assert clip0.clip_id != clip1.clip_id, "Rule violation: Duplicate clip selected!"
