import httpx
import os
from typing import List, Dict, Any, Optional
from app.providers.footage.base import BaseFootageProvider, CandidateClip
from app.config import settings
from app.core.logging import logger


class PixabayFootageProvider(BaseFootageProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.PIXABAY_API_KEY
        self.base_url = "https://pixabay.com/api/videos/"

    @property
    def provider_name(self) -> str:
        return "pixabay"

    async def search(self, query: str, min_duration: float = 3.0, count: int = 5) -> List[CandidateClip]:
        key = self.api_key or settings.PIXABAY_API_KEY
        if not key:
            return []

        # Pixabay search prefers 1-4 keywords
        clean_q = " ".join([w for w in query.split() if len(w) > 2][:4])

        params = {
            "key": key,
            "q": clean_q or query,
            "per_page": count * 2,
            "video_type": "film",
        }

        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(self.base_url, params=params)
                if resp.status_code != 200:
                    logger.warning(f"Pixabay API error HTTP {resp.status_code}: {resp.text}")
                    return []

                data = resp.json()
                hits = data.get("hits", [])
                candidates: List[CandidateClip] = []

                for h in hits:
                    duration = float(h.get("duration", 0))
                    if duration < min_duration:
                        continue

                    videos = h.get("videos", {})
                    # Prefer medium or large
                    stream_info = videos.get("large") or videos.get("medium") or videos.get("small")
                    if not stream_info or not stream_info.get("url"):
                        continue

                    user = h.get("user", "Pixabay Creator")
                    candidates.append(CandidateClip(
                        clip_id=f"pixabay_{h.get('id')}",
                        provider=self.provider_name,
                        title=h.get("tags", f"Stock video matching {query}"),
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

                return candidates
        except Exception as e:
            logger.error(f"Pixabay search exception: {e}")
            return []

    async def download_clip(self, clip: CandidateClip, dest_path: str) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
        async with httpx.AsyncClient(timeout=45.0, follow_redirects=True) as client:
            async with client.stream("GET", clip.download_url) as resp:
                if resp.status_code != 200:
                    raise RuntimeError(f"Pixabay download failed: HTTP {resp.status_code}")
                with open(dest_path, "wb") as f:
                    async for chunk in resp.aiter_bytes(chunk_size=65536):
                        f.write(chunk)
        return dest_path
