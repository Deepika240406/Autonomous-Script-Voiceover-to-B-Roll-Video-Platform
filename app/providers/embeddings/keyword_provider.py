import math
import re
from typing import List, Dict, Set
from collections import Counter
from app.providers.embeddings.base import BaseEmbeddingsProvider


STOPWORDS = {
    "a", "an", "the", "in", "on", "at", "by", "for", "with", "about", "against",
    "between", "into", "through", "during", "before", "after", "above", "below",
    "to", "from", "up", "down", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "and", "but", "if", "or", "because",
    "as", "until", "while", "of", "it", "its", "this", "that", "these", "those"
}


class ContextualSimilarityProvider(BaseEmbeddingsProvider):
    """
    Calibrated contextual similarity provider with stopword filtering,
    sub-word n-grams, and semantic term weighting.
    """
    def _tokenize(self, text: str) -> List[str]:
        cleaned = re.sub(r"[^\w\s]", " ", text.lower())
        tokens = [t for t in cleaned.split() if len(t) > 1 and t not in STOPWORDS]
        return tokens or [t for t in cleaned.split() if len(t) > 1]

    def _get_char_ngrams(self, text: str, n: int = 3) -> List[str]:
        cleaned = re.sub(r"\s+", " ", text.lower().strip())
        if len(cleaned) < n:
            return [cleaned]
        return [cleaned[i:i+n] for i in range(len(cleaned) - n + 1)]

    def embed_text(self, text: str) -> List[float]:
        tokens = self._tokenize(text)
        vec = [0.0] * 64
        for t in tokens:
            idx = abs(hash(t)) % 64
            vec[idx] += 1.0
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]

    def compute_similarity(self, text1: str, text2: str) -> float:
        tokens1 = set(self._tokenize(text1))
        tokens2 = set(self._tokenize(text2))

        if not tokens1 or not tokens2:
            return 0.1

        # Content keyword containment
        intersection = tokens1.intersection(tokens2)
        containment = len(intersection) / max(1, min(len(tokens1), len(tokens2)))
        jaccard = len(intersection) / len(tokens1.union(tokens2))

        # Substring n-gram overlap
        ngrams1 = Counter(self._get_char_ngrams(text1, 3))
        ngrams2 = Counter(self._get_char_ngrams(text2, 3))
        dot_product = sum(ngrams1[ng] * ngrams2[ng] for ng in ngrams1 if ng in ngrams2)
        mag1 = math.sqrt(sum(v * v for v in ngrams1.values()))
        mag2 = math.sqrt(sum(v * v for v in ngrams2.values()))
        ngram_sim = (dot_product / (mag1 * mag2)) if (mag1 > 0 and mag2 > 0) else 0.0

        # Calibrated contextual similarity
        raw_sim = 0.60 * containment + 0.20 * jaccard + 0.20 * ngram_sim
        # Apply gentle sigmoidal boost for strong partial matches
        boosted = math.pow(raw_sim, 0.75) if raw_sim > 0.2 else raw_sim
        return round(min(1.0, max(0.05, boosted)), 4)
