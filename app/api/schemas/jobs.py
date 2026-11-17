from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional, Dict, Any, Literal
from app.api.schemas.errors import ErrorDetail


class SceneInput(BaseModel):
    text: str = Field(..., min_length=1, description="Narration text for this scene")
    visual_hint: Optional[str] = Field(default=None, description="Intended visual content or direction")


class CaptionsConfig(BaseModel):
    burn_in: bool = Field(default=True, description="Whether to burn subtitles directly into video frames")
    srt: bool = Field(default=True, description="Whether to generate and export a standalone captions.srt file")


class BrollJobCreateRequest(BaseModel):
    audio_url: Optional[str] = Field(default=None, description="Direct URL to voiceover audio file (mp3, wav, m4a)")
    script: Optional[str] = Field(default=None, description="Plain text narration script for automatic TTS synthesis")
    scenes: Optional[List[SceneInput]] = Field(default=None, description="Optional IncuBrix scene list with visual hints")
    voice: Optional[str] = Field(default="en-IN-female", description="Voice profile identifier (e.g. en-IN-female, hi-IN-female, ta-IN-female, en-US-male)")
    aspect_ratios: List[str] = Field(default=["16:9"], description="Requested aspect ratios: 16:9, 9:16, 1:1")
    style: Optional[str] = Field(default="bright, modern, real-world footage", description="Stylistic guidance for footage curation")
    avoid: Optional[List[str]] = Field(default_factory=list, description="Content keywords or themes to avoid in visual retrieval")
    captions: CaptionsConfig = Field(default_factory=CaptionsConfig, description="Caption generation and burn-in settings")
    callback_url: Optional[str] = Field(default=None, description="Optional webhook URL to receive job completion callback")

    @field_validator("aspect_ratios")
    @classmethod
    def validate_aspect_ratios(cls, v: List[str]) -> List[str]:
        allowed = {"16:9", "9:16", "1:1"}
        if not v:
            raise ValueError("aspect_ratios must contain at least one valid aspect ratio")
        for ratio in v:
            if ratio not in allowed:
                raise ValueError(f"Invalid aspect ratio '{ratio}'. Allowed values are: {sorted(list(allowed))}")
        return list(dict.fromkeys(v))  # deduplicate preserving order

    @model_validator(mode="after")
    def validate_inputs(self) -> "BrollJobCreateRequest":
        provided = [bool(self.audio_url), bool(self.script), bool(self.scenes)]
        if not any(provided):
            raise ValueError("At least one input must be provided: 'audio_url', 'script', or 'scenes'.")
        if self.script is not None and not self.script.strip():
            raise ValueError("Input 'script' cannot be empty or only whitespace.")
        if self.scenes is not None and len(self.scenes) == 0:
            raise ValueError("Input 'scenes' list cannot be empty.")
        if self.audio_url and (self.script or self.scenes):
            raise ValueError("Conflicting inputs: cannot provide both 'audio_url' and text/scenes in the same job.")
        return self


class BrollJobCreateResponse(BaseModel):
    job_id: str
    status: Literal["queued", "running", "succeeded", "failed"] = "queued"
    progress: int = 0
    status_url: str


class JobResultFiles(BaseModel):
    videos: Dict[str, str] = Field(default_factory=dict, description="URLs/paths for rendered video files keyed by aspect ratio")
    captions: Optional[str] = Field(default=None, description="URL/path to captions.srt")
    timeline: Optional[str] = Field(default=None, description="URL/path to timeline.json")
    manifest: Optional[str] = Field(default=None, description="URL/path to manifest.json")


class BrollJobStatusResponse(BaseModel):
    job_id: str
    status: Literal["queued", "running", "succeeded", "failed"]
    progress: int = Field(ge=0, le=100)
    stage: str
    created_at: str
    updated_at: str
    result: Optional[JobResultFiles] = None
    error: Optional[ErrorDetail] = None


class ClipReplacementRequest(BaseModel):
    clip_id: Optional[str] = Field(default=None, description="Identifier of replacement clip or search query override")
    search_query: Optional[str] = Field(default=None, description="Explicit new search query for this scene")
    source_provider: Optional[str] = Field(default=None, description="Optional forced provider (pexels, pixabay, mock, local)")
    visual_hint: Optional[str] = Field(default=None, description="Updated visual hint for this scene")
