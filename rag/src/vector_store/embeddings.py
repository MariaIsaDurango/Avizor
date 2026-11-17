"""Local E5 embeddings; no implicit truncation or network download."""

import math
from pathlib import Path

MODEL_ID = "intfloat/multilingual-e5-base"
DIMENSIONS = 768


class E5Embedder:
    def __init__(self, revision: str = "main"):
        from huggingface_hub import snapshot_download
        from sentence_transformers import SentenceTransformer
        from transformers import AutoTokenizer

        path = snapshot_download(MODEL_ID, revision=revision, local_files_only=True)
        self.revision = Path(path).name
        self.tokenizer = AutoTokenizer.from_pretrained(
            path, use_fast=True, local_files_only=True
        )
        self.model = SentenceTransformer(path, device="cpu", local_files_only=True)
        if hasattr(self.model, "get_embedding_dimension"):
            dimension = self.model.get_embedding_dimension()
        else:
            dimension = self.model.get_sentence_embedding_dimension()

        if dimension != DIMENSIONS:
            raise ValueError("Unexpected embedding dimensions")
        self.model.max_seq_length = 512

    def encode(self, texts: list[str], *, query: bool = False) -> list[list[float]]:
        prefix = "query: " if query else "passage: "
        prepared = [prefix + text for text in texts]
        for text in prepared:
            if (
                len(
                    self.tokenizer.encode(
                        text, add_special_tokens=True, truncation=False, verbose=False
                    )
                )
                > 512
            ):
                raise ValueError("E5 input exceeds 512 tokens")
        if not prepared:
            return []
        vectors = self.model.encode(
            prepared,
            normalize_embeddings=True,
            batch_size=8,
            convert_to_numpy=True,
            show_progress_bar=False,
        ).tolist()
        for vector in vectors:
            if len(vector) != DIMENSIONS or not all(math.isfinite(x) for x in vector):
                raise ValueError("Invalid embedding")
            if not math.isclose(math.sqrt(sum(x * x for x in vector)), 1, abs_tol=1e-4):
                raise ValueError("Embedding is not L2 normalized")
        return vectors
