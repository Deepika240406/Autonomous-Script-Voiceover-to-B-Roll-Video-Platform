import re
from typing import List, Dict, Any, Optional
from app.models.job import SceneData
from app.api.schemas.jobs import SceneInput
from app.core.logging import logger


class SceneSegmentationService:
    def __init__(self, min_scene_duration: float = 2.5, max_scene_duration: float = 8.5):
        self.min_scene_duration = min_scene_duration
        self.max_scene_duration = max_scene_duration

    def _split_into_sentences(self, text: str) -> List[str]:
        # Split on sentence terminals while keeping punctuation
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        return [s.strip() for s in sentences if s.strip()]

    def segment_from_scene_inputs(
        self,
        scene_inputs: List[SceneInput],
        total_duration: float,
        word_timings: Optional[List[Dict[str, Any]]] = None
    ) -> List[SceneData]:
        """
        Segment scenes when the user explicitly provides an IncuBrix scene list
        [{"text": "...", "visual_hint": "..."}].
        Maps each scene to speech timestamps accurately.
        """
        scenes: List[SceneData] = []
        num_scenes = len(scene_inputs)

        if not word_timings:
            # Fallback proportional timing if word timings absent
            total_words = sum(max(1, len(s.text.split())) for s in scene_inputs)
            curr_time = 0.0
            for idx, sc in enumerate(scene_inputs):
                w_count = max(1, len(sc.text.split()))
                dur = round((w_count / total_words) * total_duration, 3)
                start = round(curr_time, 3)
                end = round(total_duration if idx == num_scenes - 1 else curr_time + dur, 3)
                curr_time = end

                scenes.append(SceneData(
                    scene_index=idx,
                    narration_text=sc.text,
                    start_time=start,
                    end_time=end,
                    duration=round(end - start, 3),
                    visual_description=sc.visual_hint or sc.text,
                    visual_hint=sc.visual_hint,
                    search_query=sc.visual_hint or sc.text,
                    semantic_context=sc.text,
                ))
            return scenes

        # When word timings are available, find exact phrase boundaries
        word_idx = 0
        total_available_words = len(word_timings)
        curr_time = 0.0

        for idx, sc in enumerate(scene_inputs):
            scene_words = sc.text.strip().split()
            scene_word_count = len(scene_words)

            start_t = round(word_timings[word_idx]["start"] if word_idx < total_available_words else curr_time, 3)
            # Make sure start_t aligns with previous scene end to prevent gaps
            if idx > 0 and scenes:
                start_t = scenes[-1].end_time

            target_word_idx = min(total_available_words - 1, word_idx + scene_word_count - 1)
            target_speech_end = round(word_timings[target_word_idx]["end"], 3) if target_word_idx >= 0 else None
            if idx == num_scenes - 1:
                end_t = round(total_duration, 3)
            else:
                end_t = round(target_speech_end if target_speech_end is not None else start_t + 3.0, 3)

            # Ensure monotonic progress
            if end_t <= start_t:
                end_t = round(start_t + max(1.0, (total_duration - start_t) / (num_scenes - idx)), 3)

            word_idx += scene_word_count
            curr_time = end_t

            scenes.append(SceneData(
                scene_index=idx,
                narration_text=sc.text,
                start_time=start_t,
                end_time=end_t,
                duration=round(end_t - start_t, 3),
                visual_description=sc.visual_hint or sc.text,
                visual_hint=sc.visual_hint,
                search_query=sc.visual_hint or sc.text,
                semantic_context=sc.text,
                speech_end_time=target_speech_end,
            ))

        # Final pass: Ensure 100% narration coverage from 0 to total_duration
        if scenes:
            scenes[0].start_time = 0.0
            scenes[-1].end_time = round(total_duration, 3)
            scenes[-1].duration = round(scenes[-1].end_time - scenes[-1].start_time, 3)

        return scenes

    def segment_from_transcription_or_text(
        self,
        full_text: str,
        total_duration: float,
        segments: Optional[List[Dict[str, Any]]] = None,
        word_timings: Optional[List[Dict[str, Any]]] = None
    ) -> List[SceneData]:
        """
        Segments plain script or speech transcription into coherent, paced scenes.
        Respects sentence/phrase boundaries and speech timing.
        """
        raw_sentences = self._split_into_sentences(full_text)
        if not raw_sentences:
            raw_sentences = [full_text.strip()] if full_text.strip() else ["Narration"]

        # If Whisper segments exist with timestamps, align sentences to segments
        if segments and len(segments) > 0:
            return self._segment_with_speech_timestamps(segments, total_duration)

        # Proportional alignment if word timings exist
        if word_timings and len(word_timings) > 0:
            return self._segment_with_words(raw_sentences, word_timings, total_duration)

        # Baseline sentence segmentation
        scenes: List[SceneData] = []
        total_words = sum(max(1, len(s.split())) for s in raw_sentences)
        curr_time = 0.0
        num = len(raw_sentences)

        for idx, sentence in enumerate(raw_sentences):
            w_count = max(1, len(sentence.split()))
            dur = round((w_count / max(1, total_words)) * total_duration, 3)
            start = round(curr_time, 3)
            end = round(total_duration if idx == num - 1 else curr_time + dur, 3)
            curr_time = end

            scenes.append(SceneData(
                scene_index=idx,
                narration_text=sentence,
                start_time=start,
                end_time=end,
                duration=round(end - start, 3),
                visual_description=sentence,
                visual_hint=None,
                search_query=sentence,
                semantic_context=full_text,
            ))

        if scenes:
            scenes[0].start_time = 0.0
            scenes[-1].end_time = round(total_duration, 3)
            scenes[-1].duration = round(scenes[-1].end_time - scenes[-1].start_time, 3)

        return scenes

    def _segment_with_speech_timestamps(
        self,
        segments: List[Dict[str, Any]],
        total_duration: float
    ) -> List[SceneData]:
        scenes: List[SceneData] = []
        curr_time = 0.0

        # Merge segments that are too brief (< 2.0s) into neighbouring clauses
        merged_segments = []
        acc_text = ""
        acc_start = None
        acc_end = 0.0

        for seg in segments:
            text = (seg.get("text") or "").strip()
            if not text:
                continue
            start = seg.get("start", curr_time)
            end = seg.get("end", start + 2.0)

            if acc_start is None:
                acc_start = start

            acc_text = f"{acc_text} {text}".strip()
            acc_end = end

            # If accumulated duration meets minimum threshold or is final segment
            if (acc_end - acc_start) >= self.min_scene_duration:
                merged_segments.append({
                    "start": acc_start,
                    "end": acc_end,
                    "text": acc_text
                })
                acc_start = None
                acc_text = ""

        if acc_text and acc_start is not None:
            if merged_segments:
                merged_segments[-1]["end"] = acc_end
                merged_segments[-1]["text"] = f"{merged_segments[-1]['text']} {acc_text}".strip()
            else:
                merged_segments.append({
                    "start": acc_start,
                    "end": acc_end,
                    "text": acc_text
                })

        num_merged = len(merged_segments)
        for idx, item in enumerate(merged_segments):
            start = round(0.0 if idx == 0 else merged_segments[idx - 1]["end"], 3)
            end = round(total_duration if idx == num_merged - 1 else item["end"], 3)
            text = item["text"]
            actual_speech_end = round(item["end"], 3)

            scenes.append(SceneData(
                scene_index=idx,
                narration_text=text,
                start_time=start,
                end_time=end,
                duration=round(end - start, 3),
                visual_description=text,
                visual_hint=None,
                search_query=text,
                semantic_context=" ".join(s["text"] for s in merged_segments),
                speech_end_time=actual_speech_end,
            ))

        if scenes:
            scenes[0].start_time = 0.0
            scenes[-1].end_time = round(total_duration, 3)
            scenes[-1].duration = round(scenes[-1].end_time - scenes[-1].start_time, 3)

        return scenes

    def _segment_with_words(
        self,
        sentences: List[str],
        word_timings: List[Dict[str, Any]],
        total_duration: float
    ) -> List[SceneData]:
        scenes: List[SceneData] = []
        total_words = len(word_timings)
        word_pointer = 0
        num_sentences = len(sentences)

        for idx, sentence in enumerate(sentences):
            s_words = sentence.split()
            count = len(s_words)

            start = round(0.0 if idx == 0 else scenes[-1].end_time, 3)
            target_idx = min(total_words - 1, word_pointer + count - 1)

            if idx == num_sentences - 1:
                end = round(total_duration, 3)
            elif target_idx >= 0 and target_idx < total_words:
                end = round(word_timings[target_idx]["end"], 3)
            else:
                end = round(start + 3.0, 3)

            if end <= start:
                end = round(start + max(1.5, (total_duration - start) / (num_sentences - idx)), 3)

            word_pointer += count

            scenes.append(SceneData(
                scene_index=idx,
                narration_text=sentence,
                start_time=start,
                end_time=end,
                duration=round(end - start, 3),
                visual_description=sentence,
                visual_hint=None,
                search_query=sentence,
                semantic_context=sentence,
            ))

        if scenes:
            scenes[0].start_time = 0.0
            scenes[-1].end_time = round(total_duration, 3)
            scenes[-1].duration = round(scenes[-1].end_time - scenes[-1].start_time, 3)

        return scenes


scene_segmentation_service = SceneSegmentationService()
