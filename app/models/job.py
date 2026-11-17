from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any


@dataclass
class ClipMetadata:
    clip_id: str
    provider: str
    source_url: str
    local_path: str
    duration: float
    width: int
    height: int
    fps: float
    licence_name: str
    licence_url: str
    attribution: str
    is_ai_generated: bool
    selection_reason: str
    relevance_score: float
    search_query: str
    warnings: List[str] = field(default_factory=list)


@dataclass
class SceneData:
    scene_index: int
    narration_text: str
    start_time: float
    end_time: float
    duration: float
    visual_description: str
    visual_hint: Optional[str]
    search_query: str
    semantic_context: str
    selected_clip: Optional[ClipMetadata] = None
    candidate_clips: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class JobRecord:
    job_id: str
    status: str = "queued"  # queued, running, succeeded, failed
    progress: int = 0
    stage: str = "initialized"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Inputs
    input_type: str = "script"  # audio_file, audio_url, script, scenes
    request_params: Dict[str, Any] = field(default_factory=dict)
    audio_path: Optional[str] = None
    narration_text: Optional[str] = None

    # Processing state
    scenes: List[SceneData] = field(default_factory=list)
    word_timestamps: List[Dict[str, Any]] = field(default_factory=list)

    # Generated outputs
    output_videos: Dict[str, str] = field(default_factory=dict)
    captions_file: Optional[str] = None
    timeline_file: Optional[str] = None
    manifest_file: Optional[str] = None

    # Observability & Metrics
    stage_timings: Dict[str, float] = field(default_factory=dict)
    cost_estimates: Dict[str, float] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    error: Optional[Dict[str, Any]] = None

    def update_progress(self, progress: int, stage: str):
        self.progress = max(0, min(100, progress))
        self.stage = stage
        self.updated_at = datetime.now(timezone.utc).isoformat()
