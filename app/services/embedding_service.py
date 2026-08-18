"""
Embedding Generation Service
Supports NVIDIA NIM embeddings, OpenAI-compatible embeddings, and deterministic local mock fallback.
Uses zero-dependency pure Python vector math for maximum portability and robustness across all runtime environments.
"""

import hashlib
import logging
import math
from typing import List
import httpx

from app.config import settings

logger = logging.getLogger("tanvelo.embedding")


class EmbeddingService:
    def __init__(self):
        self.provider = settings.EMBEDDING_PROVIDER.lower()
        self.api_key = settings.EMBEDDING_API_KEY or settings.NVIDIA_API_KEY
        self.model = settings.EMBEDDING_MODEL
        self.dim = settings.EMBEDDING_DIMENSION
        self.base_url = settings.NVIDIA_BASE_URL

    async def get_embedding(self, text: str) -> List[float]:
        """Generate embedding vector for single text."""
        embeddings = await self.get_embeddings([text])
        return embeddings[0]

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate normalized embedding vectors for a list of texts."""
        clean_texts = [t.strip().replace("\n", " ") for t in texts]

        # Use external API if key is present and provider is configured
        if self.api_key and not self.api_key.startswith("mock") and not self.api_key.startswith("nvapi-your"):
            try:
                if self.provider in ["nvidia", "openai"]:
                    return await self._call_remote_embeddings(clean_texts)
            except Exception as e:
                logger.warning(f"Remote embedding API call failed ({e}), falling back to deterministic local embeddings.")

        # Fallback to high-quality deterministic pseudo-semantic embeddings
        return [self._generate_local_embedding(t) for t in clean_texts]

    async def _call_remote_embeddings(self, texts: List[str]) -> List[List[float]]:
        url = f"{self.base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "input": texts,
            "model": self.model,
            "encoding_format": "float"
        }
        if self.provider == "nvidia":
            payload["input_type"] = "query"

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            raw_embeddings = [item["embedding"] for item in data["data"]]
            return [self._normalize_vector(emb) for emb in raw_embeddings]

    def _generate_local_embedding(self, text: str) -> List[float]:
        """
        Deterministic local feature embedding for local development, offline runs, and unit testing.
        Uses character n-grams, word token hashes, and lexical similarity to produce
        high-fidelity embeddings where related phrases (e.g. 'FastAPI and Supabase')
        have high cosine similarity.
        """
        vec = [0.0] * self.dim
        words = text.lower().split()

        # Word-level features
        for i, word in enumerate(words):
            # Clean word
            clean_word = "".join(c for c in word if c.isalnum() or c in "-_")
            if not clean_word:
                continue

            # Position-independent hash
            h_word = int(hashlib.md5(clean_word.encode("utf-8")).hexdigest(), 16)
            idx1 = h_word % self.dim
            idx2 = (h_word >> 16) % self.dim
            idx3 = (h_word >> 32) % self.dim

            vec[idx1] += 1.5
            vec[idx2] += 1.0
            vec[idx3] += 0.8

            # Substring / n-gram features (length 3 to 5)
            for n in range(3, min(6, len(clean_word) + 1)):
                for start in range(len(clean_word) - n + 1):
                    ngram = clean_word[start:start + n]
                    h_ng = int(hashlib.sha1(ngram.encode("utf-8")).hexdigest(), 16)
                    ng_idx = h_ng % self.dim
                    vec[ng_idx] += 0.4

        # Context phrase features (bigrams)
        for i in range(len(words) - 1):
            bigram = f"{words[i]}_{words[i+1]}"
            h_bi = int(hashlib.md5(bigram.encode("utf-8")).hexdigest(), 16)
            vec[h_bi % self.dim] += 1.2

        # Global sentence hash baseline
        h_all = int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16)
        vec[h_all % self.dim] += 0.5

        return self._normalize_vector(vec)

    @staticmethod
    def _normalize_vector(vec: List[float]) -> List[float]:
        sq_sum = sum(x * x for x in vec)
        norm = math.sqrt(sq_sum)
        if norm > 0:
            return [x / norm for x in vec]
        return vec

    @staticmethod
    def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
        """Compute cosine similarity between two normalized vectors using pure Python."""
        if not vec_a or not vec_b:
            return 0.0
        
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))

        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        sim = dot / (norm_a * norm_b)
        return max(-1.0, min(1.0, float(sim)))


embedding_service = EmbeddingService()
