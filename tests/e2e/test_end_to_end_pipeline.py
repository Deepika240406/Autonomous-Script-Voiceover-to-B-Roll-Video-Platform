import os
import pytest
import time
import json
from app.models.job import JobRecord
from app.workers.task_runner import process_job
from app.workers.queue import job_repo
from app.utils.ffmpeg import probe_media_file


@pytest.mark.asyncio
async def test_full_pipeline_end_to_end(tmp_path):
    job_id = "e2e-test-job-001"
    request_params = {
        "script": "Trust is earned slowly. Sales grew 40% in 2025.",
        "voice": "en-IN-female",
        "aspect_ratios": ["16:9", "9:16"],
        "style": "bright, modern, real-world footage",
        "avoid": ["people's faces"],
        "captions": {"burn_in": True, "srt": True}
    }

    job = JobRecord(
        job_id=job_id,
        status="queued",
        progress=0,
        stage="queued",
        input_type="script",
        request_params=request_params
    )
    job_repo.save(job)

    # Execute full pipeline
    t_start = time.time()
    await process_job(job_id)
    total_time = time.time() - t_start

    finished_job = job_repo.get(job_id)
    assert finished_job.status == "succeeded"
    assert finished_job.progress == 100
    assert len(finished_job.scenes) >= 2

    # Verify 16:9 output
    assert "16:9" in finished_job.output_videos
    video_16_9_path = os.path.abspath(f"./storage_root/jobs/{job_id}/video_16_9.mp4")
    assert os.path.exists(video_16_9_path)
    info_16_9 = probe_media_file(video_16_9_path)
    v_stream_16_9 = next(s for s in info_16_9["streams"] if s["codec_type"] == "video")
    a_stream_16_9 = next(s for s in info_16_9["streams"] if s["codec_type"] == "audio")
    assert v_stream_16_9["width"] == 1920
    assert v_stream_16_9["height"] == 1080
    assert a_stream_16_9["codec_name"] == "aac"

    # Verify 9:16 output
    assert "9:16" in finished_job.output_videos
    video_9_16_path = os.path.abspath(f"./storage_root/jobs/{job_id}/video_9_16.mp4")
    assert os.path.exists(video_9_16_path)
    info_9_16 = probe_media_file(video_9_16_path)
    v_stream_9_16 = next(s for s in info_9_16["streams"] if s["codec_type"] == "video")
    assert v_stream_9_16["width"] == 1080
    assert v_stream_9_16["height"] == 1920

    # Verify captions.srt
    srt_path = os.path.abspath(f"./storage_root/jobs/{job_id}/captions.srt")
    assert os.path.exists(srt_path)
    with open(srt_path, "r", encoding="utf-8") as f:
        srt_content = f.read()
    assert "-->" in srt_content
    assert "Trust is earned slowly" in srt_content

    # Verify timeline.json
    timeline_path = os.path.abspath(f"./storage_root/jobs/{job_id}/timeline.json")
    assert os.path.exists(timeline_path)
    with open(timeline_path, "r", encoding="utf-8") as f:
        timeline_data = json.load(f)
    assert len(timeline_data["scenes"]) == len(finished_job.scenes)
    for sc in timeline_data["scenes"]:
        footage = sc["selected_footage"]
        assert footage["clip_id"] is not None
        assert footage["licence_name"] is not None
        assert footage["selection_reason"] is not None
        assert footage["relevance_score"] >= 1.0

    # Verify manifest.json
    manifest_path = os.path.abspath(f"./storage_root/jobs/{job_id}/manifest.json")
    assert os.path.exists(manifest_path)
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)
    assert manifest_data["job_id"] == job_id
    assert "cost_estimates_usd" in manifest_data
    assert "processing_timings_seconds" in manifest_data
    assert manifest_data["licensing_and_rights"]["commercial_usable"] is True
