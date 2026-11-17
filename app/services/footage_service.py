import os
from typing import List, Dict, Any, Set, Optional, Tuple
from app.models.job import SceneData, ClipMetadata
from app.providers.footage.base import BaseFootageProvider, CandidateClip
from app.providers.footage.pexels_provider import PexelsFootageProvider
from app.providers.footage.pixabay_provider import PixabayFootageProvider
from app.providers.footage.mock_provider import MockFootageProvider
from app.providers.footage.local_fallback_provider import LocalFallbackProvider
from app.services.semantic_service import semantic_service
from app.config import settings
from app.core.logging import logger


class FootageService:
    def __init__(self):
        self.mock_provider = MockFootageProvider()
        self.fallback_provider = LocalFallbackProvider()
        self.pexels_provider = PexelsFootageProvider()
        self.pixabay_provider = PixabayFootageProvider()

    def get_providers_pipeline(self, forced_provider: Optional[str] = None) -> List[BaseFootageProvider]:
        if forced_provider == "pexels":
            return [self.pexels_provider, self.mock_provider, self.fallback_provider]
        if forced_provider == "pixabay":
            return [self.pixabay_provider, self.mock_provider, self.fallback_provider]
        if forced_provider == "mock":
            return [self.mock_provider, self.fallback_provider]
        if forced_provider == "local":
            return [self.fallback_provider]

        # Default multi-tier pipeline
        pipeline: List[BaseFootageProvider] = []
        if settings.PEXELS_API_KEY:
            pipeline.append(self.pexels_provider)
        if settings.PIXABAY_API_KEY:
            pipeline.append(self.pixabay_provider)

        # Mock provider is always present as secondary/testing tier
        pipeline.append(self.mock_provider)
        # Procedural local fallback is the ultimate failsafe
        pipeline.append(self.fallback_provider)
        return pipeline

    async def select_footage_for_scenes(
        self,
        scenes: List[SceneData],
        job_dir: str,
        avoid_list: Optional[List[str]] = None,
        style: Optional[str] = None,
        forced_provider: Optional[str] = None
    ) -> None:
        avoid = avoid_list or []
        used_clip_ids: Set[str] = set()
        providers = self.get_providers_pipeline(forced_provider)

        for scene in scenes:
            logger.info(f"Retrieving footage for Scene {scene.scene_index}: '{scene.narration_text[:40]}...'")

            # 1. Semantic context analysis and query expansion
            analysis = semantic_service.analyze_hard_cases(scene.narration_text, scene.visual_hint)
            scene.search_query = analysis["primary_query"]
            scene.warnings.extend(analysis["warnings"])

            # 2. Candidate retrieval across providers
            candidates: List[CandidateClip] = []
            selected_clip_metadata: Optional[ClipMetadata] = None

            for query in analysis["all_queries"]:
                if selected_clip_metadata:
                    break

                for provider in providers:
                    try:
                        results = await provider.search(query=query, min_duration=scene.duration, count=4)
                        for cand in results:
                            # Rule: No clip used twice in one video
                            if cand.clip_id in used_clip_ids:
                                continue

                            # Rule: Avoidance filtering
                            metadata_str = f"{cand.title} {cand.description} {' '.join(cand.tags)}"
                            violates, reason = semantic_service.violates_avoid_rules(metadata_str, avoid)
                            if violates:
                                logger.info(f"Candidate {cand.clip_id} rejected due to avoid rule: '{reason}'")
                                continue

                            # Compute semantic relevance score (1.0 - 5.0)
                            rel_score = semantic_service.compute_relevance(
                                scene_text=scene.narration_text,
                                candidate_description=metadata_str,
                                visual_hint=scene.visual_hint
                            )

                            # Reject weak matches (unless fallback provider)
                            if rel_score < 2.2 and provider.provider_name not in ("local_fallback", "mock_provider"):
                                continue

                            candidates.append(cand)
                            used_clip_ids.add(cand.clip_id)

                            # Download chosen clip
                            dest_filename = f"scene_{scene.scene_index}_{cand.clip_id}.mp4"
                            dest_path = os.path.join(job_dir, "footage", dest_filename)
                            await provider.download_clip(cand, dest_path)

                            selection_reason = (
                                f"Selected from {cand.provider} matching visual concept '{query}' "
                                f"with semantic relevance {rel_score}/5.0"
                            )

                            selected_clip_metadata = ClipMetadata(
                                clip_id=cand.clip_id,
                                provider=cand.provider,
                                source_url=cand.download_url,
                                local_path=dest_path,
                                duration=cand.duration,
                                width=cand.width,
                                height=cand.height,
                                fps=cand.fps,
                                licence_name=cand.licence_name,
                                licence_url=cand.licence_url,
                                attribution=cand.attribution,
                                is_ai_generated=cand.is_ai_generated,
                                selection_reason=selection_reason,
                                relevance_score=rel_score,
                                search_query=query,
                                warnings=list(scene.warnings),
                            )
                            break
                        if selected_clip_metadata:
                            break
                    except Exception as e:
                        logger.warning(f"Provider {provider.provider_name} search/download failed: {e}. Moving to next.")
                        scene.warnings.append(f"Provider {provider.provider_name} error: {str(e)}")

            # 3. If no candidate succeeded, invoke deterministic local fallback
            if not selected_clip_metadata:
                logger.warning(f"All providers exhausted for Scene {scene.scene_index}. Activating LocalFallbackProvider.")
                fallback_cand_list = await self.fallback_provider.search(scene.narration_text, min_duration=scene.duration)
                cand = fallback_cand_list[0]
                dest_path = os.path.join(job_dir, "footage", f"scene_{scene.scene_index}_fallback.mp4")
                await self.fallback_provider.download_clip(cand, dest_path)

                selected_clip_metadata = ClipMetadata(
                    clip_id=cand.clip_id,
                    provider=cand.provider,
                    source_url=cand.download_url,
                    local_path=dest_path,
                    duration=cand.duration,
                    width=cand.width,
                    height=cand.height,
                    fps=cand.fps,
                    licence_name=cand.licence_name,
                    licence_url=cand.licence_url,
                    attribution=cand.attribution,
                    is_ai_generated=cand.is_ai_generated,
                    selection_reason="Procedural fallback generated after external provider search yielded no matches.",
                    relevance_score=3.5,
                    search_query=scene.search_query,
                    warnings=list(scene.warnings) + ["External footage unavailable; generated local fallback video."],
                )

            scene.selected_clip = selected_clip_metadata


footage_service = FootageService()
