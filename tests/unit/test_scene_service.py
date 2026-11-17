import pytest
from app.services.scene_service import scene_segmentation_service
from app.api.schemas.jobs import SceneInput


def test_segment_from_scene_inputs():
    scene_inputs = [
        SceneInput(text="First scene narration text.", visual_hint="corporate office"),
        SceneInput(text="Second scene discussing statistics.", visual_hint="financial charts"),
        SceneInput(text="Third scene concluding the message.", visual_hint="sunset view")
    ]
    total_duration = 15.0
    scenes = scene_segmentation_service.segment_from_scene_inputs(scene_inputs, total_duration)

    assert len(scenes) == 3
    assert scenes[0].start_time == 0.0
    assert scenes[-1].end_time == 15.0
    # Ensure seamless connection without gaps
    assert scenes[0].end_time == scenes[1].start_time
    assert scenes[1].end_time == scenes[2].start_time
    # Check visual hints preserved
    assert scenes[0].visual_hint == "corporate office"
    assert scenes[1].visual_hint == "financial charts"


def test_segment_from_plain_text():
    script = "Trust is earned slowly. Sales grew 40% in 2025. Modern cloud computing revolutionizes enterprise tech."
    total_duration = 12.0
    scenes = scene_segmentation_service.segment_from_transcription_or_text(script, total_duration)

    assert len(scenes) == 3
    assert scenes[0].start_time == 0.0
    assert scenes[-1].end_time == 12.0
    for s in scenes:
        assert s.duration > 0
        assert s.narration_text.strip() != ""
