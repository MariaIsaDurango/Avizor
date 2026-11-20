"""Persistent Chroma collection with explicit embeddings and idempotent updates."""

from pathlib import Path

from rag.src.ingestion.models import MODEL_NAME

COLLECTION = "official_notices"


class ChromaStore:
    def __init__(self, path: Path, *, revision: str, synthetic: bool):
        import chromadb

        self.synthetic = synthetic
        self.client = chromadb.PersistentClient(path=str(path))
        expected = {
            "hnsw:space": "cosine",
            "embedding_model": MODEL_NAME,
            "embedding_revision": revision,
            "corpus_mode": "synthetic" if synthetic else "official",
        }
        # Do not modify existing metadata or silently reuse a different model/corpus.
        names = {
            item if isinstance(item, str) else item.name
            for item in self.client.list_collections()
        }
        if COLLECTION in names:
            self.collection = self.client.get_collection(
                COLLECTION, embedding_function=None
            )
        else:
            self.collection = self.client.create_collection(
                name=COLLECTION, metadata=expected, embedding_function=None
            )
        actual = self.collection.metadata or {}
        if any(actual.get(key) != value for key, value in expected.items()):
            raise ValueError(
                "Collection configuration differs; use a separate path or reindex"
            )

    def replace(self, notice, chunks, vectors):
        """Upsert stable IDs, remove obsolete IDs; exact body dedup across sources."""
        if notice.synthetic != self.synthetic:
            raise ValueError("Corpus mode mismatch")
        if not chunks or len(chunks) != len(vectors):
            raise ValueError("Invalid chunk/vector batch")
        old = self.collection.get(where={"url": notice.url}, include=[])["ids"]
        matches = self.collection.get(
            where={"content_hash": notice.content_hash}, include=["metadatas"]
        )
        duplicate = any(meta["url"] != notice.url for meta in matches["metadatas"])
        if duplicate:
            if old:
                self.collection.delete(ids=old)
            return "duplicate", 0
        ids = [notice.chunk_id(i) for i in range(len(chunks))]
        self.collection.upsert(
            ids=ids,
            documents=[chunk.text for chunk in chunks],
            embeddings=vectors,
            metadatas=[notice.metadata() for _ in chunks],
        )
        stale = sorted(set(old) - set(ids))
        if stale:
            self.collection.delete(ids=stale)
        return ("updated" if old else "inserted"), len(ids)

    def query(self, vector, *, limit: int = 5, where=None, documents: bool = False):
        count = self.collection.count()
        fields = ["metadatas", "distances"]
        if documents:
            fields.append("documents")
        if count == 0 or limit <= 0:
            return {key: [[]] for key in ["ids", *fields]}
        return self.collection.query(
            query_embeddings=[vector],
            n_results=min(limit, count, 5),
            include=fields,
            **({"where": where} if where is not None else {}),
        )
