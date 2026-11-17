from abc import ABC, abstractmethod
from typing import List
import numpy as np


class BaseEmbeddingsProvider(ABC):
    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Returns embedding vector for a single string."""
        pass

    @abstractmethod
    def compute_similarity(self, text1: str, text2: str) -> float:
        """Returns semantic cosine similarity between two texts in range [0.0, 1.0]."""
        pass
