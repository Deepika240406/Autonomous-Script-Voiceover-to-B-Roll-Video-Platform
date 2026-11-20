import os
from fastapi import APIRouter, Response, status
from fastapi.responses import FileResponse, JSONResponse
from app.config import settings
from app.utils.ffmpeg import run_command_sync
from app.storage.s3_storage import get_storage


router = APIRouter()


@router.api_route("/health", methods=["GET", "HEAD"], tags=["System"])
def health_check():
    """
    Standard health check endpoint returning 200 OK when service is running.
    Supports both GET and HEAD requests (Render and cloud health probes).
    """
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT
    }


@router.api_route("/ready", methods=["GET", "HEAD"], tags=["System"])
def readiness_check():
    """
    Readiness check verifying FFmpeg binary and storage accessibility.
    """
    # 1. Verify FFmpeg binary
    code, stdout, stderr = run_command_sync([settings.FFMPEG_BINARY, "-version"], timeout=5)
    if code != 0:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready", "reason": "FFmpeg binary unavailable"}
        )

    # 2. Verify storage directory write access
    storage = get_storage()
    try:
        test_file = os.path.join(settings.LOCAL_STORAGE_PATH, ".ready_check")
        with open(test_file, "w") as f:
            f.write("ok")
        if os.path.exists(test_file):
            os.remove(test_file)
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready", "reason": f"Storage path not writable: {e}"}
        )

    return {
        "status": "ready",
        "dependencies": {
            "ffmpeg": "available",
            "storage": "writable",
            "tts": settings.DEFAULT_TTS_PROVIDER,
            "whisper": settings.WHISPER_MODEL_SIZE,
        }
    }


@router.get(f"{settings.API_V1_PREFIX}/storage/{{file_path:path}}", tags=["Storage"])
def serve_storage_file(file_path: str):
    """
    Serves stored output videos, manifests, captions, and timelines.
    """
    storage = get_storage()
    full_local = storage.get_local_path(file_path)
    if not os.path.exists(full_local):
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "FILE_NOT_FOUND", "message": "The requested asset does not exist.", "retryable": False, "details": {}}}
        )
    return FileResponse(full_local)
