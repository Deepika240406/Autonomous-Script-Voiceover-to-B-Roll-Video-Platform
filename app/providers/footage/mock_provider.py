import os
import subprocess
import asyncio
from typing import List, Dict, Any, Optional
from app.providers.footage.base import BaseFootageProvider, CandidateClip
from app.core.logging import logger


SAMPLE_FOOTAGE_LIBRARY = [
    {
        "clip_id": "mock_tech_01",
        "title": "Cloud data center server racks glowing blue",
        "description": "High-tech cloud computing infrastructure servers and networking cables data transmission",
        "tags": ["cloud computing", "server", "data center", "technology", "network", "cybersecurity"],
        "download_url": "mock://sample_tech_01.mp4",
        "duration": 12.0,
        "width": 1920,
        "height": 1080,
        "fps": 30.0,
        "licence_name": "IncuBrix Verified Commercial Mock Licence",
        "licence_url": "https://incubrix.com/licences/commercial-use",
        "attribution": "IncuBrix Creative Studios (Mock Collection)",
        "color_spec": "color=c=0x0a192f:s=1920x1080:d=12",
        "is_ai_generated": False,
    },
    {
        "clip_id": "mock_finance_01",
        "title": "Stock market charts and financial statistics growth",
        "description": "Business analytics dashboard with graphs indicating 40% sales growth and revenue expansion",
        "tags": ["business analytics", "finance", "bank", "stock chart", "growth", "statistics", "sales"],
        "download_url": "mock://sample_finance_01.mp4",
        "duration": 10.0,
        "width": 1920,
        "height": 1080,
        "fps": 30.0,
        "licence_name": "IncuBrix Verified Commercial Mock Licence",
        "licence_url": "https://incubrix.com/licences/commercial-use",
        "attribution": "IncuBrix Creative Studios (Mock Collection)",
        "color_spec": "color=c=0x112240:s=1920x1080:d=10",
        "is_ai_generated": False,
    },
    {
        "clip_id": "mock_trust_01",
        "title": "Professional business partnership handshake in bright office",
        "description": "Two corporate partners shaking hands earning trust and closing agreement slowly",
        "tags": ["trust", "handshake", "business partnership", "office", "collaboration", "agreement"],
        "download_url": "mock://sample_trust_01.mp4",
        "duration": 10.0,
        "width": 1920,
        "height": 1080,
        "fps": 30.0,
        "licence_name": "IncuBrix Verified Commercial Mock Licence",
        "licence_url": "https://incubrix.com/licences/commercial-use",
        "attribution": "IncuBrix Creative Studios (Mock Collection)",
        "color_spec": "color=c=0x233554:s=1920x1080:d=10",
        "is_ai_generated": False,
    },
    {
        "clip_id": "mock_python_code_01",
        "title": "Programmer coding python software syntax on laptop",
        "description": "Software engineer developer writing python code algorithms in modern IDE terminal",
        "tags": ["python", "code", "programming", "software developer", "computer science", "script"],
        "download_url": "mock://sample_python_01.mp4",
        "duration": 10.0,
        "width": 1920,
        "height": 1080,
        "fps": 30.0,
        "licence_name": "IncuBrix Verified Commercial Mock Licence",
        "licence_url": "https://incubrix.com/licences/commercial-use",
        "attribution": "IncuBrix Creative Studios (Mock Collection)",
        "color_spec": "color=c=0x1f2937:s=1920x1080:d=10",
        "is_ai_generated": False,
    },
    {
        "clip_id": "mock_nature_river_01",
        "title": "Peaceful river bank with flowing water in sunlight",
        "description": "Scenic outdoor river bank fresh stream flowing near green nature landscape",
        "tags": ["river", "riverbank", "bank", "stream", "nature", "water", "landscape"],
        "download_url": "mock://sample_nature_01.mp4",
        "duration": 12.0,
        "width": 1920,
        "height": 1080,
        "fps": 30.0,
        "licence_name": "IncuBrix Verified Commercial Mock Licence",
        "licence_url": "https://incubrix.com/licences/commercial-use",
        "attribution": "IncuBrix Creative Studios (Mock Collection)",
        "color_spec": "color=c=0x1b4332:s=1920x1080:d=12",
        "is_ai_generated": False,
    },
    {
        "clip_id": "mock_nature_clouds_01",
        "title": "Dramatic white cumulus clouds in bright blue sky",
        "description": "Time lapse of beautiful white clouds floating over bright sunny weather sky",
        "tags": ["sky", "clouds", "cumulus", "weather", "atmosphere", "blue sky"],
        "download_url": "mock://sample_clouds_01.mp4",
        "duration": 12.0,
        "width": 1920,
        "height": 1080,
        "fps": 30.0,
        "licence_name": "IncuBrix Verified Commercial Mock Licence",
        "licence_url": "https://incubrix.com/licences/commercial-use",
        "attribution": "IncuBrix Creative Studios (Mock Collection)",
        "color_spec": "color=c=0x2b6cb0:s=1920x1080:d=12",
        "is_ai_generated": False,
    },
    {
        "clip_id": "mock_patience_mountain_01",
        "title": "Climber standing near mountain peak summit with patience",
        "description": "Endurance and patience required for success as mountaineer reaches high ridge",
        "tags": ["patience", "success", "mountain", "climber", "endurance", "perseverance"],
        "download_url": "mock://sample_patience_01.mp4",
        "duration": 10.0,
        "width": 1920,
        "height": 1080,
        "fps": 30.0,
        "licence_name": "IncuBrix Verified Commercial Mock Licence",
        "licence_url": "https://incubrix.com/licences/commercial-use",
        "attribution": "IncuBrix Creative Studios (Mock Collection)",
        "color_spec": "color=c=0x4a5568:s=1920x1080:d=10",
        "is_ai_generated": False,
    },
    {
        "clip_id": "mock_memorial_dawn_01",
        "title": "Quiet peaceful dawn sunrise landscape for memorial",
        "description": "Respectful somber dawn light reflecting over calm water memorial tribute",
        "tags": ["memorial", "peaceful", "sensitive", "dawn", "somber", "reflection", "tribute"],
        "download_url": "mock://sample_memorial_01.mp4",
        "duration": 10.0,
        "width": 1920,
        "height": 1080,
        "fps": 30.0,
        "licence_name": "IncuBrix Verified Commercial Mock Licence",
        "licence_url": "https://incubrix.com/licences/commercial-use",
        "attribution": "IncuBrix Creative Studios (Mock Collection)",
        "color_spec": "color=c=0x374151:s=1920x1080:d=10",
        "is_ai_generated": False,
    },
    {
        "clip_id": "mock_executive_speech_01",
        "title": "Tech executive speaking on conference stage",
        "description": "Keynote speaker technology leader presenting on illuminated conference stage",
        "tags": ["executive", "keynote", "technology leader", "conference", "presentation", "visionary"],
        "download_url": "mock://sample_executive_01.mp4",
        "duration": 10.0,
        "width": 1920,
        "height": 1080,
        "fps": 30.0,
        "licence_name": "IncuBrix Verified Commercial Mock Licence",
        "licence_url": "https://incubrix.com/licences/commercial-use",
        "attribution": "IncuBrix Creative Studios (Mock Collection)",
        "color_spec": "color=c=0x1e3a8a:s=1920x1080:d=10",
        "is_ai_generated": False,
    },
    {
        "clip_id": "mock_generative_01",
        "title": "AI-generated abstract digital particle flow",
        "description": "Luminescent neural network particle simulation representing future artificial intelligence",
        "tags": ["ai", "generative", "neural network", "digital art", "particles", "innovation"],
        "download_url": "mock://sample_gen_01.mp4",
        "duration": 10.0,
        "width": 1920,
        "height": 1080,
        "fps": 30.0,
        "licence_name": "IncuBrix AI Commercial Open Licence",
        "licence_url": "https://incubrix.com/licences/ai-commercial",
        "attribution": "IncuBrix Generative Synthesis Engine",
        "color_spec": "color=c=0x581c87:s=1920x1080:d=10",
        "is_ai_generated": True,
    }
]


class MockFootageProvider(BaseFootageProvider):
    def __init__(self, cache_dir: str = "./assets/sample_footage"):
        self.cache_dir = os.path.abspath(cache_dir)
        os.makedirs(self.cache_dir, exist_ok=True)

    @property
    def provider_name(self) -> str:
        return "mock_provider"

    async def search(self, query: str, min_duration: float = 3.0, count: int = 5) -> List[CandidateClip]:
        query_words = set(query.lower().split())
        scored: List[tuple] = []

        for item in SAMPLE_FOOTAGE_LIBRARY:
            match_score = 0
            all_text = f"{item['title']} {item['description']} {' '.join(item['tags'])}".lower()
            for qw in query_words:
                if qw in all_text:
                    match_score += 2
            for tag in item["tags"]:
                if tag in query.lower():
                    match_score += 3
            scored.append((match_score, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = [item for _, item in scored[:count]]

        candidates = []
        for item in top:
            candidates.append(CandidateClip(
                clip_id=item["clip_id"],
                provider=self.provider_name,
                title=item["title"],
                description=item["description"],
                tags=item["tags"],
                download_url=item["download_url"],
                duration=item["duration"],
                width=item["width"],
                height=item["height"],
                fps=item["fps"],
                licence_name=item["licence_name"],
                licence_url=item["licence_url"],
                attribution=item["attribution"],
                is_ai_generated=item["is_ai_generated"],
            ))
        return candidates

    async def download_clip(self, clip: CandidateClip, dest_path: str) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)

        cached_file = os.path.join(self.cache_dir, f"{clip.clip_id}.mp4")
        if not os.path.exists(cached_file):
            # Find item spec
            item = next((x for x in SAMPLE_FOOTAGE_LIBRARY if x["clip_id"] == clip.clip_id), SAMPLE_FOOTAGE_LIBRARY[0])
            color_src = item.get("color_spec", "color=c=0x112240:s=1920x1080:d=10")

            # Render genuine 1080p MP4 clip with cinematic aesthetic tone
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", color_src,
                "-vf", "vignette=PI/4,noise=c1s=8:c0f=u,format=yuv420p",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-r", "30",
                cached_file
            ]
            proc = await asyncio.to_thread(subprocess.run, cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if proc.returncode != 0:
                logger.error(f"FFmpeg failed creating mock clip: {proc.stderr.decode()}")
                raise RuntimeError("Failed to generate mock video clip")

        # Copy to destination
        import shutil
        shutil.copy2(cached_file, dest_path)
        return dest_path
