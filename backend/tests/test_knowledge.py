from pathlib import Path
import pytest
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
