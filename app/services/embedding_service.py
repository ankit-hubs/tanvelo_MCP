"""
Embedding Generation Service with Connection Pooling, LRU In-Memory Caching,
Multi-Provider Support (NVIDIA NIM, OpenAI, Ollama, Local Deterministic).
"""

import hashlib
import logging
import math
from collections import OrderedDict
from typing import List, Optional
import httpx

from app.config import settings
from app.services.http_client import http_client_manager

logger = logging.getLogger("tanvelo.embedding")


class EmbeddingService:
    def __init__(self):
        self.provider = settings.EMBEDDING_PROVIDER.lower()
        self.api_key = settings.EMBEDDING_API_KEY or settings.NVIDIA_API_KEY
        self.model = settings.EMBEDDING_MODEL
        self.dim = settings.EMBEDDING_DIMENSION
        self.base_url = settings.NVIDIA_BASE_URL
        self._cache: OrderedDict[str, List[float]] = OrderedDict()
        self._max_cache_size = settings.EMBEDDING_CACHE_SIZE

    def _get_from_cache(self, text: str) -> Optional[List[float]]:
        if text in self._cache:
            self._cache.move_to_end(text)
            return self._cache[text]
        return None

    def _set_cache(self, text: str, embedding: List[float]):
        if text in self._cache:
            self._cache.move_to_end(text)
        else:
            if len(self._cache) >= self._max_cache_size:
                self._cache.popitem(last=False)
            self._cache[text] = embedding

    async def get_embedding(self, text: str) -> List[float]:
        """Generate embedding vector for single text with caching."""
        clean_text = text.strip().replace("\n", " ")
        cached = self._get_from_cache(clean_text)
        if cached is not None:
            return cached

        embeddings = await self.get_embeddings([clean_text])
        emb = embeddings[0]
        self._set_cache(clean_text, emb)
        return emb

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate normalized embedding vectors for a list of texts with batch caching."""
        clean_texts = [t.strip().replace("\n", " ") for t in texts]
        results: List[Optional[List[float]]] = [self._get_from_cache(t) for t in clean_texts]

        uncached_indices = [i for i, r in enumerate(results) if r is None]
        if not uncached_indices:
            return [r for r in results if r is not None]

        uncached_texts = [clean_texts[i] for i in uncached_indices]
        generated_embeddings: Optional[List[List[float]]] = None

        # Check if external provider should be used
        if self.api_key and not self.api_key.startswith("mock") and not self.api_key.startswith("nvapi-your"):
            try:
                if self.provider == "nvidia":
                    generated_embeddings = await self._call_nvidia_embeddings(uncached_texts)
                elif self.provider == "openai":
                    generated_embeddings = await self._call_openai_embeddings(uncached_texts)
                elif self.provider == "ollama":
                    generated_embeddings = await self._call_ollama_embeddings(uncached_texts)
            except Exception as e:
                logger.warning(f"Remote embedding provider '{self.provider}' failed ({e}). Falling back to local deterministic embeddings.")

        if generated_embeddings is None or len(generated_embeddings) != len(uncached_texts):
            generated_embeddings = [self._generate_local_embedding(t) for t in uncached_texts]

        # Put into results and update cache
        for idx, emb in zip(uncached_indices, generated_embeddings):
            self._set_cache(clean_texts[idx], emb)
            results[idx] = emb

        return [r for r in results if r is not None]

    async def _call_nvidia_embeddings(self, texts: List[str]) -> List[List[float]]:
        client = http_client_manager.get_client()
        url = f"{self.base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "input": texts,
            "model": self.model,
            "input_type": "query",
            "encoding_format": "float"
        }
        resp = await client.post(url, headers=headers, json=payload, timeout=8.0)
        resp.raise_for_status()
        data = resp.json()
        raw_embeddings = [item["embedding"] for item in data["data"]]
        return [self._normalize_vector(emb) for emb in raw_embeddings]

    async def _call_openai_embeddings(self, texts: List[str]) -> List[List[float]]:
        client = http_client_manager.get_client()
        url = f"{settings.OPENAI_BASE_URL}/embeddings"
        key = settings.OPENAI_API_KEY or self.api_key
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }
        payload = {
            "input": texts,
            "model": settings.EMBEDDING_MODEL if "text-embedding" in settings.EMBEDDING_MODEL else "text-embedding-3-small",
            "dimensions": self.dim
        }
        resp = await client.post(url, headers=headers, json=payload, timeout=8.0)
        resp.raise_for_status()
        data = resp.json()
        raw_embeddings = [item["embedding"] for item in data["data"]]
        return [self._normalize_vector(emb) for emb in raw_embeddings]

    async def _call_ollama_embeddings(self, texts: List[str]) -> List[List[float]]:
        client = http_client_manager.get_client()
        url = f"{settings.OLLAMA_BASE_URL}/api/embed"
        payload = {
            "model": settings.OLLAMA_MODEL,
            "input": texts
        }
        resp = await client.post(url, json=payload, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()
        raw_embeddings = data.get("embeddings", [])
        return [self._normalize_vector(emb) for emb in raw_embeddings]

    def _generate_local_embedding(self, text: str) -> List[float]:
        """
        Deterministic high-fidelity pseudo-semantic embedding for offline/local use and tests.
        Produces stable, normalized representations with meaningful lexical and n-gram overlap.
        """
        vec = [0.0] * self.dim
        words = text.lower().split()

        for word in words:
            clean_word = "".join(c for c in word if c.isalnum() or c in "-_")
            if not clean_word:
                continue

            h_word = int(hashlib.md5(clean_word.encode("utf-8")).hexdigest(), 16)
            vec[h_word % self.dim] += 1.5
            vec[(h_word >> 16) % self.dim] += 1.0
            vec[(h_word >> 32) % self.dim] += 0.8

            for n in range(3, min(6, len(clean_word) + 1)):
                for start in range(len(clean_word) - n + 1):
                    ngram = clean_word[start:start + n]
                    h_ng = int(hashlib.sha1(ngram.encode("utf-8")).hexdigest(), 16)
                    vec[h_ng % self.dim] += 0.4

        for i in range(len(words) - 1):
            bigram = f"{words[i]}_{words[i+1]}"
            h_bi = int(hashlib.md5(bigram.encode("utf-8")).hexdigest(), 16)
            vec[h_bi % self.dim] += 1.2

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
        """Compute cosine similarity between two normalized vectors in pure Python."""
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
