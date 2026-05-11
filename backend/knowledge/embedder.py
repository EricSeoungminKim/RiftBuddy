from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from backend.knowledge.loader import load_champion_snippets
from backend.knowledge.schemas import KnowledgeSnippet

_COLLECTION_NAME = "riftbuddy_knowledge"
_MODEL_NAME = "all-MiniLM-L6-v2"


def build_collection(snippets: list[KnowledgeSnippet], db_path: Path) -> chromadb.Collection:
    client = chromadb.PersistentClient(path=str(db_path))
    ef = SentenceTransformerEmbeddingFunction(model_name=_MODEL_NAME)
    collection = client.get_or_create_collection(
        name=_COLLECTION_NAME,
        embedding_function=ef,
    )
    if collection.count() == 0:
        collection.add(
            ids=[s.source for s in snippets],
            documents=[s.content for s in snippets],
            metadatas=[{"source": s.source, "relevance": s.relevance} for s in snippets],
        )
    return collection


def get_or_build_collection(data_dir: Path, db_path: Path) -> chromadb.Collection:
    client = chromadb.PersistentClient(path=str(db_path))
    ef = SentenceTransformerEmbeddingFunction(model_name=_MODEL_NAME)
    collection = client.get_or_create_collection(
        name=_COLLECTION_NAME,
        embedding_function=ef,
    )
    if collection.count() == 0:
        snippets = load_champion_snippets(data_dir)
        collection.add(
            ids=[s.source for s in snippets],
            documents=[s.content for s in snippets],
            metadatas=[{"source": s.source, "relevance": s.relevance} for s in snippets],
        )
    return collection
