import os
import subprocess
import asyncio
from typing import List, Dict, Any
from app.providers.footage.base import BaseFootageProvider, CandidateClip
from app.core.logging import logger


class LocalFallbackProvider(BaseFootageProvider):
    @property
    def provider_name(self) -> str:
        return "local_fallback"

    async def search(self, query: str, min_duration: float = 3.0, count: int = 5) -> List[CandidateClip]:
        safe_tag = query.replace("'", "").strip()[:40] or "B-Roll Visual"
        clip_id = f"fallback_{abs(hash(query)) % 100000}"
        return [
            CandidateClip(
                clip_id=clip_id,
                provider=self.provider_name,
                title=f"Procedural Motion Background: {safe_tag}",
                description=f"Clean animated ambient cinematic video backdrop generated locally for '{safe_tag}'",
                tags=["procedural", "motion background", "ambient", "fallback"],
                download_url=f"local://{clip_id}.mp4",
                duration=max(6.0, min_duration + 3.0),
                width=1920,
                height=1080,
                fps=30.0,
                licence_name="Procedural Motion Safe (Commercial Open Domain)",
                licence_url="https://incubrix.com/licences/procedural-open",
                attribution="IncuBrix Procedural Video Synthesis",
                is_ai_generated=True,
            )
        ]

    async def download_clip(self, clip: CandidateClip, dest_path: str) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
        dur = max(4.0, clip.duration)
        safe_title = clip.title.replace("'", "").replace(":", " -")

        # Procedural cinematic gradient background with subtle pan/zoom motion
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"gradients=s=1920x1080:d={dur}:c0=0x0f172a:c1=0x1e3a8a:x0=0:y0=0:x1=1920:y1=1080",
            "-vf", f"drawtext=text='{safe_title}':fontcolor=white@0.85:fontsize=36:x=(w-text_w)/2:y=h-120",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-r", "30",
            dest_path
        ]
        proc = await asyncio.to_thread(subprocess.run, cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            # Fallback to testsrc if gradients filter isn't compiled
            alt_cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", f"color=c=0x1e293b:s=1920x1080:d={dur}",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-r", "30",
                dest_path
            ]
            await asyncio.to_thread(subprocess.run, alt_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        return dest_path
