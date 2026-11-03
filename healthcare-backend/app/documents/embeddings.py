"""Lazy, batch-oriented BGE-M3 dense embedding adapter."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from functools import lru_cache
from threading import Lock
from typing import Any

from app.core.config import get_settings
from app.core.model_runtime import HEAVY_MODEL_LOCK
from app.models.knowledge import EMBEDDING_DIMENSION


class EmbeddingError(RuntimeError):
    pass


class EmbeddingService:
    def __init__(
        self,
        model_name: str,
        batch_size: int,
        model_factory: Callable[..., Any] | None = None,
    ) -> None:
        self.model_name = model_name
        self.batch_size = batch_size
        self._model_factory = model_factory
        self._model: Any | None = None
        self._lock = Lock()

    def _get_model(self) -> Any:
        if self._model is None:
            if self._model_factory is None:
                from sentence_transformers import SentenceTransformer

                self._model_factory = SentenceTransformer
            try:
                self._model = self._model_factory(self.model_name, device="cpu")
            except Exception as exc:
                raise EmbeddingError("Embedding model could not be loaded.") from exc
        return self._model

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts or any(not text.strip() for text in texts):
            raise EmbeddingError("Embedding input must contain non-empty text.")
        try:
            with HEAVY_MODEL_LOCK, self._lock:
                vectors = self._get_model().encode(
                    list(texts),
                    batch_size=self.batch_size,
                    normalize_embeddings=True,
                    show_progress_bar=False,
                    convert_to_numpy=True,
                )
            result = [vector.tolist() if hasattr(vector, "tolist") else list(vector) for vector in vectors]
        except EmbeddingError:
            raise
        except Exception as exc:
            raise EmbeddingError("Embedding generation failed.") from exc
        if len(result) != len(texts) or any(len(vector) != EMBEDDING_DIMENSION for vector in result):
            raise EmbeddingError(f"Embedding output must have {EMBEDDING_DIMENSION} dimensions.")
        return result

    def release_model(self) -> None:
        """Release BGE-M3 weights before another large local model runs."""
        with HEAVY_MODEL_LOCK, self._lock:
            self._model = None


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    """Return the one lazy BGE-M3 service shared by chat and ingestion HTTP paths."""
    settings = get_settings()
    return EmbeddingService(settings.embedding_model, settings.embedding_batch_size)
