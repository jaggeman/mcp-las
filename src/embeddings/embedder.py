import os
import re
import math
import hashlib
import logging
from typing import List, Optional
import numpy as np
import requests
from src.config import settings

logger = logging.getLogger(__name__)

SWEDISH_STOPWORDS = {
    'a', 'ad', 'alla', 'allt', 'alltså', 'andra', 'annat', 'att', 'av', 'blev', 'bli', 'blir',
    'blivit', 'då', 'de', 'del', 'dem', 'den', 'denna', 'denne', 'deras', 'dess', 'dessa', 'det',
    'detta', 'dig', 'din', 'dina', 'ditt', 'dock', 'där', 'därför', 'efter', 'ej', 'eller', 'en',
    'enkelt', 'enligt', 'er', 'era', 'ert', 'ett', 'få', 'får', 'fått', 'från', 'för', 'först',
    'genom', 'ha', 'hade', 'haft', 'han', 'hans', 'har', 'heller', 'helt', 'henne', 'hennes',
    'hos', 'hon', 'honom', 'hur', 'här', 'i', 'icke', 'igen', 'ifrån', 'in', 'inte', 'ja',
    'jag', 'ju', 'kan', 'kunde', 'kunnat', 'kunna', 'lika', 'man', 'med', 'mellan', 'men',
    'mer', 'mera', 'mig', 'min', 'mina', 'mitt', 'mot', 'mycket', 'måste', 'när', 'någon',
    'något', 'några', 'nån', 'nåt', 'och', 'också', 'om', 'oss', 'på', 'redan', 'rätt',
    'samma', 'sedan', 'sen', 'sig', 'sin', 'sina', 'sitt', 'själv', 'skall', 'ska', 'skulle',
    'som', 'säga', 'så', 'tack', 'till', 'tills', 'under', 'upp', 'ur', 'utan', 'vad',
    'var', 'vara', 'varit', 'varje', 'varken', 'vars', 'vart', 'vem', 'vems', 'verkar',
    'vi', 'vid', 'vilka', 'vilkas', 'vilken', 'vilket', 'vill', 'viss', 'vissa', 'vår',
    'våra', 'vårt', 'än', 'ändå', 'är', 'även', 'över', 'gäller', 'gällande'
}

class Embedder:
    """
    Embedding service supporting OpenAI (text-embedding-3-small),
    Google Gemini (text-embedding-004), and Smart Offline Semantic Embeddings.
    """

    @classmethod
    def get_embedding(cls, text: str) -> List[float]:
        provider = settings.EMBEDDING_PROVIDER.lower()

        if (provider == "openai" or (provider == "mock" and settings.OPENAI_API_KEY)) and settings.OPENAI_API_KEY:
            return cls._embed_openai(text)
        elif (provider == "gemini" or (provider == "mock" and settings.GEMINI_API_KEY)) and settings.GEMINI_API_KEY:
            return cls._embed_gemini(text)
        else:
            return cls._embed_mock(text)

    @classmethod
    def _embed_openai(cls, text: str) -> List[float]:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            clean_input = text.replace("\n", " ")[:8192]
            res = client.embeddings.create(
                input=clean_input,
                model="text-embedding-3-small"
            )
            return res.data[0].embedding
        except Exception as e:
            logger.warning(f"OpenAI embedding error: {e}, falling back to offline embedder.")
            return cls._embed_mock(text)

    @classmethod
    def _embed_gemini(cls, text: str) -> List[float]:
        if not settings.GEMINI_API_KEY:
            return cls._embed_mock(text)
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={settings.GEMINI_API_KEY}"
            clean_input = text.replace("\n", " ")[:2048]
            resp = requests.post(url, json={
                "model": "models/text-embedding-004",
                "content": {"parts": [{"text": clean_input}]}
            }, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return data["embedding"]["values"]
            else:
                logger.warning(f"Gemini API returned status {resp.status_code}: {resp.text}")
                return cls._embed_mock(text)
        except Exception as e:
            logger.warning(f"Gemini embedding error: {e}, falling back to offline embedder.")
            return cls._embed_mock(text)

    @classmethod
    def _embed_mock(cls, text: str, dim: int = 1536) -> List[float]:
        """
        High-quality deterministic offline semantic embedding.
        Strips stopwords and creates n-gram hashed vectors without position decay bias.
        """
        words = re.findall(r'[a-zåäö0-9]+', text.lower())
        meaningful = [w for w in words if w not in SWEDISH_STOPWORDS and len(w) >= 2]
        if not meaningful:
            meaningful = words

        vec = np.zeros(dim, dtype=np.float32)
        for w in meaningful:
            # Word level hash
            h_w = int(hashlib.md5(f"w_{w}".encode('utf-8')).hexdigest(), 16) % dim
            vec[h_w] += 2.0
            # Character n-grams (3 to 5 chars) for morphological matching
            for n in (3, 4, 5):
                for i in range(len(w) - n + 1):
                    ngram = w[i:i + n]
                    h_ng = int(hashlib.md5(f"ng_{ngram}".encode('utf-8')).hexdigest(), 16) % dim
                    vec[h_ng] += 0.5

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

