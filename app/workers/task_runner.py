import os
import time
from datetime import datetime, timezone
from typing import Optional
from app.models.job import JobRecord, SceneData
from app.workers.queue import job_repo, get_job_queue
from app.services.audio_service import audio_service
from app.services.tts_service import tts_service
from app.services.transcription_service import transcription_service
from app.services.scene_service import scene_segmentation_service
from app.services.footage_service import footage_service
from app.services.rendering_service import rendering_service
from app.services.caption_service import caption_service
from app.services.manifest_service import manifest_service
from app.storage.s3_storage import get_storage
from app.core.callbacks import dispatch_callback
from app.core.logging import logger, job_id_ctx
from app.core.exceptions import IncuBrixException


async def process_job(job_id: str) -> None:
    job = job_repo.get(job_id)
    if not job:
        logger.error(f"Cannot process job {job_id}: not found in repo")
        return

    job_id_ctx.set(job_id)
    storage = get_storage()
    job_dir = os.path.abspath(f"./storage_root/jobs/{job_id}")
    os.makedirs(job_dir, exist_ok=True)

    job.status = "running"
    job.update_progress(5, "validating_input")
    start_total_time = time.time()

    try:
        # ---------------------------------------------------------
        # STAGE 1: Audio Ingestion / Synthesis
        # ---------------------------------------------------------
        t0 = time.time()
        job.update_progress(15, "preparing_narration_audio")

        raw_audio_path = job.audio_path
        word_timings = []
        speech_segments = []

        if job.input_type == "audio_url":
            audio_url = job.request_params.get("audio_url")
            raw_audio_path = await audio_service.download_audio_from_url(audio_url)
            job.audio_path = raw_audio_path
        elif job.input_type == "script":
            script_text = job.request_params.get("script")
            voice = job.request_params.get("voice")
            dest_audio = os.path.join(job_dir, "narration.mp3")
            tts_res = await tts_service.generate_narration(script_text, voice=voice, output_path=dest_audio)
            raw_audio_path = tts_res["audio_path"]
            job.audio_path = raw_audio_path
            job.narration_text = tts_res.get("spoken_text", script_text)
            word_timings = tts_res.get("word_timings", [])
        elif job.input_type == "scenes":
            scenes_input = job.request_params.get("scenes", [])
            combined_script = " ".join([s["text"] for s in scenes_input])
            voice = job.request_params.get("voice")
            dest_audio = os.path.join(job_dir, "narration.mp3")
            tts_res = await tts_service.generate_narration(combined_script, voice=voice, output_path=dest_audio)
            raw_audio_path = tts_res["audio_path"]
            job.audio_path = raw_audio_path
            job.narration_text = combined_script
            word_timings = tts_res.get("word_timings", [])

        # Validate ingested audio
        audio_meta = audio_service.validate_file_metadata(raw_audio_path)
        total_duration = audio_meta["duration"]
        job.stage_timings["audio_preparation"] = round(time.time() - t0, 3)

        # ---------------------------------------------------------
        # STAGE 2: Speech Transcription (if uploaded/URL audio)
        # ---------------------------------------------------------
        t0 = time.time()
        job.update_progress(30, "transcribing_speech")

        if job.input_type in ("audio_file", "audio_url"):
            # Use Whisper speech recognition
            trans_res = transcription_service.transcribe_audio(raw_audio_path)
            job.narration_text = trans_res["text"]
            speech_segments = trans_res.get("segments", [])
            for seg in speech_segments:
                word_timings.extend(seg.get("words", []))

        job.word_timestamps = word_timings
        job.stage_timings["transcription"] = round(time.time() - t0, 3)

        # ---------------------------------------------------------
        # STAGE 3: Semantic Scene Segmentation
        # ---------------------------------------------------------
        t0 = time.time()
        job.update_progress(45, "segmenting_scenes")

        if job.input_type == "scenes":
            from app.api.schemas.jobs import SceneInput
            parsed_scenes_in = [SceneInput(**s) for s in job.request_params.get("scenes", [])]
            scenes = scene_segmentation_service.segment_from_scene_inputs(
                scene_inputs=parsed_scenes_in,
                total_duration=total_duration,
                word_timings=word_timings
            )
        else:
            scenes = scene_segmentation_service.segment_from_transcription_or_text(
                full_text=job.narration_text,
                total_duration=total_duration,
                segments=speech_segments,
                word_timings=word_timings
            )

        job.scenes = scenes
        job.stage_timings["scene_segmentation"] = round(time.time() - t0, 3)

        # ---------------------------------------------------------
        # STAGE 4: Semantic Footage Retrieval & Provenance
        # ---------------------------------------------------------
        t0 = time.time()
        job.update_progress(60, "retrieving_and_matching_footage")

        await footage_service.select_footage_for_scenes(
            scenes=job.scenes,
            job_dir=job_dir,
            avoid_list=job.request_params.get("avoid", []),
            style=job.request_params.get("style")
        )
        job.stage_timings["footage_retrieval"] = round(time.time() - t0, 3)

        # ---------------------------------------------------------
        # STAGE 5: Captions Generation & Audio Synchronization
        # ---------------------------------------------------------
        t0 = time.time()
        job.update_progress(75, "generating_captions")

        # Priority 4: Detect audio speech boundaries and trailing silence
        speech_sync = audio_service.detect_speech_boundaries(
            file_path=raw_audio_path,
            total_duration=total_duration,
            word_timings=word_timings
        )
        trailing_silence = speech_sync.get("trailing_silence", 0.0)
        if trailing_silence > 0.4:
            logger.info(f"Trailing silence of {trailing_silence}s detected in audio. Synchronizing subtitle boundaries.")

        captions_cfg = job.request_params.get("captions", {"burn_in": True, "srt": True})
        srt_local_path = os.path.join(job_dir, "captions.srt")
        caption_service.generate_srt(job.scenes, srt_local_path, trailing_silence=trailing_silence)
        job.stage_timings["captions"] = round(time.time() - t0, 3)

        # ---------------------------------------------------------
        # STAGE 6: Video Processing & Multi-Aspect Rendering
        # ---------------------------------------------------------
        t0 = time.time()
        job.update_progress(80, "rendering_videos")

        aspect_ratios = job.request_params.get("aspect_ratios", ["16:9"])
        rendered_videos_map = {}

        for ratio in aspect_ratios:
            ratio_tag = ratio.replace(":", "_")
            out_video_local = os.path.join(job_dir, f"video_{ratio_tag}.mp4")

            # Normalise each scene for this aspect ratio
            normalised_scene_paths = []
            for sc in job.scenes:
                scene_clip_path = os.path.join(job_dir, "clips", f"scene_{sc.scene_index}_{ratio_tag}.mp4")
                await rendering_service.render_scene_clip(sc, ratio, scene_clip_path)
                normalised_scene_paths.append(scene_clip_path)

            # Assemble video
            await rendering_service.assemble_video(
                scene_clip_paths=normalised_scene_paths,
                audio_path=raw_audio_path,
                output_video_path=out_video_local,
                srt_path=srt_local_path,
                burn_in_captions=captions_cfg.get("burn_in", True)
            )

            # Save to storage
            storage_url = storage.save_file(f"jobs/{job_id}/video_{ratio_tag}.mp4", out_video_local)
            rendered_videos_map[ratio] = storage_url

        job.output_videos = rendered_videos_map
        job.stage_timings["video_rendering"] = round(time.time() - t0, 3)

        # ---------------------------------------------------------
        # STAGE 7: Timeline & Manifest Artifacts
        # ---------------------------------------------------------
        t0 = time.time()
        job.update_progress(95, "generating_manifest_and_timeline")

        timeline_local = os.path.join(job_dir, "timeline.json")
        manifest_local = os.path.join(job_dir, "manifest.json")

        # Save captions.srt to storage first so its download URL is available for manifest and timeline
        if captions_cfg.get("srt", True) and os.path.exists(srt_local_path):
            job.captions_file = storage.save_file(f"jobs/{job_id}/captions.srt", srt_local_path)

        # Pre-assign storage URLs so manifest and timeline artifacts reference fully populated download links
        job.timeline_file = storage.get_file_url(f"jobs/{job_id}/timeline.json")
        job.manifest_file = storage.get_file_url(f"jobs/{job_id}/manifest.json")

        manifest_service.generate_timeline(job, timeline_local)
        manifest_service.generate_manifest(job, manifest_local)

        # Persist timeline.json and manifest.json with all URLs embedded
        storage.save_file(f"jobs/{job_id}/timeline.json", timeline_local)
        storage.save_file(f"jobs/{job_id}/manifest.json", manifest_local)

        job.stage_timings["artifacts"] = round(time.time() - t0, 3)
        job.stage_timings["total_pipeline_time"] = round(time.time() - start_total_time, 3)

        # ---------------------------------------------------------
        # STAGE 8: Mark Succeeded and Dispatch Webhook
        # ---------------------------------------------------------
        job.status = "succeeded"
        job.update_progress(100, "completed")
        logger.info(f"Job {job_id} successfully completed in {job.stage_timings['total_pipeline_time']}s")

        callback_url = job.request_params.get("callback_url")
        if callback_url:
            await dispatch_callback(
                callback_url=callback_url,
                payload={
                    "job_id": job.job_id,
                    "status": job.status,
                    "progress": 100,
                    "result": {
                        "videos": job.output_videos,
                        "captions": job.captions_file,
                        "timeline": job.timeline_file,
                        "manifest": job.manifest_file,
                    }
                }
            )

    except IncuBrixException as e:
        logger.error(f"Job {job_id} failed with IncuBrixException: [{e.code}] {e.message}")
        job.status = "failed"
        job.update_progress(job.progress, "failed")
        job.error = {
            "code": e.code,
            "message": e.message,
            "retryable": e.retryable,
            "details": e.details
        }
        callback_url = job.request_params.get("callback_url")
        if callback_url:
            await dispatch_callback(callback_url, {"job_id": job.job_id, "status": "failed", "error": job.error})

    except Exception as e:
        logger.exception(f"Job {job_id} failed with unhandled exception: {str(e)}")
        job.status = "failed"
        job.update_progress(job.progress, "failed")
        job.error = {
            "code": "INTERNAL_SERVER_ERROR",
            "message": f"Unexpected execution error: {str(e)}",
            "retryable": True,
            "details": {"error_type": e.__class__.__name__}
        }
        callback_url = job.request_params.get("callback_url")
        if callback_url:
            await dispatch_callback(callback_url, {"job_id": job.job_id, "status": "failed", "error": job.error})


async def worker_loop() -> None:
    """Background worker loop continuously taking jobs from queue."""
    logger.info("Background job worker loop started.")
    queue = get_job_queue()
    while True:
        try:
            job_id = await queue.get()
            await process_job(job_id)
            queue.task_done()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Worker exception: {e}")
            await asyncio.sleep(1)
