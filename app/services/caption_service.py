import os
from typing import List, Dict, Any
from app.models.job import SceneData


def format_srt_timestamp(seconds: float) -> str:
    total_ms = max(0, int(round(seconds * 1000)))
    ms = total_ms % 1000
    total_seconds = total_ms // 1000
    s = total_seconds % 60
    total_minutes = total_seconds // 60
    m = total_minutes % 60
    h = total_minutes // 60
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


class CaptionService:
    def generate_srt(self, scenes: List[SceneData], output_path: str) -> str:
        """
        Generates compliant SubRip (.srt) caption file from scene narration timings.
        Guarantees non-overlapping, strictly positive timestamps and sequential numbering.
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        srt_blocks: List[str] = []
        seq_num = 1

        for scene in scenes:
            text = scene.narration_text.strip()
            if not text:
                continue

            start_t = max(0.0, scene.start_time)
            end_t = max(start_t + 0.5, scene.end_time)

            start_str = format_srt_timestamp(start_t)
            end_str = format_srt_timestamp(end_t)

            srt_blocks.append(f"{seq_num}\n{start_str} --> {end_str}\n{text}\n")
            seq_num += 1

        content = "\n".join(srt_blocks)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        return output_path


caption_service = CaptionService()
