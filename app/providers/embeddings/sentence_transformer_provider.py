from typing import List
import os
from app.providers.embeddings.base import BaseEmbeddingsProvider
from app.providers.embeddings.keyword_provider import ContextualSimilarityProvider
from app.config import settings
from app.core.logging import logger

_model = None


def get_st_model():
    global _model
    if _model is None:
        # Only attempt to load SentenceTransformer if an explicit local model path exists
        # or if OFFLINE_TEST is not active
        if os.environ.get("USE_REAL_SENTENCE_TRANSFORMER") == "true":
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"Loading SentenceTransformer '{settings.SENTENCE_TRANSFORMER_MODEL}'...")
                _model = SentenceTransformer(settings.SENTENCE_TRANSFORMER_MODEL, device=settings.EMBEDDINGS_DEVICE)
            except Exception as e:
                logger.warning(f"Could not load SentenceTransformer ({e}). Using ContextualSimilarityProvider.")
                _model = False
        else:
            _model = False
    return _model


class SentenceTransformerEmbeddingsProvider(BaseEmbeddingsProvider):
    def __init__(self):
        self.fallback = ContextualSimilarityProvider()

    def embed_text(self, text: str) -> List[float]:
        model = get_st_model()
        if model:
            try:
                emb = model.encode(text, convert_to_numpy=True)
                return emb.tolist()
            except Exception as e:
                logger.error(f"Embedding failed: {e}")
        return self.fallback.embed_text(text)

    def compute_similarity(self, text1: str, text2: str) -> float:
        model = get_st_model()
        if model:
            try:
                import numpy as np
                emb1 = model.encode(text1, convert_to_numpy=True)
                emb2 = model.encode(text2, convert_to_numpy=True)
                cosine = float(np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2)))
                return round(float(max(0.0, (cosine + 1.0) / 2.0)), 4)
            except Exception as e:
                logger.warning(f"ST compute similarity error: {e}")
        return self.fallback.compute_similarity(text1, text2)
