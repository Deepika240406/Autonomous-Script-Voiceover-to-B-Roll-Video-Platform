import httpx
import os
from typing import List, Dict, Any, Optional
from app.providers.footage.base import BaseFootageProvider, CandidateClip
from app.config import settings
from app.core.logging import logger


class PexelsFootageProvider(BaseFootageProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.PEXELS_API_KEY
        self.base_url = "https://api.pexels.com/videos"

    @property
    def provider_name(self) -> str:
        return "pexels"

    async def search(self, query: str, min_duration: float = 3.0, count: int = 5) -> List[CandidateClip]:
        if not self.api_key:
            return []

        headers = {"Authorization": self.api_key}
        params = {
            "query": query,
            "per_page": count * 2,
            "orientation": "landscape",
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self.base_url}/search", params=params, headers=headers)
                if resp.status_code != 200:
                    logger.warning(f"Pexels API error HTTP {resp.status_code}: {resp.text}")
                    return []

                data = resp.json()
                videos = data.get("videos", [])
                candidates: List[CandidateClip] = []

                for v in videos:
                    duration = float(v.get("duration", 0))
                    if duration < min_duration:
                        continue

                    # Find best HD video file
                    v_files = v.get("video_files", [])
                    hd_files = [f for f in v_files if f.get("quality") == "hd" and f.get("link")]
                    best_file = hd_files[0] if hd_files else (v_files[0] if v_files else None)
                    if not best_file:
                        continue

                    user_info = v.get("user", {})
                    author = user_info.get("name", "Pexels Creator")

                    candidates.append(CandidateClip(
                        clip_id=f"pexels_{v.get('id')}",
                        provider=self.provider_name,
                        title=f"Stock video by {author} on Pexels",
                        description=f"Pexels footage matching '{query}'",
                        tags=query.split(),
                        download_url=best_file.get("link"),
                        duration=duration,
                        width=int(best_file.get("width") or 1920),
                        height=int(best_file.get("height") or 1080),
                        fps=float(best_file.get("fps") or 30.0),
                        licence_name="Pexels Licence (Free Commercial Use Allowed)",
                        licence_url="https://www.pexels.com/license/",
                        attribution=f"Video by {author} from Pexels ({v.get('url')})",
                        is_ai_generated=False,
                        preview_url=v.get("image")
                    ))
                    if len(candidates) >= count:
                        break

                return candidates
        except Exception as e:
            logger.error(f"Pexels search exception: {e}")
            return []

    async def download_clip(self, clip: CandidateClip, dest_path: str) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
        async with httpx.AsyncClient(timeout=45.0, follow_redirects=True) as client:
            async with client.stream("GET", clip.download_url) as resp:
                if resp.status_code != 200:
                    raise RuntimeError(f"Pexels download failed: HTTP {resp.status_code}")
                with open(dest_path, "wb") as f:
                    async for chunk in resp.aiter_bytes(chunk_size=65536):
                        f.write(chunk)
        return dest_path
