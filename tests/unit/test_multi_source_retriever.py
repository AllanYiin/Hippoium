from __future__ import annotations

import os

from hippoium.core.retriever import (
    APISource,
    DatabaseSource,
    Document,
    LocalFileSource,
    MultiSourceRetriever,
)


# prepare fixtures
FILE_PATH = "example.txt"
FILE_CONTENT = "Python is a programming language. It is widely used in AI and ML."


def setup_module(module):
    with open(FILE_PATH, "w", encoding="utf-8") as f:
        f.write(FILE_CONTENT)


def teardown_module(module):
    if os.path.exists(FILE_PATH):
        os.remove(FILE_PATH)


def dummy_api_fetch(query: str):
    if "history" in query.lower():
        return "Guido van Rossum created Python in the late 1980s."
    elif "python" in query.lower():
        return "Python was created by Guido van Rossum."
    return ""


DB_RECORDS = [
    "Python is great for data science.",
    "Python is a programming language widely used in AI.",
    "Java is another programming language.",
    {"id": 1, "content": "Machine learning uses Python."},
]


def build_retriever():
    local_source = LocalFileSource([FILE_PATH])
    api_source = APISource(dummy_api_fetch)
    db_source = DatabaseSource(DB_RECORDS)
    r = MultiSourceRetriever(
        sources=[local_source, api_source, db_source],
        negative_phrases=["java"],
        negative_texts=["Guido van Rossum"],
        negative_threshold=0.45,
        dedup_threshold=0.8,
    )
    r.index_all()
    return r


def test_sources_loaded():
    r = build_retriever()
    assert len(r.sources) == 3


def test_basic_retrieval_and_filters():
    r = build_retriever()

    # case A: dedup similar entries
    res_a = r.retrieve("Python programming")
    assert len(res_a) == 1
    assert res_a[0].source.startswith("file:")

    # case B: negative keyword filter removes Java sentence
    res_b = r.retrieve("programming language")
    assert all("java" not in d.content.lower() for d in res_b)
    assert len(res_b) >= 1

    # case C: negative text filter removes API result
    res_c = r.retrieve("Python history")
    assert res_c == []


def test_insert_into_ragtree():
    r = build_retriever()
    docs = r.retrieve("Python programming")

    class DummyRAGTree:
        def __init__(self):
            self.nodes = []

        def add_memory(self, doc: Document):
            self.nodes.append({"content": doc.content, "source": doc.source})

    tree = DummyRAGTree()
    for d in docs:
        tree.add_memory(d)

    assert len(tree.nodes) == len(docs)
    assert tree.nodes[0]["source"].startswith("file:")
