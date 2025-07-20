from __future__ import annotations

"""Multi-source RAG retriever with negative filtering and deduplication."""

from difflib import SequenceMatcher
from pathlib import Path
from typing import List, Callable, Optional, Union, Any


class Document:
    """Simple document wrapper holding content and source information."""

    def __init__(self, content: str, source: str = "", metadata: Optional[dict] = None):
        self.content: str = content
        self.source: str = source
        self.metadata: dict = metadata or {}
        self.score: float | None = None

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        snippet = self.content[:30].replace("\n", " ")
        return f"Document(source={self.source}, content='{snippet}...', score={self.score})"


class BaseSource:
    """Abstract retrieval source."""

    def search(self, query: str) -> List[Document]:
        raise NotImplementedError


class LocalFileSource(BaseSource):
    """Retrieve documents from local text files or direct text snippets."""

    def __init__(self, file_paths: List[str]):
        self.documents: List[Document] = []
        for path in file_paths:
            text: str
            p = Path(path)
            if p.exists():
                text = p.read_text(encoding="utf-8")
            else:
                # treat path string as literal content
                text = path
            self.documents.append(Document(content=text, source=f"file:{path}", metadata={"path": str(path)}))

    def search(self, query: str) -> List[Document]:
        results: List[Document] = []
        query_terms = query.lower().split()
        for doc in self.documents:
            text_lower = doc.content.lower()
            if all(term in text_lower for term in query_terms):
                doc.score = sum(text_lower.count(term) for term in query_terms)
                results.append(doc)
        results.sort(key=lambda d: d.score or 0, reverse=True)
        return results


class APISource(BaseSource):
    """Retrieve data via a user supplied fetch function."""

    def __init__(self, fetch_func: Callable[[str], Any]):
        self.fetch_func = fetch_func

    def search(self, query: str) -> List[Document]:
        results: List[Document] = []
        data = self.fetch_func(query)
        if not data:
            return results
        if isinstance(data, Document):
            results.append(data)
        elif isinstance(data, str):
            if data.strip():
                results.append(Document(content=data, source="api"))
        elif isinstance(data, list):
            if data and isinstance(data[0], Document):
                results = data
            else:
                for item in data:
                    if isinstance(item, str) and item.strip():
                        results.append(Document(content=item, source="api"))
        elif isinstance(data, dict):
            text = str(data)
            if text.strip():
                results.append(Document(content=text, source="api"))
        return results


class DatabaseSource(BaseSource):
    """Retrieve from in-memory record list."""

    def __init__(self, records: List[Union[str, Document, dict]]):
        self.documents: List[Document] = []
        for rec in records:
            if isinstance(rec, Document):
                self.documents.append(rec)
            elif isinstance(rec, str):
                self.documents.append(Document(content=rec, source="db"))
            elif isinstance(rec, dict):
                text = rec.get("content") or rec.get("text")
                if text is None:
                    text = str(rec)
                self.documents.append(Document(content=text, source="db", metadata=rec))

    def search(self, query: str) -> List[Document]:
        results: List[Document] = []
        query_terms = query.lower().split()
        for doc in self.documents:
            text_lower = doc.content.lower()
            if all(term in text_lower for term in query_terms):
                doc.score = sum(text_lower.count(term) for term in query_terms)
                results.append(doc)
        results.sort(key=lambda d: d.score or 0, reverse=True)
        return results


class MultiSourceRetriever:
    """Combine multiple sources with negative filtering and deduplication."""

    def __init__(
        self,
        sources: Optional[List[BaseSource]] = None,
        negative_phrases: Optional[List[str]] = None,
        negative_texts: Optional[List[str]] = None,
        negative_threshold: float = 0.8,
        dedup_threshold: float = 0.9,
        similarity_func: Callable[[str, str], float] | None = None,
    ) -> None:
        self.sources = list(sources) if sources else []
        self.negative_phrases = [p.lower() for p in (negative_phrases or [])]
        self.negative_texts = negative_texts or []
        self.negative_threshold = negative_threshold
        self.dedup_threshold = dedup_threshold
        if similarity_func is None:
            self.similarity_func = lambda a, b: SequenceMatcher(None, a, b).ratio()
        else:
            self.similarity_func = similarity_func

    def add_source(self, source: BaseSource) -> None:
        self.sources.append(source)

    def index_all(self) -> None:
        for src in self.sources:
            if hasattr(src, "index") and callable(getattr(src, "index")):
                src.index()

    def _filter_negatives(self, docs: List[Document]) -> List[Document]:
        kept: List[Document] = []
        for d in docs:
            text_lower = d.content.lower()
            if any(p in text_lower for p in self.negative_phrases):
                continue
            skip = False
            for nt in self.negative_texts:
                if self.similarity_func(d.content, nt) >= self.negative_threshold:
                    skip = True
                    break
            if not skip:
                kept.append(d)
        return kept

    def _deduplicate(self, docs: List[Document]) -> List[Document]:
        unique: List[Document] = []
        for d in docs:
            dup = False
            for u in unique:
                if self.similarity_func(d.content, u.content) >= self.dedup_threshold:
                    dup = True
                    break
            if not dup:
                unique.append(d)
        return unique

    def retrieve(self, query: str, top_k: int | None = None) -> List[Document]:
        all_docs: List[Document] = []
        for src in self.sources:
            try:
                all_docs.extend(src.search(query))
            except Exception:
                continue
        filtered = self._filter_negatives(all_docs)
        deduped = self._deduplicate(filtered)
        deduped.sort(key=lambda d: d.score or 0, reverse=True)
        if top_k is not None:
            deduped = deduped[:top_k]
        return deduped
