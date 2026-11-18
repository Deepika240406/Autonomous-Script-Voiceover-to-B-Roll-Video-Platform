import os
from typing import List, Dict, Any, Set, Optional, Tuple
from app.models.job import SceneData, ClipMetadata
from app.providers.footage.base import BaseFootageProvider, CandidateClip
from app.providers.footage.pexels_provider import PexelsFootageProvider
from app.providers.footage.pixabay_provider import PixabayFootageProvider
from app.providers.footage.mock_provider import MockFootageProvider
from app.providers.footage.local_fallback_provider import LocalFallbackProvider
from app.services.semantic_service import semantic_service
from app.services.vision_language_service import vision_language_service
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

            # 1. Semantic context analysis, LLM visual description & query expansion
            analysis = semantic_service.analyze_hard_cases(
                text=scene.narration_text,
                visual_hint=scene.visual_hint,
                overall_context=scene.semantic_context
            )
            scene.search_query = analysis["primary_query"]
            if analysis.get("visual_description"):
                scene.visual_description = analysis["visual_description"]
            scene.warnings.extend(analysis["warnings"])

            # 2. Candidate retrieval across providers using tiered hierarchy
            selected_clip_metadata: Optional[ClipMetadata] = None

            # Tier 1: Real external providers (Pixabay, Pexels)
            # Tier 2: Internal mock / fallback providers
            external_providers = [p for p in providers if p.provider_name in ("pexels", "pixabay")]
            internal_providers = [p for p in providers if p.provider_name not in ("pexels", "pixabay")]

            tiers = []
            if external_providers:
                tiers.append(("external", external_providers))
            if internal_providers:
                tiers.append(("internal", internal_providers))

            # Full scene context incorporates narration, overall storyline context, visual concept, and user visual hints
            context_elements = [f"Narration: {scene.narration_text.strip()}"]
            if scene.semantic_context and scene.semantic_context.strip() != scene.narration_text.strip():
                context_elements.append(f"Story Context: {scene.semantic_context.strip()}")
            if scene.visual_description:
                context_elements.append(f"Visual Concept: {scene.visual_description.strip()}")
            if scene.visual_hint:
                context_elements.append(f"Visual Hint: {scene.visual_hint.strip()}")
            full_scene_context = " | ".join(context_elements)

            for tier_name, tier_providers in tiers:
                if selected_clip_metadata:
                    break

                for provider in tier_providers:
                    if selected_clip_metadata:
                        break

                    # Priority 1: Multi-candidate pooling across descriptive queries instead of single query
                    candidate_pool: Dict[str, Tuple[CandidateClip, str, str]] = {}  # clip_id -> (cand, metadata_str, query)

                    for query in analysis["all_queries"]:
                        try:
                            # Fetch 10-20 candidates per scene where provider allows it
                            results = await provider.search(query=query, min_duration=scene.duration, count=20)
                            for cand in results:
                                if cand.clip_id in used_clip_ids or cand.clip_id in candidate_pool:
                                    continue

                                metadata_str = f"{cand.title} {cand.description} {' '.join(cand.tags)}"
                                violates, reason = semantic_service.violates_avoid_rules(metadata_str, avoid)
                                if violates:
                                    logger.info(f"Candidate {cand.clip_id} rejected due to avoid rule: '{reason}'")
                                    continue

                                domain_mismatch, domain_reason = semantic_service.is_domain_incompatible(
                                    metadata_str, analysis.get("domain", "general")
                                )
                                if domain_mismatch:
                                    logger.info(f"Candidate {cand.clip_id} rejected due to domain mismatch: '{domain_reason}'")
                                    continue

                                candidate_pool[cand.clip_id] = (cand, metadata_str, query)
                        except Exception as e:
                            logger.warning(f"Provider {provider.provider_name} search failed for query '{query}': {e}")
                            scene.warnings.append(f"Provider {provider.provider_name} error: {str(e)}")

                    if candidate_pool:
                        pool_items = list(candidate_pool.values())
                        pool_metas = [item[1] for item in pool_items]

                        # Vectorized batch ranking against the full scene context
                        rel_scores = semantic_service.compute_batch_relevance(
                            scene_text=full_scene_context,
                            candidate_descriptions=pool_metas,
                            visual_hint=scene.visual_hint
                        )
                        min_rel = 1.8 if tier_name == "external" else 1.0

                        valid_candidates = []
                        for score, (cand, meta, q) in zip(rel_scores, pool_items):
                            if score >= min_rel:
                                valid_candidates.append((score, cand, q))

                        if valid_candidates:
                            # Rank candidates by full scene context semantic relevance score descending
                            valid_candidates.sort(key=lambda x: x[0], reverse=True)
                            best_sem_score, best_cand, matched_query = valid_candidates[0]

                            used_clip_ids.add(best_cand.clip_id)

                            # Download chosen clip
                            dest_filename = f"scene_{scene.scene_index}_{best_cand.clip_id}.mp4"
                            dest_path = os.path.join(job_dir, "footage", dest_filename)
                            await provider.download_clip(best_cand, dest_path)

                            # Priority 2: Extract frame and run independent VLM evaluation
                            frames_dir = os.path.join(job_dir, "frames")
                            frame_dest = os.path.join(frames_dir, f"scene_{scene.scene_index}_{best_cand.clip_id}.jpg")
                            mid_ts = min(best_cand.duration / 2.0, 2.0) if best_cand.duration else 1.0
                            extracted_frame = vision_language_service.extract_video_frame(
                                video_path=dest_path,
                                timestamp=mid_ts,
                                output_path=frame_dest
                            )
                            vlm_eval = vision_language_service.evaluate_frame(
                                frame_path=extracted_frame,
                                narration_text=scene.narration_text,
                                visual_concept=scene.visual_description,
                                semantic_score=best_sem_score
                            )
                            vlm_score = vlm_eval["vlm_score"]
                            composite_relevance = vlm_eval["composite_score"]

                            selection_reason = (
                                f"Selected from {best_cand.provider} matching visual concept '{matched_query}' "
                                f"ranked by full scene context. Sentence-BERT: {best_sem_score}/5.0, "
                                f"Vision-Language: {vlm_score}/5.0"
                            )

                            selected_clip_metadata = ClipMetadata(
                                clip_id=best_cand.clip_id,
                                provider=best_cand.provider,
                                source_url=best_cand.download_url,
                                local_path=dest_path,
                                duration=best_cand.duration,
                                width=best_cand.width,
                                height=best_cand.height,
                                fps=best_cand.fps,
                                licence_name=best_cand.licence_name,
                                licence_url=best_cand.licence_url,
                                attribution=best_cand.attribution,
                                is_ai_generated=best_cand.is_ai_generated,
                                selection_reason=selection_reason,
                                relevance_score=composite_relevance,
                                semantic_score=best_sem_score,
                                vlm_score=vlm_score,
                                human_rating=None,  # strictly isolated from automated model scores
                                extracted_frame_path=extracted_frame,
                                search_query=matched_query,
                                warnings=list(scene.warnings),
                            )
                            break
                        else:
                            logger.info(
                                f"Provider {provider.provider_name} yielded {len(candidate_pool)} pooled clips across queries "
                                f"but none satisfied relevance bar ({min_rel}). Rejecting and checking next tier..."
                            )

            # 3. If no candidate succeeded, invoke deterministic local fallback
            if not selected_clip_metadata:
                logger.warning(f"All providers exhausted for Scene {scene.scene_index}. Activating LocalFallbackProvider.")
                fallback_cand_list = await self.fallback_provider.search(scene.narration_text, min_duration=scene.duration)
                cand = fallback_cand_list[0]
                dest_path = os.path.join(job_dir, "footage", f"scene_{scene.scene_index}_fallback.mp4")
                await self.fallback_provider.download_clip(cand, dest_path)

                frames_dir = os.path.join(job_dir, "frames")
                frame_dest = os.path.join(frames_dir, f"scene_{scene.scene_index}_fallback.jpg")
                extracted_frame = vision_language_service.extract_video_frame(
                    video_path=dest_path,
                    timestamp=0.5,
                    output_path=frame_dest
                )
                vlm_eval = vision_language_service.evaluate_frame(
                    frame_path=extracted_frame,
                    narration_text=scene.narration_text,
                    visual_concept=scene.visual_description,
                    semantic_score=3.5
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
                    selection_reason="Procedural fallback generated after external provider search yielded no matches.",
                    relevance_score=vlm_eval["composite_score"],
                    semantic_score=3.5,
                    vlm_score=vlm_eval["vlm_score"],
                    human_rating=None,  # strictly isolated from automated model scores
                    extracted_frame_path=extracted_frame,
                    search_query=scene.search_query,
                    warnings=list(scene.warnings) + ["External footage unavailable; generated local fallback video."],
                )

            scene.selected_clip = selected_clip_metadata


footage_service = FootageService()
