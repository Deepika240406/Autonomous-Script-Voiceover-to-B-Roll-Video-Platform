import os
import uuid
import json
import time
from typing import Optional, List
from fastapi import APIRouter, Header, Request, UploadFile, File, Form, status
from fastapi.responses import JSONResponse
from app.api.schemas.jobs import (
    BrollJobCreateRequest,
    BrollJobCreateResponse,
    BrollJobStatusResponse,
    JobResultFiles,
    ClipReplacementRequest,
)
from app.models.job import JobRecord, SceneData, ClipMetadata
from app.workers.queue import job_repo, get_job_queue
from app.core.idempotency import idempotency_store
from app.core.security import is_safe_url
from app.core.exceptions import InvalidInputException, NotFoundException
from app.core.logging import logger, correlation_id_ctx
from app.services.audio_service import audio_service
from app.services.footage_service import footage_service
from app.services.rendering_service import rendering_service
from app.services.manifest_service import manifest_service
from app.storage.s3_storage import get_storage
from app.config import settings


router = APIRouter(prefix="/jobs", tags=["B-Roll Jobs"])


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=BrollJobCreateResponse,
    summary="Submit B-roll video generation job"
)
async def create_broll_job(
    request: Request,
    body: Optional[BrollJobCreateRequest] = None,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """
    Submits an asynchronous B-roll video creation job from script, scenes, or audio URL.
    Returns HTTP 202 with job_id and status URL.
    Safe retries supported via Idempotency-Key.
    """
    # 1. Check Idempotency-Key
    if idempotency_key:
        cached = idempotency_store.get(idempotency_key)
        if cached:
            logger.info(f"Idempotent hit for key: {idempotency_key} -> returning job {cached['job_id']}")
            return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content=cached["response"])

    if not body:
        raise InvalidInputException("Missing request body payload.")

    # 2. Validate URL if audio_url supplied
    if body.audio_url:
        is_safe_url(body.audio_url, allow_local_for_dev=settings.DEBUG or settings.ENVIRONMENT == "development")

    job_id = str(uuid.uuid4())
    input_type = "audio_url" if body.audio_url else ("scenes" if body.scenes else "script")

    job = JobRecord(
        job_id=job_id,
        status="queued",
        progress=0,
        stage="queued",
        input_type=input_type,
        request_params=body.model_dump(),
    )
    job_repo.save(job)

    # 3. Queue job
    await get_job_queue().put(job_id)

    status_url = f"{settings.API_V1_PREFIX}/jobs/{job_id}"
    response_data = {
        "job_id": job_id,
        "status": "queued",
        "progress": 0,
        "status_url": status_url
    }

    if idempotency_key:
        req_hash = idempotency_store.compute_hash(body.model_dump())
        idempotency_store.set(idempotency_key, job_id, req_hash, response_data)

    return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content=response_data)


@router.post(
    "/upload",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=BrollJobCreateResponse,
    summary="Submit B-roll job with audio file upload"
)
async def create_broll_job_with_upload(
    request: Request,
    audio_file: UploadFile = File(...),
    voice: Optional[str] = Form("en-IN-female"),
    aspect_ratios: Optional[str] = Form('["16:9"]'),
    style: Optional[str] = Form("bright, modern, real-world footage"),
    avoid: Optional[str] = Form('[]'),
    captions_burn_in: Optional[bool] = Form(True),
    captions_srt: Optional[bool] = Form(True),
    callback_url: Optional[str] = Form(None),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """
    Submits an asynchronous B-roll job with multipart voiceover audio file upload.
    """
    if idempotency_key:
        cached = idempotency_store.get(idempotency_key)
        if cached:
            return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content=cached["response"])

    job_id = str(uuid.uuid4())
    job_dir = os.path.abspath(f"./storage_root/jobs/{job_id}")
    os.makedirs(job_dir, exist_ok=True)

    filename = audio_file.filename or "upload.mp3"
    saved_path = os.path.join(job_dir, filename)

    content = await audio_file.read()
    if len(content) == 0:
        raise InvalidInputException("Uploaded audio file is empty.")

    with open(saved_path, "wb") as f:
        f.write(content)

    # Validate audio immediately
    audio_service.validate_file_metadata(saved_path, filename=filename)

    # Parse ratios and avoids
    try:
        ratios_parsed = json.loads(aspect_ratios) if aspect_ratios.startswith("[") else [r.strip() for r in aspect_ratios.split(",")]
    except Exception:
        ratios_parsed = ["16:9"]

    try:
        avoid_parsed = json.loads(avoid) if avoid.startswith("[") else [a.strip() for a in avoid.split(",") if a.strip()]
    except Exception:
        avoid_parsed = []

    request_params = {
        "audio_url": None,
        "script": None,
        "scenes": None,
        "voice": voice,
        "aspect_ratios": ratios_parsed,
        "style": style,
        "avoid": avoid_parsed,
        "captions": {"burn_in": captions_burn_in, "srt": captions_srt},
        "callback_url": callback_url,
    }

    job = JobRecord(
        job_id=job_id,
        status="queued",
        progress=0,
        stage="queued",
        input_type="audio_file",
        audio_path=saved_path,
        request_params=request_params,
    )
    job_repo.save(job)
    await get_job_queue().put(job_id)

    status_url = f"{settings.API_V1_PREFIX}/jobs/{job_id}"
    response_data = {
        "job_id": job_id,
        "status": "queued",
        "progress": 0,
        "status_url": status_url
    }

    if idempotency_key:
        idempotency_store.set(idempotency_key, job_id, str(len(content)), response_data)

    return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content=response_data)


@router.get(
    "/{job_id}",
    response_model=BrollJobStatusResponse,
    summary="Get job execution status and result links"
)
def get_job_status(job_id: str):
    job = job_repo.get(job_id)
    if not job:
        raise NotFoundException(f"Job with ID '{job_id}' not found.")

    res_files = None
    if job.status == "succeeded":
        res_files = JobResultFiles(
            videos=job.output_videos,
            captions=job.captions_file,
            timeline=job.timeline_file,
            manifest=job.manifest_file,
        )

    return {
        "job_id": job.job_id,
        "status": job.status,
        "progress": job.progress,
        "stage": job.stage,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "result": res_files,
        "error": job.error,
    }


@router.post(
    "/{job_id}/scenes/{scene_index}/replace",
    summary="Advanced: Swap clip for an individual scene and perform rapid re-render"
)
async def replace_scene_clip(
    job_id: str,
    scene_index: int,
    body: ClipReplacementRequest
):
    """
    Advanced feature: Replaces the footage of a specific scene, re-rendering only
    the affected scene clip and reassembling the video in a fraction of full-render time.
    """
    job = job_repo.get(job_id)
    if not job:
        raise NotFoundException(f"Job with ID '{job_id}' not found.")
    if job.status != "succeeded":
        raise InvalidInputException("Can only replace clips on successfully completed jobs.")
    if scene_index < 0 or scene_index >= len(job.scenes):
        raise InvalidInputException(f"Invalid scene_index {scene_index}. Job has {len(job.scenes)} scenes.")

    scene = job.scenes[scene_index]
    job_dir = os.path.abspath(f"./storage_root/jobs/{job_id}")
    storage = get_storage()

    t_swap_start = time.time()
    search_q = body.search_query or body.visual_hint or f"replacement for {scene.narration_text}"
    logger.info(f"Swapping clip for Scene {scene_index} in Job {job_id} with query: '{search_q}'")

    # Retrieve replacement clip
    providers = footage_service.get_providers_pipeline(body.source_provider)
    chosen_cand = None
    for prov in providers:
        try:
            results = await prov.search(search_q, min_duration=scene.duration, count=2)
            if results:
                chosen_cand = results[0]
                break
        except Exception:
            continue

    if not chosen_cand:
        # Fallback to local procedural
        cands = await footage_service.fallback_provider.search(search_q, min_duration=scene.duration)
        chosen_cand = cands[0]

    dest_path = os.path.join(job_dir, "footage", f"scene_{scene_index}_replaced_{chosen_cand.clip_id}.mp4")
    # Download replacement clip
    prov_inst = next((p for p in providers if p.provider_name == chosen_cand.provider), footage_service.fallback_provider)
    await prov_inst.download_clip(chosen_cand, dest_path)

    # Update scene selected clip
    scene.selected_clip = ClipMetadata(
        clip_id=chosen_cand.clip_id,
        provider=chosen_cand.provider,
        source_url=chosen_cand.download_url,
        local_path=dest_path,
        duration=chosen_cand.duration,
        width=chosen_cand.width,
        height=chosen_cand.height,
        fps=chosen_cand.fps,
        licence_name=chosen_cand.licence_name,
        licence_url=chosen_cand.licence_url,
        attribution=chosen_cand.attribution,
        is_ai_generated=chosen_cand.is_ai_generated,
        selection_reason=f"Manually replaced clip using query '{search_q}' from {chosen_cand.provider}",
        relevance_score=4.8,
        search_query=search_q,
        warnings=list(scene.warnings) + [f"Scene {scene_index} clip replaced by user request."],
    )

    # Re-render ONLY this scene's normalized clip for each aspect ratio
    aspect_ratios = job.request_params.get("aspect_ratios", ["16:9"])
    for ratio in aspect_ratios:
        ratio_tag = ratio.replace(":", "_")
        scene_clip_path = os.path.join(job_dir, "clips", f"scene_{scene_index}_{ratio_tag}.mp4")
        await rendering_service.render_scene_clip(scene, ratio, scene_clip_path)

        # Fast re-assembly using existing clips
        all_scene_paths = [
            os.path.join(job_dir, "clips", f"scene_{sc.scene_index}_{ratio_tag}.mp4")
            for sc in job.scenes
        ]
        out_video_local = os.path.join(job_dir, f"video_{ratio_tag}.mp4")
        srt_local = os.path.join(job_dir, "captions.srt")
        captions_cfg = job.request_params.get("captions", {"burn_in": True})

        await rendering_service.assemble_video(
            scene_clip_paths=all_scene_paths,
            audio_path=job.audio_path,
            output_video_path=out_video_local,
            srt_path=srt_local,
            burn_in_captions=captions_cfg.get("burn_in", True)
        )
        storage.save_file(f"jobs/{job_id}/video_{ratio_tag}.mp4", out_video_local)

    # Update manifest & timeline
    manifest_service.generate_timeline(job, os.path.join(job_dir, "timeline.json"))
    manifest_service.generate_manifest(job, os.path.join(job_dir, "manifest.json"))

    swap_duration = round(time.time() - t_swap_start, 3)
    logger.info(f"Scene {scene_index} replaced in {swap_duration}s (rapid re-render).")

    return {
        "status": "succeeded",
        "message": f"Scene {scene_index} replaced and re-rendered successfully in {swap_duration}s.",
        "swap_duration_seconds": swap_duration,
        "job_id": job_id,
        "timeline_url": job.timeline_file,
    }
