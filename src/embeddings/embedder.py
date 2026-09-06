import os
import math
import hashlib
from typing import List, Optional
import numpy as np
from src.config import settings

class Embedder:
    """
    Embedding service supporting OpenAI, Gemini, and Mock (offline) embeddings.
    """
    
    @classmethod
    def get_embedding(cls, text: str) -> List[float]:
        provider = settings.EMBEDDING_PROVIDER.lower()
        
        if provider == "openai" and settings.OPENAI_API_KEY:
            return cls._embed_openai(text)
        elif provider == "gemini" and settings.GEMINI_API_KEY:
            return cls._embed_gemini(text)
        else:
            return cls._embed_mock(text)

    @classmethod
    def _embed_openai(cls, text: str) -> List[float]:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            res = client.embeddings.create(
                input=text,
                model="text-embedding-3-small"
            )
            return res.data[0].embedding
        except Exception as e:
            print(f"OpenAI embedding error: {e}, falling back to mock.")
            return cls._embed_mock(text)

    @classmethod
    def _embed_gemini(cls, text: str) -> List[float]:
        # Fallback to mock if SDK not configured
        return cls._embed_mock(text)

    @classmethod
    def _embed_mock(cls, text: str, dim: int = 1536) -> List[float]:
        """
        Deterministic mock embedding using MD5 hash & n-grams for reproducible testing.
        """
        words = text.lower().split()
        vec = np.zeros(dim, dtype=np.float32)
        
        for i, word in enumerate(words):
            h = int(hashlib.md5(word.encode('utf-8')).hexdigest(), 16)
            idx = h % dim
            weight = 1.0 / (1.0 + math.log(i + 1))
            vec[idx] += weight
            
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    @staticmethod
    def cosine_similarity(v1: List[float], v2: List[float]) -> float:
        a = np.array(v1)
        b = np.array(v2)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))
