import tempfile
from pathlib import Path

import chromadb
import pytest

from backend.knowledge.embedder import build_collection, get_or_build_collection
from backend.knowledge.loader import load_champion_snippets
from backend.knowledge.schemas import KnowledgeSnippet

DATA_DIR = Path("backend/knowledge/data")


def test_loader_returns_snippets():
    snippets = load_champion_snippets(DATA_DIR)
    assert len(snippets) > 0
    assert all(isinstance(s, KnowledgeSnippet) for s in snippets)


def test_loader_gameplan_source_format():
    snippets = load_champion_snippets(DATA_DIR)
    gameplan_sources = [s for s in snippets if "gameplan" in s.source]
    assert len(gameplan_sources) > 0
    for s in gameplan_sources:
        parts = s.source.split(":")
        assert parts[0] == "champion"
        assert parts[2] == "gameplan"


def test_loader_matchup_source_format():
    snippets = load_champion_snippets(DATA_DIR)
    matchup_sources = [s for s in snippets if "matchup" in s.source]
    assert len(matchup_sources) > 0
    for s in matchup_sources:
        parts = s.source.split(":")
        assert parts[0] == "champion"
        assert parts[2] == "matchup"
        assert len(parts) == 4


def test_loader_snippet_content_nonempty():
    snippets = load_champion_snippets(DATA_DIR)
    for s in snippets:
        assert s.content.strip() != ""


def test_loader_rumble_present():
    snippets = load_champion_snippets(DATA_DIR)
    sources = [s.source for s in snippets]
    assert any("rumble" in src for src in sources)


def test_loader_empty_dir_returns_empty(tmp_path):
    snippets = load_champion_snippets(tmp_path)
    assert snippets == []


def test_build_collection_returns_collection():
    snippets = load_champion_snippets(DATA_DIR)
    with tempfile.TemporaryDirectory() as tmp:
        collection = build_collection(snippets, Path(tmp))
        assert collection is not None


def test_build_collection_document_count():
    snippets = load_champion_snippets(DATA_DIR)
    with tempfile.TemporaryDirectory() as tmp:
        collection = build_collection(snippets, Path(tmp))
        count = collection.count()
        assert count == len(snippets)


def test_get_or_build_reuses_existing():
    snippets = load_champion_snippets(DATA_DIR)
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp)
        col1 = get_or_build_collection(DATA_DIR, db_path)
        col2 = get_or_build_collection(DATA_DIR, db_path)
        assert col1.count() == col2.count()


from backend.knowledge.retriever import retrieve


def _make_test_collection():
    snippets = load_champion_snippets(DATA_DIR)
    tmp = tempfile.mkdtemp()
    return build_collection(snippets, Path(tmp))


def test_retrieve_known_champion():
    col = _make_test_collection()
    snippets = retrieve("Rumble", "Darius", None, col, top_k=3)
    assert len(snippets) == 3
    assert all(isinstance(s, KnowledgeSnippet) for s in snippets)


def test_retrieve_returns_relevant_source():
    col = _make_test_collection()
    snippets = retrieve("Rumble", "Darius", None, col, top_k=3)
    sources = [s.source for s in snippets]
    assert any("rumble" in src or "darius" in src for src in sources)


def test_retrieve_unknown_champion_fallback():
    col = _make_test_collection()
    # "Yone" has no seed — should still return snippets via semantic fallback
    snippets = retrieve("Yone", "Malphite", None, col, top_k=3)
    assert len(snippets) == 3


def test_retrieve_no_opponents():
    col = _make_test_collection()
    snippets = retrieve("Ahri", None, None, col, top_k=3)
    assert len(snippets) == 3


def test_retrieve_with_fed_enemy():
    col = _make_test_collection()
    snippets = retrieve("Zed", "Ahri", "Jinx", col, top_k=3)
    assert len(snippets) == 3
