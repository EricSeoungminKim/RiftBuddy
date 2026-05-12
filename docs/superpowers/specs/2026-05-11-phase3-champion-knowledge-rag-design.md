# Phase 3: Champion Knowledge RAG — Design Spec

**Date:** 2026-05-11
**Status:** Approved

---

## Goal

At draft time, embed champion knowledge into a local ChromaDB vector store using sentence-transformers (zero API cost). During the game, retrieve the 3 most relevant `KnowledgeSnippet`s based on the player's current champion, lane opponent, and most-fed enemy — injected into the LLM prompt before every advice call.

---

## Architecture

```
Draft / First Startup
─────────────────────────────────────────
JSON files in backend/knowledge/data/
        ↓
KnowledgeLoader → list[KnowledgeSnippet]
        ↓
Embedder (all-MiniLM-L6-v2)
        ↓
ChromaDB (persisted to .chroma_db/)

Game Phase (every advice call)
─────────────────────────────────────────
GameState.champion_name
GameState.lane_opponent       ← new field
GameState.fed_enemy           ← new field
        ↓
Retriever builds query string
        ↓
ChromaDB semantic search → top-3 snippets
        ↓
KnowledgeSnippets injected into ContextPacket summary
        ↓
LLM prompt
```

---

## Data Schema

Each champion file lives at `backend/knowledge/data/{champion_name}.json` (lowercase, no spaces).

```json
{
  "champion": "rumble",
  "gameplan": {
    "summary": "Farm to 3 core items, then become a teamfight monster. Avoid extended 1v1s vs tanks late.",
    "power_spikes": ["level 6 (Equalizer)", "Sunfire + Rylai's", "full build"],
    "win_condition": "Hit 5-man Equalizer in teamfights. Never split push.",
    "early_game": "Harass with E+Q. Don't overheat. Trade short, not extended.",
    "positioning": "Flank from fog of war for Equalizer. Never front-line."
  },
  "matchups": {
    "darius": {
      "difficulty": "hard",
      "tips": "Never fight extended. Poke with Q from max range. Disengage if he pulls you.",
      "power_shift": "You outscale at 2 items. Survive laning phase."
    }
  }
}
```

**10 seeded champions:** rumble, garen, darius, jinx, thresh, leesin, ahri, zed, yasuo, vi

Each champion has:

- Full `gameplan` block (summary, power_spikes, win_condition, early_game, positioning)
- 4–6 `matchups` entries covering common lane opponents

---

## Components

### `backend/knowledge/loader.py`

Reads all JSON files from `data/`, flattens into a list of `KnowledgeSnippet`s.

Each snippet gets a `source` tag:

- `"champion:rumble:gameplan"` — for gameplan content
- `"champion:rumble:matchup:darius"` — for matchup-specific tips

```python
def load_champion_snippets(data_dir: Path) -> list[KnowledgeSnippet]:
    ...
```

### `backend/knowledge/embedder.py`

Embeds snippets using `sentence-transformers` model `all-MiniLM-L6-v2` (80MB, CPU-fast, no API cost). Persists to ChromaDB at `.chroma_db/` in the project root.

```python
def get_or_build_collection(data_dir: Path, db_path: Path) -> chromadb.Collection:
    # Returns existing collection if already built, builds and persists if not
    ...

def build_collection(snippets: list[KnowledgeSnippet], db_path: Path) -> chromadb.Collection:
    # Embeds all snippets and stores in ChromaDB
    ...
```

Called once at app startup (or draft time). If the collection already exists on disk, skip re-embedding.

### `backend/knowledge/retriever.py`

Builds a natural language query from game state, runs semantic search, returns top-3 `KnowledgeSnippet`s.

```python
def retrieve(
    champion: str,
    lane_opponent: str | None,
    fed_enemy: str | None,
    collection: chromadb.Collection,
    top_k: int = 3,
) -> list[KnowledgeSnippet]:
    ...
```

**Query construction:**

- If lane_opponent and fed_enemy known:
  `"Rumble top lane gameplan against Darius. Most fed enemy: Jinx."`
- If only champion known (no seed exists for opponents):
  `"Rumble top lane gameplan and win condition."`
- **Fallback (no seed for champion):** query without champion name:
  `"top lane gameplan against Darius. Most fed enemy: Jinx."` — semantic search returns whatever is most contextually similar

### `backend/riot/live_client.py` — changes

Add two new fields to `GameState`:

```python
lane_opponent: str | None = None   # enemy champion in same lane position
fed_enemy: str | None = None       # enemy champion with most kills this game
```

Add two extraction helpers:

```python
def _infer_lane_opponent(data: dict, active_player: dict) -> str | None:
    # Match active player's assigned_position against enemy players' positions
    # Returns champion name of enemy in same position, or None

def _infer_fed_enemy(data: dict, active_player: dict) -> str | None:
    # Iterate allPlayers, filter to enemy team, return champion with highest kills
    # Returns None if all enemies have 0 kills
```

Both helpers read from `allPlayers[].position` and `allPlayers[].scores.kills` — already present in the Live Client API `/allgamedata` response.

Update `get_fake_game_state()` to include:

```python
lane_opponent="Tryndamere",
fed_enemy="Darius",
```

### `backend/main.py` — changes

Initialize knowledge collection at startup:

```python
_knowledge_collection = get_or_build_collection(
    data_dir=Path("backend/knowledge/data"),
    db_path=Path(".chroma_db"),
)
```

Wire retriever into `send_advice()` after building context packet:

```python
snippets = retrieve(
    champion=game_state.champion_name,
    lane_opponent=game_state.lane_opponent,
    fed_enemy=game_state.fed_enemy,
    collection=_knowledge_collection,
)
if snippets:
    knowledge_block = "\n".join(f"[KNOWLEDGE] {s.source}: {s.content}" for s in snippets)
    packet = ContextPacket(
        **{f: getattr(packet, f) for f in packet.__dataclass_fields__ if f != "summary"},
        summary=f"{knowledge_block}\n\n{packet.summary}",
    )
```

---

## Tech Stack

| Library                 | Version | Purpose                                    |
| ----------------------- | ------- | ------------------------------------------ |
| `sentence-transformers` | >=2.7   | Local embeddings, `all-MiniLM-L6-v2` model |
| `chromadb`              | >=0.5   | Local persistent vector store              |

Both are zero-cost, CPU-compatible, no API key required.

---

## Testing

All tests run without a live game (fake game state).

### `backend/tests/test_knowledge.py`

| Test                                       | What it verifies                                                         |
| ------------------------------------------ | ------------------------------------------------------------------------ |
| `test_loader_returns_snippets`             | loader returns non-empty list from data dir                              |
| `test_loader_snippet_sources`              | source tags follow `champion:X:gameplan` / `champion:X:matchup:Y` format |
| `test_build_collection`                    | collection builds without error, contains expected doc count             |
| `test_retrieve_known_champion`             | returns 3 snippets for Rumble vs Darius                                  |
| `test_retrieve_unknown_champion_fallback`  | returns snippets even when champion has no seed                          |
| `test_retrieve_no_opponents`               | returns snippets for champion-only query                                 |
| `test_lane_opponent_extraction`            | `_infer_lane_opponent` returns correct enemy for TOP position            |
| `test_fed_enemy_extraction`                | `_infer_fed_enemy` returns enemy with highest kills                      |
| `test_fed_enemy_all_zero`                  | returns None when all enemies have 0 kills                               |
| `test_main_send_advice_includes_knowledge` | end-to-end: knowledge block appears in LLM prompt                        |

### Smoke test (no live game)

```bash
RIFTBUDDY_TEST_MODE=1 python -m backend.main
# POST /advice with fake game state
# Response should include knowledge context for Rumble
```

---

## File Structure

```
backend/
  knowledge/
    __init__.py          (exists)
    schemas.py           (exists, no changes)
    loader.py            (create)
    embedder.py          (create)
    retriever.py         (create)
    data/
      rumble.json        (create)
      garen.json         (create)
      darius.json        (create)
      jinx.json          (create)
      thresh.json        (create)
      leesin.json        (create)
      ahri.json          (create)
      zed.json           (create)
      yasuo.json         (create)
      vi.json            (create)
  riot/
    live_client.py       (modify — add lane_opponent, fed_enemy fields)
  main.py                (modify — wire knowledge retriever)
  tests/
    test_knowledge.py    (create)
.chroma_db/              (auto-generated, gitignored)
requirements.txt         (modify — add sentence-transformers, chromadb)
```

---

## Out of Scope (Phase 3.5)

- Post-game data collection and performance memory
- Auto-generated seeds from personal match history
- SQLite performance tracking per matchup
- Seed auto-update from accumulated game data
