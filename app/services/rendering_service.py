import os
import subprocess
import asyncio
from typing import List, Dict, Any, Optional
from app.models.job import SceneData
from app.config import settings
from app.core.exceptions import RenderingException
from app.utils.ffmpeg import inspect_audio, probe_media_file, run_command_sync
from app.core.logging import logger


ASPECT_RATIO_CONFIGS = {
    "16:9": {
        "width": 1920,
        "height": 1080,
        "filter": "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,eq=contrast=1.03:brightness=0.01:saturation=1.05,format=yuv420p"
    },
    "9:16": {
        "width": 1080,
        "height": 1920,
        # Intelligent blurred background composite preserving edge subjects without cropping or distortion
        "complex_filter": "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:5[bg];[0:v]scale=1080:1920:force_original_aspect_ratio=decrease[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,eq=contrast=1.03:brightness=0.01:saturation=1.05,format=yuv420p"
    },
    "1:1": {
        "width": 1080,
        "height": 1080,
        "complex_filter": "[0:v]scale=1080:1080:force_original_aspect_ratio=increase,crop=1080:1080,boxblur=25:5[bg];[0:v]scale=1080:1080:force_original_aspect_ratio=decrease[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,eq=contrast=1.03:brightness=0.01:saturation=1.05,format=yuv420p"
    }
}


class VideoRenderingService:
    def __init__(self):
        pass

    async def render_scene_clip(
        self,
        scene: SceneData,
        aspect_ratio: str,
        output_clip_path: str
    ) -> str:
        """
        Normalises an individual scene clip:
        - Exact duration trimming and loop extension if clip shorter than scene
        - Conforms resolution, aspect ratio (with 9:16 smart composite)
        - 30 fps, yuv420p pixel format, colour/brightness balance
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_clip_path)), exist_ok=True)
        raw_clip = scene.selected_clip.local_path
        target_duration = max(0.5, scene.duration)

        config = ASPECT_RATIO_CONFIGS.get(aspect_ratio, ASPECT_RATIO_CONFIGS["16:9"])

        cmd = [
            settings.FFMPEG_BINARY, "-y",
            "-stream_loop", "-1",  # loop if clip is shorter than scene duration
            "-i", raw_clip,
            "-t", str(target_duration),
        ]

        if "complex_filter" in config:
            cmd.extend(["-filter_complex", config["complex_filter"]])
        else:
            cmd.extend(["-vf", config["filter"]])

        cmd.extend([
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-threads", "1",
            "-crf", "22",
            "-r", "30",
            "-an",  # strip internal clip audio; narration audio is overlaid in final assembly
            output_clip_path
        ])

        code, stdout, stderr = await asyncio.to_thread(run_command_sync, cmd, timeout=120)
        if code != 0:
            logger.error(f"FFmpeg failed rendering scene clip: {stderr}")
            raise RenderingException(f"Failed to normalise scene {scene.scene_index} for {aspect_ratio}: {stderr}")

        return output_clip_path

    async def assemble_video(
        self,
        scene_clip_paths: List[str],
        audio_path: str,
        output_video_path: str,
        srt_path: Optional[str] = None,
        burn_in_captions: bool = False
    ) -> str:
        """
        Concatenates normalised scene video clips, synchronises narration audio,
        burns in captions if requested, and outputs final production MP4.
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_video_path)), exist_ok=True)

        # Create concat manifest file
        manifest_path = output_video_path + ".concat.txt"
        with open(manifest_path, "w", encoding="utf-8") as f:
            for clip in scene_clip_paths:
                clean_path = os.path.abspath(clip).replace("\\", "/")
                f.write(f"file '{clean_path}'\n")

        cmd = [
            settings.FFMPEG_BINARY, "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", manifest_path,
            "-i", audio_path,
        ]

        # Apply subtitle burn-in if enabled
        if burn_in_captions and srt_path and os.path.exists(srt_path):
            escaped_srt = os.path.abspath(srt_path).replace("\\", "/").replace(":", "\\:")
            # Use style with semi-transparent background box for readability
            sub_filter = (
                f"subtitles='{escaped_srt}':force_style="
                "'FontSize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=3,MarginV=35'"
            )
            cmd.extend(["-vf", sub_filter])

        cmd.extend([
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-threads", "1",
            "-crf", "20",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "44100",
            "-shortest",  # Ensure video terminates cleanly with audio
            "-pix_fmt", "yuv420p",
            output_video_path
        ])

        code, stdout, stderr = await asyncio.to_thread(run_command_sync, cmd, timeout=180)

        # Cleanup concat txt
        if os.path.exists(manifest_path):
            os.remove(manifest_path)

        if code != 0:
            # If subtitles filter failed on Windows fontconfig, retry without subtitles filter to guarantee delivery
            if burn_in_captions and "subtitles" in stderr:
                logger.warning("Subtitles filter failed (fontconfig issue). Retrying video assembly without burn-in.")
                return await self.assemble_video(scene_clip_paths, audio_path, output_video_path, burn_in_captions=False)
            logger.error(f"FFmpeg assembly failed: {stderr}")
            raise RenderingException(f"Failed to assemble final video: {stderr}")

        # Verification check: inspect output video
        probe_info = probe_media_file(output_video_path)
        logger.info(f"Video assembled successfully: {output_video_path} (size: {os.path.getsize(output_video_path)} bytes)")
        return output_video_path


rendering_service = VideoRenderingService()
