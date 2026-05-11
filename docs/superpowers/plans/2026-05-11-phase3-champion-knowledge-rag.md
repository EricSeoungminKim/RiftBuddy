# Phase 3: Champion Knowledge RAG Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local RAG pipeline that embeds champion knowledge at startup and retrieves personalized snippets (gameplan + matchup tips) into the LLM prompt on every advice call.

**Architecture:** 10 seeded champion JSON files → `loader.py` flattens into `KnowledgeSnippet`s → `embedder.py` uses `sentence-transformers/all-MiniLM-L6-v2` + ChromaDB (persisted to `.chroma_db/`) → `retriever.py` does semantic search using champion name, lane opponent, and most-fed enemy from `GameState` → snippets injected into `ContextPacket.summary` before LLM call.

**Tech Stack:** `sentence-transformers>=2.7`, `chromadb>=0.5`, Python 3.13, pytest, existing `KnowledgeSnippet` dataclass

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `backend/knowledge/data/rumble.json` | Create | Seeded champion data |
| `backend/knowledge/data/garen.json` | Create | Seeded champion data |
| `backend/knowledge/data/darius.json` | Create | Seeded champion data |
| `backend/knowledge/data/jinx.json` | Create | Seeded champion data |
| `backend/knowledge/data/thresh.json` | Create | Seeded champion data |
| `backend/knowledge/data/leesin.json` | Create | Seeded champion data |
| `backend/knowledge/data/ahri.json` | Create | Seeded champion data |
| `backend/knowledge/data/zed.json` | Create | Seeded champion data |
| `backend/knowledge/data/yasuo.json` | Create | Seeded champion data |
| `backend/knowledge/data/vi.json` | Create | Seeded champion data |
| `backend/knowledge/loader.py` | Create | Load JSON → `list[KnowledgeSnippet]` |
| `backend/knowledge/embedder.py` | Create | Embed snippets → ChromaDB collection |
| `backend/knowledge/retriever.py` | Create | Query ChromaDB → top-3 snippets |
| `backend/riot/live_client.py` | Modify | Add `lane_opponent`, `fed_enemy` to `GameState` |
| `backend/main.py` | Modify | Init collection at startup, inject snippets in `send_advice()` |
| `backend/tests/test_knowledge.py` | Create | All knowledge layer tests |
| `requirements.txt` | Modify | Add `sentence-transformers`, `chromadb` |
| `.gitignore` | Modify | Ignore `.chroma_db/` |

---

## Task 1: Add dependencies and champion seed data

**Files:**
- Modify: `requirements.txt`
- Modify: `.gitignore`
- Create: `backend/knowledge/data/rumble.json` through `vi.json` (10 files)

- [ ] **Step 1: Add dependencies to requirements.txt**

Open `requirements.txt` and append:
```
sentence-transformers>=2.7
chromadb>=0.5
```

Final `requirements.txt`:
```
fastapi[standard]==0.128.0
uvicorn[standard]==0.46.0
httpx==0.28.1
anthropic==0.97.0
elevenlabs==2.45.0
openai-whisper==20250625
sounddevice==0.5.5
numpy==2.4.4
supabase==2.29.0
python-dotenv==1.2.2
pytest==9.0.3
pytest-asyncio==1.3.0
sentence-transformers>=2.7
chromadb>=0.5
```

- [ ] **Step 2: Install dependencies**

```bash
pip install sentence-transformers chromadb
```

Expected: packages install without error.

- [ ] **Step 3: Add .chroma_db/ to .gitignore**

Check if `.gitignore` exists at project root:
```bash
cat .gitignore 2>/dev/null || echo "no gitignore"
```

Add `.chroma_db/` to `.gitignore` (create the file if it doesn't exist):
```
.chroma_db/
```

- [ ] **Step 4: Create backend/knowledge/data/ directory**

```bash
mkdir -p backend/knowledge/data
```

- [ ] **Step 5: Create rumble.json**

Create `backend/knowledge/data/rumble.json`:
```json
{
  "champion": "rumble",
  "gameplan": {
    "summary": "Farm to 3 core items then become a teamfight monster. Avoid extended 1v1s vs tanks late.",
    "power_spikes": ["level 6 (Equalizer)", "Sunfire + Rylai's", "full build"],
    "win_condition": "Hit 5-man Equalizer in teamfights. Never split push.",
    "early_game": "Harass with E+Q. Don't overheat past 50% heat in trades. Trade short bursts.",
    "positioning": "Flank from fog of war for Equalizer. Never front-line into hard engage."
  },
  "matchups": {
    "darius": {
      "difficulty": "hard",
      "tips": "Never fight extended. Poke with Q from max range. Disengage immediately if he grabs you. Buy Ninja Tabi early.",
      "power_shift": "You outscale at 2 items. Survive laning phase and win through teamfights."
    },
    "garen": {
      "difficulty": "medium",
      "tips": "Poke freely with Q early. Respect his all-in at level 6. Kite backwards with E+Q combo.",
      "power_shift": "Even scaling. Win through teamfight Equalizer, not dueling."
    },
    "tryndamere": {
      "difficulty": "hard",
      "tips": "Poke with Q but never commit to a full trade — he wins extended. Keep ignite for his ult. Buy Thornmail.",
      "power_shift": "You win teamfights; he wins side lane. Force 5v5s."
    },
    "fiora": {
      "difficulty": "hard",
      "tips": "She parries your Q — bait the parry with E first, then Q. Never fight without heat advantage. Take Ghost.",
      "power_shift": "She outduels you all game. Win through teamfights, never 1v1 post-6."
    },
    "malphite": {
      "difficulty": "easy",
      "tips": "Freely poke with Q. He has no way to close the gap early. Stack heat slowly for consistent damage.",
      "power_shift": "Both want teamfights. You win if Equalizer hits; he wins if ult engages first."
    }
  }
}
```

- [ ] **Step 6: Create garen.json**

Create `backend/knowledge/data/garen.json`:
```json
{
  "champion": "garen",
  "gameplan": {
    "summary": "Bully early with Q-auto-W, scale into a frontline tank. Win through sustained fights and Villain execution.",
    "power_spikes": ["level 1-3 (Q bully)", "Stridebreaker", "full tank build"],
    "win_condition": "Split push and force 1v1s early. Teamfight as frontline tank with Judgment peel.",
    "early_game": "Q into auto with Decisive Strike. Max Q for max slow and silence duration.",
    "positioning": "Frontline in teamfights. Use W to reduce damage. Save Q for catching key targets."
  },
  "matchups": {
    "darius": {
      "difficulty": "hard",
      "tips": "Never let him stack bleed to 5. Short trades only — Q in and out. Buy Steelcaps + Stridebreaker rush.",
      "power_shift": "He wins extended trades all game. Win through split pushing when he's not nearby."
    },
    "teemo": {
      "difficulty": "hard",
      "tips": "His blind negates your Q auto. Rush MR item. Don't chase into his mushrooms. Freeze lane.",
      "power_shift": "He kites you forever. Win by roaming and taking objectives while he pushes."
    },
    "malphite": {
      "difficulty": "medium",
      "tips": "Long trade wins — Judgment melts him. Don't let him poke you down pre-6. Take Ignite.",
      "power_shift": "Even. Both are frontlines. Win via Stridebreaker to prevent him kiting."
    },
    "vayne": {
      "difficulty": "hard",
      "tips": "She shreds tanks with W passive. Pressure early before she scales. Force fights before 3 items.",
      "power_shift": "She wins 1v1 at 2+ items. Win through teamfights where her DPS is split."
    },
    "nasus": {
      "difficulty": "medium",
      "tips": "Deny his farm early with Q poke. Don't let him reach 300 stacks. Pressure him off minions constantly.",
      "power_shift": "He outscales at 400+ stacks. Win the game before 25 minutes."
    }
  }
}
```

- [ ] **Step 7: Create darius.json**

Create `backend/knowledge/data/darius.json`:
```json
{
  "champion": "darius",
  "gameplan": {
    "summary": "Win lane through bleed stacks and all-ins. Snowball kills into Noxian Might for free kills.",
    "power_spikes": ["level 3 (full combo)", "Stridebreaker", "Noxian Might active (5 stacks)"],
    "win_condition": "Stack bleed to 5 and execute with Noxus Guillotine. Dominate side lane.",
    "early_game": "Level 1 E to pull then Q heal. Level 3 is first kill window. Max Q.",
    "positioning": "Flank at choke points. Use E to pull isolated targets. Never fight without Tenacity vs CC."
  },
  "matchups": {
    "garen": {
      "difficulty": "medium",
      "tips": "He silences you — don't use E while silenced. Bait his W then commit. Win long trades.",
      "power_shift": "You win extended trades with bleed. Short trades favor Garen. Force long fights."
    },
    "fiora": {
      "difficulty": "hard",
      "tips": "She parries your E pull — never use E as opener. Bait parry with auto, then Q+E combo.",
      "power_shift": "She outduels you at 2+ items. Win via roaming and taking objectives."
    },
    "quinn": {
      "difficulty": "hard",
      "tips": "Her E knock-back cancels your pull. Rush Merc Treads. Freeze under tower and roam.",
      "power_shift": "She kites you all game. Win through splitpush when she's elsewhere."
    },
    "malphite": {
      "difficulty": "easy",
      "tips": "You shred his armor with passive. Free all-in at level 3. Ignite + full combo wins early.",
      "power_shift": "You win all stages of the game 1v1. Avoid his teamfight ult setup."
    },
    "rumble": {
      "difficulty": "medium",
      "tips": "Respect his Q poke at range. All-in when he's overheated. Use E pull to gap-close through his E slow.",
      "power_shift": "You win level 1-5. He outscales in teamfights. Win before he gets 2 items."
    }
  }
}
```

- [ ] **Step 8: Create jinx.json**

Create `backend/knowledge/data/jinx.json`:
```json
{
  "champion": "jinx",
  "gameplan": {
    "summary": "Scale safely to 3 items then hypercarry teamfights with Fishbones AoE. Never get caught alone.",
    "power_spikes": ["level 6 (Super Mega Death Rocket)", "Kraken Slayer + Runaan's", "full build"],
    "win_condition": "Stay safe in teamfights behind your frontline. Let Fishbones shred grouped enemies.",
    "early_game": "Farm safely with Minigun. Only poke with Fishbones when mana allows. Play for 3 items.",
    "positioning": "Extreme backline. Never walk up without peel. Use E traps to create distance from divers."
  },
  "matchups": {
    "caitlyn": {
      "difficulty": "hard",
      "tips": "She outranges you early. Farm under tower. Buy Vampiric Scepter to sustain her poke.",
      "power_shift": "You outscale at 3 items. Survive laning phase and win late teamfights."
    },
    "draven": {
      "difficulty": "hard",
      "tips": "He wins all early trades. Play for farm only. Don't fight without support CC to set up.",
      "power_shift": "Equal at 2 items. You win if game goes long — his lead fades without kills."
    },
    "jhin": {
      "difficulty": "medium",
      "tips": "Dodge his W root — it enables his full combo. Farm and scale. Buy early Vampiric Scepter.",
      "power_shift": "You outscale in teamfights. His damage spikes before yours."
    },
    "ezreal": {
      "difficulty": "easy",
      "tips": "He pokes you but won't all-in. Farm freely. He can't engage without Arcane Shift.",
      "power_shift": "You win sustained teamfights at 3 items. He falls off unless snowballed."
    },
    "zeri": {
      "difficulty": "medium",
      "tips": "She kites better than you. Play around your support CC. Don't chase her.",
      "power_shift": "Even at 3 items. Win through superior AoE in 5v5 teamfights."
    }
  }
}
```

- [ ] **Step 9: Create thresh.json**

Create `backend/knowledge/data/thresh.json`:
```json
{
  "champion": "thresh",
  "gameplan": {
    "summary": "Control lane with hook threats, stack souls for scaling, and carry with Lantern + Death Sentence combos.",
    "power_spikes": ["level 2 (Q+E combo)", "40 souls", "Locket + Knight's Vow"],
    "win_condition": "Create picks with Death Sentence then snowball. Peel for ADC in teamfights with Flay.",
    "early_game": "Level 1 Q hook onto overextended targets. Level 2 all-in with E slow. Always collect souls.",
    "positioning": "Roam constantly. Drop Lantern for teammates in danger. Save W for clutch plays."
  },
  "matchups": {
    "blitzcrank": {
      "difficulty": "medium",
      "tips": "Both want to hook first. Stand behind minions. If he hooks your ADC, E-slow him immediately.",
      "power_shift": "You outscale him in soul stacking. Win long games with superior kit utility."
    },
    "nautilus": {
      "difficulty": "medium",
      "tips": "His Q root is hard CC — don't stand near walls. Poke him before he engages.",
      "power_shift": "Both are engage supports. Win by landing Death Sentence before his Q."
    },
    "lulu": {
      "difficulty": "hard",
      "tips": "Her W polymorph stops your hook combo. Time Q when she wastes W on a minion.",
      "power_shift": "She outpokes you early. Win through roaming when she stays bot lane."
    },
    "soraka": {
      "difficulty": "easy",
      "tips": "Hook her freely — she has no mobility. Zone her from ADC so she can't heal. Ignite to counter Wish.",
      "power_shift": "You win all-ins with hook combos. She scales better if game goes past 30 min."
    },
    "leona": {
      "difficulty": "medium",
      "tips": "She has stronger burst CC at level 2. Play passive pre-6. Use Lantern to disengage her engage.",
      "power_shift": "Even. Both are engage supports. Win through superior roaming and picks."
    }
  }
}
```

- [ ] **Step 10: Create leesin.json**

Create `backend/knowledge/data/leesin.json`:
```json
{
  "champion": "leesin",
  "gameplan": {
    "summary": "Dominate early game with Q gank threat. Snowball kills before falling off at 3 items.",
    "power_spikes": ["level 3 (Q+E+W combo)", "Serpent's Fang", "early first back powerspike"],
    "win_condition": "Gank lanes early, get ahead, and use Insec kick in teamfights to displace carries.",
    "early_game": "Q → Q2 for execute. W to sustain. E to slow and shred armor. Invade enemy jungle at level 2.",
    "positioning": "Stay mobile. Insec kick: Q target, ward jump behind, R to kick into team."
  },
  "matchups": {
    "hecarim": {
      "difficulty": "medium",
      "tips": "He outduels you at level 6. Invade early before he scales. Take Ignite for duels.",
      "power_shift": "He outscales in sustained fights. Win through early ganks and objective control."
    },
    "vi": {
      "difficulty": "medium",
      "tips": "She has point-and-click CC. Don't fight her in her jungle at level 6. Invade at level 2.",
      "power_shift": "Even early. She scales better. Win through early snowball before 20 minutes."
    },
    "graves": {
      "difficulty": "hard",
      "tips": "He outduels you at all stages post level 3. Avoid 1v1s. Win through ganking while he farms.",
      "power_shift": "He wins all 1v1s. Win through superior ganks and objective setup."
    },
    "amumu": {
      "difficulty": "easy",
      "tips": "Invade him freely — he has no early dueling. Steal his camps. Counter-gank his ganks.",
      "power_shift": "You win early; he wins teamfights at 6. Shut him down before he gets ult."
    },
    "kindred": {
      "difficulty": "medium",
      "tips": "Contest her marks to deny stacks. Invade before she gets 4 marks. Don't fight inside her ult.",
      "power_shift": "She outscales at 4+ marks. Win before she reaches scaling threshold."
    }
  }
}
```

- [ ] **Step 11: Create ahri.json**

Create `backend/knowledge/data/ahri.json`:
```json
{
  "champion": "ahri",
  "gameplan": {
    "summary": "Roam after shoving waves and pick off isolated targets with charm. Scale into mobile assassin.",
    "power_spikes": ["level 6 (Spirit Rush roam)", "Luden's Tempest", "full build"],
    "win_condition": "Charm into full combo for picks. Never fight fair — use Spirit Rush to outmaneuver.",
    "early_game": "Q for waveclear and poke. E charm is your kill threat. Never use E defensively — save it for kills.",
    "positioning": "Flank from side in teamfights. Spirit Rush in, charm, combo, Spirit Rush out."
  },
  "matchups": {
    "leblanc": {
      "difficulty": "hard",
      "tips": "She bursts faster than you. Buy early MR (Verdant Barrier). Dodge her Q mark with dash. Never let her chain CC.",
      "power_shift": "Even at 2 items. Win through superior roaming — she's a solo lane bully, you're a roamer."
    },
    "zed": {
      "difficulty": "medium",
      "tips": "Charm him while he's in shadow form to stop combo. Buy Zhonya's — it counters his ult entirely.",
      "power_shift": "He wins without Zhonya's; you win with it. Build Zhonya's second item."
    },
    "yasuo": {
      "difficulty": "medium",
      "tips": "His Windwall blocks your Q and orb. Bait Windwall then engage with E charm. Play around his no-shield HP.",
      "power_shift": "He outduels at 2 items. Win through superior roaming and picking off squishy targets."
    },
    "viktor": {
      "difficulty": "medium",
      "tips": "Stay mobile to dodge his E gravity field — getting caught in it means full combo death. Roam frequently.",
      "power_shift": "He outscales in AoE teamfights. Win through picking off targets before 5v5s happen."
    },
    "syndra": {
      "difficulty": "hard",
      "tips": "She one-shots at level 9 with 7 orbs. Buy early MR. Dodge her E stun — it enables full combo.",
      "power_shift": "She outranges and outbursts you. Win by roaming constantly rather than fighting her."
    }
  }
}
```

- [ ] **Step 12: Create zed.json**

Create `backend/knowledge/data/zed.json`:
```json
{
  "champion": "zed",
  "gameplan": {
    "summary": "Assassinate squishy carries with W+R combo. Snowball kills before enemy builds armor.",
    "power_spikes": ["level 6 (Death Mark)", "Youmuu's + Serpent's Fang", "3 lethality items"],
    "win_condition": "One-shot the enemy ADC or APC in every teamfight. Use shadows for mobility escapes.",
    "early_game": "Q poke safely. Level 6 first kill window. Never waste W — it's your only escape.",
    "positioning": "Flank from fog of war. W behind enemy carries. Ult onto isolated target, never into frontline."
  },
  "matchups": {
    "ahri": {
      "difficulty": "medium",
      "tips": "She charms you during ult — walk unpredictably. She will buy Zhonya's; plan around it.",
      "power_shift": "You win if she's behind. Even matchup with Zhonya's in play."
    },
    "lissandra": {
      "difficulty": "hard",
      "tips": "Her ult counters your Death Mark entirely — she ults herself to negate it. Delay ult until her ult is down.",
      "power_shift": "She hard-counters you. Win through roaming to other lanes rather than fighting her."
    },
    "malzahar": {
      "difficulty": "hard",
      "tips": "His E silence stops your combo. His ult suppresses you — build QSS. Avoid extended fights.",
      "power_shift": "He counters your kit. Win by roaming aggressively and avoiding him."
    },
    "orianna": {
      "difficulty": "medium",
      "tips": "Dodge her Q-W poke. Shadow jump her and kill before she can get ball protection from teammates.",
      "power_shift": "You win 1v1 early. She wins teamfights at 3 items. Kill her before 20 minutes."
    },
    "katarina": {
      "difficulty": "medium",
      "tips": "Both are all-in assassins — fight for level 6 first kill. Don't let her reset daggers.",
      "power_shift": "She outscales in teamfights with resets. Win through solo kills before she gets 2 items."
    }
  }
}
```

- [ ] **Step 13: Create yasuo.json**

Create `backend/knowledge/data/yasuo.json`:
```json
{
  "champion": "yasuo",
  "gameplan": {
    "summary": "Scale into an unstoppable carry with knockup combos and unlimited Windwall. Win through mobility.",
    "power_spikes": ["level 3 (Q tornado)", "Immortal Shieldbow + Infinity Edge", "full build"],
    "win_condition": "Set up Last Breath combos with allied knockups. Dash through minions to avoid skillshots.",
    "early_game": "Q stack tornado poke. E through minions aggressively. Shield absorbs one hit — trade into it.",
    "positioning": "Dash to backline in teamfights. Never stand still — constant E dashing makes you impossible to hit."
  },
  "matchups": {
    "malphite": {
      "difficulty": "hard",
      "tips": "He hard-counters you — armor passive, point-and-click ult. Rush Wit's End for MR and on-hit. Farm and roam.",
      "power_shift": "He wins 1v1 all game. Win by roaming to other lanes and avoiding him entirely."
    },
    "pantheon": {
      "difficulty": "hard",
      "tips": "His E blocks your Q. Never dash to him — he blocks it. Poke with tornado at max range only.",
      "power_shift": "He wins early hard. You outscale at 3 items if you survived laning phase."
    },
    "annie": {
      "difficulty": "medium",
      "tips": "Windwall her Q and W. Always track her stun count — if she has 4 stacks, disengage immediately.",
      "power_shift": "You outscale at 2 items. Win by Windwalling her burst and outlasting her damage."
    },
    "zed": {
      "difficulty": "medium",
      "tips": "Windwall his Q poke. Time W shadow to avoid his ult. Buy Verdant Barrier early.",
      "power_shift": "He wins early; you win at 2 items with shield. Equal matchup with Shieldbow rush."
    },
    "akali": {
      "difficulty": "medium",
      "tips": "Never dash into her shroud — she all-ins you there. Poke with tornado. Save E dash for escape not engage.",
      "power_shift": "Even. She outbursts; you outscale in sustained fights. Win via teamfight mobility."
    }
  }
}
```

- [ ] **Step 14: Create vi.json**

Create `backend/knowledge/data/vi.json`:
```json
{
  "champion": "vi",
  "gameplan": {
    "summary": "Gank with point-and-click ult lockdown and snowball carries. Transition into frontline bruiser.",
    "power_spikes": ["level 6 (Assault and Battery)", "Trinity Force", "full bruiser build"],
    "win_condition": "Ult the enemy carry in every teamfight. Use W armor shred to enable your team.",
    "early_game": "Q gap-close for early ganks level 3. E W passive gives strong dueling. Farm to 6 fast.",
    "positioning": "Initiate with ult on carry. Peel with Q for your own carries after initial engage."
  },
  "matchups": {
    "leesin": {
      "difficulty": "medium",
      "tips": "He outduels you before level 6. Avoid early invade. After 6 your ult wins all duels.",
      "power_shift": "You win post-6 duels. He wins early jungle. Get ahead through ganking not dueling."
    },
    "hecarim": {
      "difficulty": "hard",
      "tips": "He outduels you and out-ganks you pre-6. Avoid early fights. Counter-gank his ganks.",
      "power_shift": "He scales better. Win by targeting lanes he ignores and taking objectives."
    },
    "warwick": {
      "difficulty": "medium",
      "tips": "His ult suppresses you — don't duel near low-HP allies. Invade at level 2 before he heals up.",
      "power_shift": "Even. He sustains better; you engage better. Win through ganking over dueling."
    },
    "diana": {
      "difficulty": "medium",
      "tips": "She outduels you post-6 in extended fights. Gank faster and earlier before she stabilizes.",
      "power_shift": "You win through pick potential on carries. She wins 1v1 sustained fights."
    },
    "graves": {
      "difficulty": "hard",
      "tips": "He wins all duels at all stages. Never fight him 1v1 in his jungle. Win through superior ganks.",
      "power_shift": "He wins duels; you win teamfights. Avoid him and target laners."
    }
  }
}
```

- [ ] **Step 15: Commit seed data and dependencies**

```bash
git add requirements.txt .gitignore backend/knowledge/data/
git commit -m "feat(knowledge): add 10 seeded champion JSON files and RAG dependencies"
```

---

## Task 2: Implement KnowledgeLoader

**Files:**
- Create: `backend/knowledge/loader.py`
- Create: `backend/tests/test_knowledge.py` (partial — loader tests only)

The `KnowledgeSnippet` dataclass already exists in `backend/knowledge/schemas.py`:
```python
@dataclass
class KnowledgeSnippet:
    source: str    # e.g. "champion:rumble:gameplan"
    content: str   # text injected into LLM context
    relevance: str # "high" or "medium"
```

- [ ] **Step 1: Write failing loader tests**

Create `backend/tests/test_knowledge.py`:
```python
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
    # source format: "champion:rumble:gameplan"
    for s in gameplan_sources:
        parts = s.source.split(":")
        assert parts[0] == "champion"
        assert parts[2] == "gameplan"


def test_loader_matchup_source_format():
    snippets = load_champion_snippets(DATA_DIR)
    matchup_sources = [s for s in snippets if "matchup" in s.source]
    assert len(matchup_sources) > 0
    # source format: "champion:rumble:matchup:darius"
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest backend/tests/test_knowledge.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'backend.knowledge.loader'`

- [ ] **Step 3: Implement loader.py**

Create `backend/knowledge/loader.py`:
```python
import json
from pathlib import Path

from backend.knowledge.schemas import KnowledgeSnippet


def load_champion_snippets(data_dir: Path) -> list[KnowledgeSnippet]:
    snippets: list[KnowledgeSnippet] = []
    for json_file in sorted(data_dir.glob("*.json")):
        data = json.loads(json_file.read_text(encoding="utf-8"))
        champion = data["champion"]
        gp = data["gameplan"]
        gameplan_text = (
            f"Gameplan: {gp['summary']} "
            f"Power spikes: {', '.join(gp['power_spikes'])}. "
            f"Win condition: {gp['win_condition']} "
            f"Early game: {gp['early_game']} "
            f"Positioning: {gp['positioning']}"
        )
        snippets.append(KnowledgeSnippet(
            source=f"champion:{champion}:gameplan",
            content=gameplan_text,
            relevance="high",
        ))
        for enemy, matchup in data.get("matchups", {}).items():
            matchup_text = (
                f"Matchup vs {enemy} (difficulty: {matchup['difficulty']}): "
                f"{matchup['tips']} "
                f"Power shift: {matchup['power_shift']}"
            )
            snippets.append(KnowledgeSnippet(
                source=f"champion:{champion}:matchup:{enemy}",
                content=matchup_text,
                relevance="high",
            ))
    return snippets
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest backend/tests/test_knowledge.py -v
```

Expected: 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/knowledge/loader.py backend/tests/test_knowledge.py
git commit -m "feat(knowledge): implement KnowledgeLoader with TDD"
```

---

## Task 3: Implement Embedder (ChromaDB + sentence-transformers)

**Files:**
- Create: `backend/knowledge/embedder.py`
- Modify: `backend/tests/test_knowledge.py` (add embedder tests)

- [ ] **Step 1: Add failing embedder tests**

Append to `backend/tests/test_knowledge.py`:
```python
import tempfile
from backend.knowledge.embedder import build_collection, get_or_build_collection
import chromadb


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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest backend/tests/test_knowledge.py::test_build_collection_returns_collection -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'backend.knowledge.embedder'`

- [ ] **Step 3: Implement embedder.py**

Create `backend/knowledge/embedder.py`:
```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest backend/tests/test_knowledge.py -v
```

Expected: 8 tests PASS. Note: first run downloads `all-MiniLM-L6-v2` model (~80MB) — this is expected.

- [ ] **Step 5: Commit**

```bash
git add backend/knowledge/embedder.py backend/tests/test_knowledge.py
git commit -m "feat(knowledge): implement ChromaDB embedder with sentence-transformers"
```

---

## Task 4: Implement Retriever

**Files:**
- Create: `backend/knowledge/retriever.py`
- Modify: `backend/tests/test_knowledge.py` (add retriever tests)

- [ ] **Step 1: Add failing retriever tests**

Append to `backend/tests/test_knowledge.py`:
```python
import tempfile
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
    # At least one snippet should relate to rumble or darius
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest backend/tests/test_knowledge.py::test_retrieve_known_champion -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'backend.knowledge.retriever'`

- [ ] **Step 3: Implement retriever.py**

Create `backend/knowledge/retriever.py`:
```python
import chromadb

from backend.knowledge.schemas import KnowledgeSnippet


def retrieve(
    champion: str,
    lane_opponent: str | None,
    fed_enemy: str | None,
    collection: chromadb.Collection,
    top_k: int = 3,
) -> list[KnowledgeSnippet]:
    query = _build_query(champion, lane_opponent, fed_enemy)
    results = collection.query(query_texts=[query], n_results=top_k)
    snippets: list[KnowledgeSnippet] = []
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        snippets.append(KnowledgeSnippet(
            source=meta["source"],
            content=doc,
            relevance=meta.get("relevance", "medium"),
        ))
    return snippets


def _build_query(champion: str, lane_opponent: str | None, fed_enemy: str | None) -> str:
    parts = [f"{champion} gameplan win condition early game"]
    if lane_opponent:
        parts.append(f"matchup against {lane_opponent} tips")
    if fed_enemy:
        parts.append(f"most fed enemy {fed_enemy} how to play against")
    return " ".join(parts)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest backend/tests/test_knowledge.py -v
```

Expected: 13 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/knowledge/retriever.py backend/tests/test_knowledge.py
git commit -m "feat(knowledge): implement semantic retriever with fallback query"
```

---

## Task 5: Add lane_opponent and fed_enemy to GameState

**Files:**
- Modify: `backend/riot/live_client.py`

Current `GameState` (frozen dataclass) is at line 13. `fetch_game_state()` builds it at line 77. `_find_active_player()` at line 119. `_extract_champion_groups()` at line 156.

- [ ] **Step 1: Write failing tests for new GameState fields**

Append to `backend/tests/test_knowledge.py`:
```python
from backend.riot.live_client import (
    GameState, get_fake_game_state,
    _infer_lane_opponent, _infer_fed_enemy,
)


def test_fake_game_state_has_lane_opponent():
    state = get_fake_game_state()
    assert state.lane_opponent is not None
    assert isinstance(state.lane_opponent, str)


def test_fake_game_state_has_fed_enemy():
    state = get_fake_game_state()
    # fed_enemy can be None (all 0 kills) or a string
    assert state.fed_enemy is None or isinstance(state.fed_enemy, str)


def test_infer_lane_opponent_top():
    data = {
        "allPlayers": [
            {"championName": "Rumble", "team": "ORDER", "position": "TOP"},
            {"championName": "Darius", "team": "CHAOS", "position": "TOP"},
            {"championName": "Jinx", "team": "CHAOS", "position": "BOTTOM"},
        ]
    }
    active_player = {"team": "ORDER", "position": "TOP"}
    result = _infer_lane_opponent(data, active_player)
    assert result == "Darius"


def test_infer_lane_opponent_no_match():
    data = {
        "allPlayers": [
            {"championName": "Rumble", "team": "ORDER", "position": "TOP"},
            {"championName": "Jinx", "team": "CHAOS", "position": "BOTTOM"},
        ]
    }
    active_player = {"team": "ORDER", "position": "TOP"}
    result = _infer_lane_opponent(data, active_player)
    assert result is None


def test_infer_fed_enemy_returns_highest_kills():
    data = {
        "allPlayers": [
            {"championName": "Rumble", "team": "ORDER", "scores": {"kills": 3}},
            {"championName": "Darius", "team": "CHAOS", "scores": {"kills": 5}},
            {"championName": "Jinx", "team": "CHAOS", "scores": {"kills": 2}},
        ]
    }
    active_player = {"team": "ORDER"}
    result = _infer_fed_enemy(data, active_player)
    assert result == "Darius"


def test_infer_fed_enemy_all_zero_returns_none():
    data = {
        "allPlayers": [
            {"championName": "Rumble", "team": "ORDER", "scores": {"kills": 0}},
            {"championName": "Darius", "team": "CHAOS", "scores": {"kills": 0}},
        ]
    }
    active_player = {"team": "ORDER"}
    result = _infer_fed_enemy(data, active_player)
    assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest backend/tests/test_knowledge.py::test_fake_game_state_has_lane_opponent backend/tests/test_knowledge.py::test_infer_lane_opponent_top -v
```

Expected: FAIL with `ImportError: cannot import name '_infer_lane_opponent'`

- [ ] **Step 3: Add lane_opponent and fed_enemy fields to GameState**

In `backend/riot/live_client.py`, add two fields to the `GameState` dataclass after line 38 (`recent_events` field):

```python
    lane_opponent: str | None = None
    fed_enemy: str | None = None
```

- [ ] **Step 4: Add _infer_lane_opponent helper**

Add this function after `_find_active_player` (after line 125):

```python
def _infer_lane_opponent(data: dict, active_player: dict) -> str | None:
    active_team = active_player.get("team")
    active_position = active_player.get("position", "").upper()
    if not active_team or not active_position:
        return None
    for player in data.get("allPlayers", []):
        if player.get("team") == active_team:
            continue
        if player.get("position", "").upper() == active_position:
            return player.get("championName")
    return None


def _infer_fed_enemy(data: dict, active_player: dict) -> str | None:
    active_team = active_player.get("team")
    best_name: str | None = None
    best_kills = 0
    for player in data.get("allPlayers", []):
        if player.get("team") == active_team:
            continue
        kills = player.get("scores", {}).get("kills", 0) or 0
        if kills > best_kills:
            best_kills = kills
            best_name = player.get("championName")
    return best_name if best_kills > 0 else None
```

- [ ] **Step 5: Wire into fetch_game_state()**

In `fetch_game_state()`, add the two new fields to the `GameState(...)` constructor call (after `recent_events=_extract_recent_events(data),`):

```python
            lane_opponent=_infer_lane_opponent(data, active_player),
            fed_enemy=_infer_fed_enemy(data, active_player),
```

- [ ] **Step 6: Update get_fake_game_state()**

Add to the `GameState(...)` in `get_fake_game_state()` (after `recent_events=...`):

```python
        lane_opponent="Tryndamere",
        fed_enemy="Darius",
```

- [ ] **Step 7: Run tests to verify they pass**

```bash
pytest backend/tests/test_knowledge.py -v
```

Expected: 19 tests PASS.

- [ ] **Step 8: Run full test suite to check for regressions**

```bash
pytest backend/tests/ --ignore=backend/tests/test_voice.py -v
```

Expected: all existing tests still PASS.

- [ ] **Step 9: Commit**

```bash
git add backend/riot/live_client.py backend/tests/test_knowledge.py
git commit -m "feat(live_client): add lane_opponent and fed_enemy to GameState"
```

---

## Task 6: Wire knowledge retriever into main.py

**Files:**
- Modify: `backend/main.py`
- Modify: `backend/tests/test_knowledge.py` (add end-to-end test)

- [ ] **Step 1: Add end-to-end test**

Append to `backend/tests/test_knowledge.py`:
```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


def test_knowledge_snippets_injected_into_context(tmp_path):
    """Verify that knowledge snippets appear in the LLM prompt during send_advice."""
    from backend.knowledge.embedder import build_collection
    from backend.knowledge.loader import load_champion_snippets

    snippets = load_champion_snippets(DATA_DIR)
    collection = build_collection(snippets, tmp_path)

    captured_packets = []

    async def fake_get_advice(packet, **kwargs):
        captured_packets.append(packet)
        return "test advice"

    from backend.riot.live_client import get_fake_game_state
    fake_state = get_fake_game_state()

    with patch("backend.main._knowledge_collection", collection), \
         patch("backend.main.fetch_game_state", AsyncMock(return_value=fake_state)), \
         patch("backend.main.get_advice", fake_get_advice), \
         patch("backend.main.text_to_speech_bytes", AsyncMock(return_value=b"")):
        from backend.main import app
        client = TestClient(app)
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"action": "advice"})
            ws.receive_json()  # advice response

    assert len(captured_packets) == 1
    assert "[KNOWLEDGE]" in captured_packets[0].summary
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest backend/tests/test_knowledge.py::test_knowledge_snippets_injected_into_context -v
```

Expected: FAIL (no `_knowledge_collection` in main yet or `[KNOWLEDGE]` not in summary).

- [ ] **Step 3: Add imports to main.py**

In `backend/main.py`, after the existing imports add:

```python
from pathlib import Path
from backend.knowledge.embedder import get_or_build_collection
from backend.knowledge.retriever import retrieve
from backend.context.engine import ContextPacket
```

- [ ] **Step 4: Initialize knowledge collection at module level**

In `backend/main.py`, after the `_event_pipeline = ...` block (after line 45), add:

```python
_knowledge_collection = get_or_build_collection(
    data_dir=Path("backend/knowledge/data"),
    db_path=Path(".chroma_db"),
)
```

- [ ] **Step 5: Inject knowledge snippets in send_advice()**

In `backend/main.py`, in `send_advice()`, after the line `packet = enrich_summary_with_events(packet, detected_events)` (line 226), add:

```python
    knowledge_snippets = retrieve(
        champion=game_state.champion_name,
        lane_opponent=game_state.lane_opponent,
        fed_enemy=game_state.fed_enemy,
        collection=_knowledge_collection,
    )
    if knowledge_snippets:
        knowledge_block = "\n".join(
            f"[KNOWLEDGE] {s.source}: {s.content}" for s in knowledge_snippets
        )
        packet = ContextPacket(
            health_percent=packet.health_percent,
            gold=packet.gold,
            level=packet.level,
            game_time_minutes=packet.game_time_minutes,
            summary=f"{knowledge_block}\n\n{packet.summary}",
            champion_name=packet.champion_name,
            assigned_position=packet.assigned_position,
            creep_score=packet.creep_score,
        )
```

- [ ] **Step 6: Run all tests**

```bash
pytest backend/tests/ --ignore=backend/tests/test_voice.py -v
```

Expected: all tests PASS including the new end-to-end test.

- [ ] **Step 7: Commit**

```bash
git add backend/main.py backend/tests/test_knowledge.py
git commit -m "feat(main): wire knowledge retriever into send_advice pipeline"
```

---

## Task 7: Smoke test end-to-end without live game

**Files:** No code changes — verification only.

- [ ] **Step 1: Run full test suite**

```bash
RIFTBUDDY_TEST_MODE=1 pytest backend/tests/ --ignore=backend/tests/test_voice.py -v
```

Expected: all tests PASS.

- [ ] **Step 2: Verify knowledge block in fake advice response**

```bash
RIFTBUDDY_TEST_MODE=1 LLM_PROVIDER=mock python -c "
import asyncio
from pathlib import Path
from backend.riot.live_client import get_fake_game_state
from backend.context.engine import build_context_packet, enrich_summary_with_events
from backend.timeline.event_detector import EventDetectorPipeline
from backend.timeline.detectors.low_health import LowHealthDetector
from backend.timeline.detectors.gold_spike import GoldSpikeDetector
from backend.knowledge.embedder import get_or_build_collection
from backend.knowledge.retriever import retrieve
from backend.context.engine import ContextPacket

state = get_fake_game_state()
packet = build_context_packet(state)

collection = get_or_build_collection(
    Path('backend/knowledge/data'),
    Path('.chroma_db'),
)
snippets = retrieve(state.champion_name, state.lane_opponent, state.fed_enemy, collection)
print(f'Retrieved {len(snippets)} snippets:')
for s in snippets:
    print(f'  [{s.relevance}] {s.source}')
    print(f'  {s.content[:80]}...')
    print()
"
```

Expected output:
```
Retrieved 3 snippets:
  [high] champion:rumble:gameplan
  Farm to 3 core items then become a teamfight monster...

  [high] champion:rumble:matchup:tryndamere
  Matchup vs tryndamere (difficulty: hard)...

  [high] champion:darius:matchup:rumble
  ...
```

- [ ] **Step 3: Commit smoke test results as a note (optional)**

If everything looks good, tag the milestone:

```bash
git tag phase3-complete
```

---

## Self-Review

**Spec coverage:**
- ✅ 10 seeded champion JSON files (Task 1)
- ✅ `loader.py` with `champion:X:gameplan` / `champion:X:matchup:Y` source format (Task 2)
- ✅ `embedder.py` with `all-MiniLM-L6-v2` + ChromaDB persistence (Task 3)
- ✅ `retriever.py` with semantic query + fallback for missing champions (Task 4)
- ✅ `GameState.lane_opponent` + `GameState.fed_enemy` fields (Task 5)
- ✅ `_infer_lane_opponent` + `_infer_fed_enemy` helpers (Task 5)
- ✅ `get_fake_game_state()` updated with new fields (Task 5)
- ✅ `main.py` wired with collection init + snippet injection (Task 6)
- ✅ `.chroma_db/` gitignored (Task 1)
- ✅ `requirements.txt` updated (Task 1)
- ✅ End-to-end smoke test (Task 7)

**Placeholder scan:** None found.

**Type consistency:** `KnowledgeSnippet` used consistently across loader, embedder, retriever, and main. `chromadb.Collection` type matches across embedder and retriever. `ContextPacket` reconstruction in Task 6 matches the same pattern used in `enrich_summary_with_events`.
