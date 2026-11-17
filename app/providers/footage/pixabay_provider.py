import httpx
import os
import subprocess
import asyncio
from typing import List, Dict, Any, Optional
from app.providers.footage.base import BaseFootageProvider, CandidateClip
from app.config import settings
from app.core.logging import logger
from app.utils.ffmpeg import run_command_sync


class PixabayFootageProvider(BaseFootageProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.PIXABAY_API_KEY
        self.video_url = "https://pixabay.com/api/videos/"
        self.photo_url = "https://pixabay.com/api/"

    @property
    def provider_name(self) -> str:
        return "pixabay"

    async def search(self, query: str, min_duration: float = 3.0, count: int = 20) -> List[CandidateClip]:
        key = self.api_key or settings.PIXABAY_API_KEY
        if not key:
            return []

        # Keep search query focused and descriptive
        words = [w for w in query.split() if len(w) > 2]
        clean_q = " ".join(words[:4]) if words else query

        candidates: List[CandidateClip] = []

        try:
            async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
                # 1. Fetch 15-20 Candidate Videos from Pixabay
                target_fetch = max(20, count)
                video_params = {
                    "key": key,
                    "q": clean_q,
                    "per_page": target_fetch,
                    "video_type": "film",
                }
                v_resp = await client.get(self.video_url, params=video_params)
                if v_resp.status_code == 200:
                    hits = v_resp.json().get("hits", [])
                    for h in hits:
                        duration = float(h.get("duration", 0))
                        if duration < 2.0:
                            continue

                        videos = h.get("videos", {})
                        stream_info = videos.get("large") or videos.get("medium") or videos.get("small")
                        if not stream_info or not stream_info.get("url"):
                            continue

                        user = h.get("user", "Pixabay Creator")
                        candidates.append(CandidateClip(
                            clip_id=f"pixabay_{h.get('id')}",
                            provider=self.provider_name,
                            title=h.get("tags", f"Stock video matching {clean_q}"),
                            description=f"Pixabay footage: {h.get('tags')}",
                            tags=[t.strip() for t in h.get("tags", "").split(",")],
                            download_url=stream_info.get("url"),
                            duration=duration,
                            width=int(stream_info.get("width") or 1920),
                            height=int(stream_info.get("height") or 1080),
                            fps=30.0,
                            licence_name="Pixabay Content License (Free Commercial Use Allowed)",
                            licence_url="https://pixabay.com/service/license-summary/",
                            attribution=f"Video by {user} from Pixabay ({h.get('pageURL')})",
                            is_ai_generated=False,
                        ))
                        if len(candidates) >= count:
                            break

                # 2. If candidates are fewer than 10, supplement with high-res Photos
                if len(candidates) < 10:
                    photo_params = {
                        "key": key,
                        "q": clean_q,
                        "image_type": "photo",
                        "orientation": "horizontal",
                        "per_page": target_fetch,
                    }
                    p_resp = await client.get(self.photo_url, params=photo_params)
                    if p_resp.status_code == 200:
                        photo_hits = p_resp.json().get("hits", [])
                        for ph in photo_hits:
                            img_url = ph.get("largeImageURL") or ph.get("webformatURL")
                            if not img_url:
                                continue

                            user = ph.get("user", "Pixabay Creator")
                            candidates.append(CandidateClip(
                                clip_id=f"pixabay_photo_{ph.get('id')}",
                                provider=self.provider_name,
                                title=ph.get("tags", f"High-resolution stock photo matching {clean_q}"),
                                description=f"Pixabay visual: {ph.get('tags')}",
                                tags=[t.strip() for t in ph.get("tags", "").split(",")],
                                download_url=img_url,
                                duration=max(min_duration, 10.0),
                                width=int(ph.get("imageWidth") or 1920),
                                height=int(ph.get("imageHeight") or 1080),
                                fps=30.0,
                                licence_name="Pixabay Content License (Free Commercial Use Allowed)",
                                licence_url="https://pixabay.com/service/license-summary/",
                                attribution=f"Photo by {user} from Pixabay ({ph.get('pageURL')})",
                                is_ai_generated=False,
                            ))
                            if len(candidates) >= count:
                                break

        except Exception as e:
            logger.error(f"Pixabay search exception: {e}")

        logger.info(f"Pixabay retrieved {len(candidates)} candidate clips for query '{clean_q}'")
        return candidates

    async def download_clip(self, clip: CandidateClip, dest_path: str) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)

        is_photo = clip.clip_id.startswith("pixabay_photo_") or any(clip.download_url.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png"])

        if is_photo:
            temp_img = dest_path + ".temp.jpg"
            async with httpx.AsyncClient(timeout=45.0, follow_redirects=True) as client:
                async with client.stream("GET", clip.download_url) as resp:
                    if resp.status_code != 200:
                        raise RuntimeError(f"Pixabay photo download failed: HTTP {resp.status_code}")
                    with open(temp_img, "wb") as f:
                        async for chunk in resp.aiter_bytes(chunk_size=65536):
                            f.write(chunk)

            dur = max(float(clip.duration), 8.0)
            frames = int(dur * 30)
            cmd = [
                settings.FFMPEG_BINARY, "-y",
                "-loop", "1",
                "-i", temp_img,
                "-t", str(dur),
                "-vf", f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,zoompan=z='min(zoom+0.001,1.15)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080,format=yuv420p",
                "-c:v", "libx264",
                "-preset", "faster",
                "-r", "30",
                "-pix_fmt", "yuv420p",
                dest_path
            ]
            code, stdout, stderr = await asyncio.to_thread(run_command_sync, cmd, timeout=90)
            if os.path.exists(temp_img):
                try:
                    os.remove(temp_img)
                except OSError:
                    pass

            if code != 0 or not os.path.exists(dest_path):
                raise RuntimeError(f"Failed converting stock photo to B-roll video: {stderr}")

            return dest_path

        # Standard video download
        async with httpx.AsyncClient(timeout=45.0, follow_redirects=True) as client:
            async with client.stream("GET", clip.download_url) as resp:
                if resp.status_code != 200:
                    raise RuntimeError(f"Pixabay download failed: HTTP {resp.status_code}")
                with open(dest_path, "wb") as f:
                    async for chunk in resp.aiter_bytes(chunk_size=65536):
                        f.write(chunk)
        return dest_path
