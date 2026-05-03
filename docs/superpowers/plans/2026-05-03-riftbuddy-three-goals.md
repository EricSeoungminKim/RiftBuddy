# RiftBuddy Three-Goal Cleanup & Feature Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Strip everything outside 3 features (in-game AI coach, draft recommender, post-game analyzer), then fix each feature to production quality.

**Architecture:** Python FastAPI backend + Electron + React frontend. Backend unchanged structurally — remove auth module usage, remove unused overlay tabs. Draft window redesigned around role-tier picks + team-comp recommendation + opponent matchup winrates. Post-game generates timeline-style feedback from snapshots.

**Tech Stack:** Python 3.11, FastAPI, Anthropic Claude Sonnet 4.6, ElevenLabs TTS, faster-whisper STT, Electron 28, React 18, TypeScript, op.gg MCP HTTP API

---

## File Map

### Files to DELETE
- `frontend/src/components/overlay/TimersTab.tsx` — Timers tab (cut)
- `frontend/src/components/overlay/GoldTab.tsx` — Gold tab (cut)
- `frontend/src/components/overlay/BuffsTab.tsx` — Buffs tab (cut)
- `frontend/src/components/overlay/UltsTab.tsx` — Ults tab (cut)
- `frontend/src/hooks/useGameEvents.ts` — only used by cut tabs
- `backend/auth/supabase_client.py` — auth removed
- `frontend/src/draft/pages/PostLockInPage.tsx` — rune apply page (cut, runes out of scope)
- `docs/superpowers/plans/2026-04-30-riftbuddy-mvp.md`
- `docs/superpowers/plans/2026-05-01-subproject-a-draft-window.md`
- `docs/superpowers/plans/2026-05-01-subproject-b-postgame-coach.md`
- `docs/superpowers/plans/2026-05-01-subproject-c-overlay.md`
- `docs/superpowers/plans/2026-05-02-overlay-redesign.md`
- `docs/superpowers/specs/2026-05-01-draft-overlay-coach-design.md`
- `docs/superpowers/specs/2026-05-02-overlay-redesign-design.md`
- `docs/todo/26-05-01.md`
- `docs/todo/26-05-02.md`

### Files to MODIFY
- `backend/main.py` — remove auth import/check, simplify WS handler
- `frontend/src/components/Overlay.tsx` — remove 4 tabs, keep AI tab only, remove `useGameEvents`
- `frontend/src/components/overlay/TabBar.tsx` — remove 4 tab entries, keep AI only (or delete TabBar entirely)
- `frontend/electron/main.ts` — reduce TAB_COUNT to 1, remove tab-switch hotkeys, remove settings-mode hotkey
- `frontend/src/draft/pages/DraftPage.tsx` — redesign panels: tier picks + team comp rec + opponent matchup winrates
- `frontend/src/draft/hooks/useDraftAnalysis.ts` — add `fetchOpponentMatchups`, split per-fetch loading states
- `frontend/src/draft/components/DraftRecommendPanel.tsx` — NEW: role tier list from op.gg meta
- `frontend/src/draft/components/TeamCompPanel.tsx` — NEW: team-comp-aware champion recommendation
- `frontend/src/draft/components/OpponentMatchupPanel.tsx` — NEW: N opponent winrates vs recommended pick
- `backend/draft/router.py` — add `POST /draft/recommend-for-role` endpoint (meta + team comp → LLM picks top 3)
- `backend/context/question_planner.py` — expand cases: each role, objective timing, cs deficit, kill pressure, vision
- `backend/postgame/router.py` — rewrite prompt → timeline-style feedback with timestamps + specific analysis
- `backend/game_session.py` — add `same_role_opponent` tracking to snapshots (for CS/gold comparison)
- `frontend/src/draft/pages/PostGamePage.tsx` — update to render timeline sections; auto-trigger on `game_end` WS event
- `frontend/src/hooks/useWebSocket.ts` — ensure `game_end` event triggers navigation to PostGamePage
- `frontend/src/draft/DraftApp.tsx` — remove `/post-lock-in` route; handle `game_end` → navigate to `/post-game`

---

## Task 1: Delete dead files + remove auth

**Files:**
- Delete: `frontend/src/components/overlay/TimersTab.tsx`, `GoldTab.tsx`, `BuffsTab.tsx`, `UltsTab.tsx`
- Delete: `frontend/src/hooks/useGameEvents.ts`
- Delete: `frontend/src/draft/pages/PostLockInPage.tsx`
- Delete: all old `docs/` plan/spec/todo files listed above
- Modify: `backend/main.py`
- Modify: `backend/auth/supabase_client.py` → delete file

- [ ] **Step 1: Delete overlay tab files**

```bash
rm frontend/src/components/overlay/TimersTab.tsx
rm frontend/src/components/overlay/GoldTab.tsx
rm frontend/src/components/overlay/BuffsTab.tsx
rm frontend/src/components/overlay/UltsTab.tsx
rm frontend/src/hooks/useGameEvents.ts
rm frontend/src/draft/pages/PostLockInPage.tsx
```

- [ ] **Step 2: Delete old docs**

```bash
rm docs/superpowers/plans/2026-04-30-riftbuddy-mvp.md
rm docs/superpowers/plans/2026-05-01-subproject-a-draft-window.md
rm docs/superpowers/plans/2026-05-01-subproject-b-postgame-coach.md
rm docs/superpowers/plans/2026-05-01-subproject-c-overlay.md
rm docs/superpowers/plans/2026-05-02-overlay-redesign.md
rm docs/superpowers/specs/2026-05-01-draft-overlay-coach-design.md
rm docs/superpowers/specs/2026-05-02-overlay-redesign-design.md
rm docs/todo/26-05-01.md
rm docs/todo/26-05-02.md
```

- [ ] **Step 3: Remove auth from `backend/main.py`**

Replace the websocket handler signature and auth block. Current lines 115-121:
```python
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = ""):
    should_bypass_auth = CONFIG["test_mode"] == "1" or CONFIG["bypass_auth"] == "1"
    user = {"id": "dev-user"} if should_bypass_auth else await verify_token(token) if token else None
    if user is None:
        await websocket.close(code=4001, reason="Unauthorized")
        return
```

Replace with:
```python
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
```

Also remove the import at top of `backend/main.py`:
```python
from backend.auth.supabase_client import verify_token
```

- [ ] **Step 4: Delete auth module**

```bash
rm -rf backend/auth/
```

- [ ] **Step 5: Verify backend starts without import errors**

```bash
cd /Users/smk/Documents/GitHub/RiftBuddy
python -m uvicorn backend.main:app --port 8001 --reload &
sleep 3
curl http://localhost:8001/health
kill %1
```

Expected: `{"status":"ok"}`

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "chore: remove dead tabs, auth module, and old planning docs"
```

---

## Task 2: Simplify overlay — AI tab only

**Files:**
- Modify: `frontend/src/components/Overlay.tsx`
- Modify: `frontend/src/components/overlay/TabBar.tsx`
- Modify: `frontend/electron/main.ts`

- [ ] **Step 1: Rewrite `TabBar.tsx` — single AI tab (no switching needed)**

Replace entire file content:
```tsx
// No-op: overlay now has only the AI tab. TabBar kept as minimal header label.
export function TabBar() {
  return (
    <div
      style={{
        display: "flex",
        background: "rgba(9,12,18,0.72)",
        border: "1px solid rgba(255,255,255,0.14)",
        borderRadius: 7,
        padding: "4px 10px",
        marginBottom: 4,
        boxShadow: "0 12px 32px rgba(0,0,0,0.3)",
      }}
    >
      <span style={{ fontSize: 12, color: "#14d9be", fontWeight: 700 }}>🤖 AI Coach</span>
    </div>
  );
}
```

- [ ] **Step 2: Rewrite `Overlay.tsx` — remove tab state, unused imports**

Replace entire file:
```tsx
import { useEffect, useRef, useState } from "react";
import { useWebSocket } from "../hooks/useWebSocket";
import { AdviceCard } from "./AdviceCard";
import { StatusBar } from "./StatusBar";
import { TabBar } from "./overlay/TabBar";

export function Overlay() {
  const { lastError, isConnected, audioQueue, messages, requestVoiceQuestion, requestPlannedAdvice } = useWebSocket();
  const [language, setLanguage] = useState((import.meta.env.VITE_RIFTBUDDY_RESPONSE_LANGUAGE as string) ?? "ko");
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (audioQueue.length === 0) return;
    const buf = audioQueue[audioQueue.length - 1];
    const blob = new Blob([buf], { type: "audio/mpeg" });
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    audio.play().catch(() => {});
    return () => URL.revokeObjectURL(url);
  }, [audioQueue]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      const modifierPressed = event.metaKey || event.ctrlKey;
      if (modifierPressed && event.shiftKey && event.key.toLowerCase() === "b") {
        event.preventDefault();
        requestPlannedAdvice(language);
      }
      if (modifierPressed && event.shiftKey && event.code === "Space") {
        event.preventDefault();
        requestVoiceQuestion(language);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [language, requestPlannedAdvice, requestVoiceQuestion]);

  useEffect(() => {
    return window.riftBuddy?.onRequestAdvice(() => requestPlannedAdvice(language));
  }, [language, requestPlannedAdvice]);

  useEffect(() => {
    return window.riftBuddy?.onRequestVoiceQuestion(() => requestVoiceQuestion(language));
  }, [language, requestVoiceQuestion]);

  useEffect(() => {
    return window.riftBuddy?.onToggleLanguage(() => {
      setLanguage((current) => (current === "ko" ? "en" : "ko"));
    });
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [lastError, messages]);

  return (
    <div
      style={{
        width: 500,
        height: 420,
        padding: 10,
        boxSizing: "border-box",
        pointerEvents: "auto",
        background: "linear-gradient(140deg, rgba(9,12,18,0.18), rgba(20,52,48,0.09))",
        borderRadius: 10,
      }}
    >
      <StatusBar isConnected={isConnected} language={language} onLanguageChange={setLanguage} />
      <TabBar />
      <div
        ref={scrollRef}
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 6,
          maxHeight: 360,
          overflowY: "auto",
          paddingRight: 4,
          scrollbarWidth: "thin",
          maskImage: "linear-gradient(to bottom, transparent 0, black 18px, black calc(100% - 10px), transparent 100%)",
        }}
      >
        {lastError && <AdviceCard role="system" text={lastError} />}
        {messages.map((message, index) => (
          <AdviceCard key={`${message.role}-${index}-${message.text}`} role={message.role} text={message.text} />
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Update `electron/main.ts` — remove tab-switch and settings-mode hotkeys**

Remove these globalShortcut.register blocks (lines 181-215):
```ts
// REMOVE these 3 blocks:
globalShortcut.register("CommandOrControl+Shift+]", ...);
globalShortcut.register("CommandOrControl+Shift+[", ...);
globalShortcut.register("CommandOrControl+Shift+,", ...);
// REMOVE ipcMain.on("riftbuddy:exit-settings-mode", ...)
```

Also remove `let currentTab = 0;` and `const TAB_COUNT = 5;` variables.

Keep: `Cmd+Shift+B`, `Cmd+Shift+Space`, `Cmd+Shift+L`, `Cmd+Shift+D`.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat(overlay): remove 4 extra tabs, AI coach only"
```

---

## Task 3: Expand `question_planner.py` — more specific per-role cases

**Files:**
- Modify: `backend/context/question_planner.py`
- Test: `backend/tests/test_question_planner.py`

The current planner has basic cases. Expand to cover: early lane kill pressure, vision deficit (non-support), objective timing (dragon/baron near), shutdown bounty risk, kill-lead snowball.

- [ ] **Step 1: Write failing tests**

Replace entire `backend/tests/test_question_planner.py`:
```python
import pytest
from backend.context.question_planner import build_planned_question
from backend.riot.live_client import GameState


def _state(**kwargs) -> GameState:
    defaults = dict(
        current_health=2000, max_health=2000, gold=1000, level=6,
        game_time=600.0, champion_name="Ezreal", summoner_name="Player",
        game_mode="CLASSIC", kills=0, deaths=0, assists=0, creep_score=60,
        ward_score=10.0, position="BOTTOM", assigned_position="bottom",
        ally_champions=(), enemy_champions=(), all_champions=(),
        ally_gold=15000.0, enemy_gold=15000.0, gold_diff=0.0,
        items=(), summoner_spells=(), recent_events=(),
    )
    defaults.update(kwargs)
    return GameState(**defaults)


def test_low_hp_with_gold_recall():
    q = build_planned_question(_state(current_health=600, max_health=2000, gold=1500), "ko")
    assert "귀환" in q or "리콜" in q


def test_high_gold_item_spike():
    q = build_planned_question(_state(gold=2500), "ko")
    assert "리콜" in q or "아이템" in q


def test_jungle_low_gold_routing():
    q = build_planned_question(_state(assigned_position="jungle", gold=700, current_health=1800, max_health=2000), "ko")
    assert "정글" in q


def test_cs_deficit():
    q = build_planned_question(_state(game_time=720.0, creep_score=40), "ko")
    assert "CS" in q or "cs" in q.lower() or "웨이브" in q


def test_team_ahead():
    q = build_planned_question(_state(gold_diff=2000), "ko")
    assert "앞서" in q or "리드" in q


def test_team_behind():
    q = build_planned_question(_state(gold_diff=-2000), "ko")
    assert "밀리" in q or "역전" in q


def test_support_low_vision():
    q = build_planned_question(_state(assigned_position="utility", ward_score=2.0), "ko")
    assert "시야" in q or "와드" in q


def test_kill_pressure_adc():
    # 3 kills early = snowball case
    q = build_planned_question(_state(assigned_position="bottom", kills=3, deaths=0, game_time=480.0), "ko")
    assert len(q) > 20


def test_objective_timing_pre_dragon():
    # game_time ~4:45 = dragon spawns at 5:00
    q = build_planned_question(_state(game_time=270.0), "ko")
    assert len(q) > 20


def test_english_fallback():
    q = build_planned_question(_state(), "en")
    assert len(q) > 10


def test_top_role():
    q = build_planned_question(_state(assigned_position="top", kills=0, deaths=2, game_time=600.0), "ko")
    assert len(q) > 20


def test_mid_role():
    q = build_planned_question(_state(assigned_position="middle", game_time=480.0, gold=1400), "ko")
    assert len(q) > 20
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/smk/Documents/GitHub/RiftBuddy
python -m pytest backend/tests/test_question_planner.py -v 2>&1 | head -40
```

Expected: several FAIL (kill_pressure, objective_timing, top_role, mid_role have no matching cases yet)

- [ ] **Step 3: Rewrite `backend/context/question_planner.py` with expanded cases**

Replace entire file:
```python
from backend.context.engine import normalize_position
from backend.riot.live_client import GameState

_DRAGON_SPAWN_SECONDS = 300.0
_BARON_SPAWN_SECONDS = 1200.0
_OBJECTIVE_WINDOW_SECONDS = 90.0


def build_planned_question(state: GameState, language: str = "ko") -> str:
    if language != "ko":
        return _build_english_question(state)
    return _build_korean_question(state)


def _build_korean_question(state: GameState) -> str:
    health_pct = _health_percent(state)
    position = normalize_position(state.assigned_position)
    gold_diff = state.gold_diff
    kda = f"{state.kills}/{state.deaths}/{state.assists}"
    minute = int(state.game_time // 60)
    cs_floor = _expected_cs_floor(state.game_time)
    team_state = _team_state_phrase(gold_diff)
    near_obj = _near_objective(state.game_time)

    # 1. Critical HP + gold → recall decision
    if health_pct < 35 and state.gold >= 1200:
        return (
            f"{team_state} 나는 {position}이고 체력이 {health_pct:g}%인데 {state.gold:g}골드를 들고 있어. "
            "지금 바로 귀환해야 하는지, 안전하게 한 웨이브나 캠프만 더 보고 귀환해도 되는지 판단해줘."
        )

    # 2. Critical HP → immediate safety call
    if health_pct < 35:
        return (
            f"{team_state} 나는 {position}이고 체력이 {health_pct:g}%야. "
            "라인에 남아도 되는지, 바로 귀환/합류해야 하는지 판단해줘."
        )

    # 3. Near objective spawn → prioritize?
    if near_obj:
        return (
            f"{near_obj} 곧 스폰 예정이야. {team_state} 나는 {position}이고 KDA {kda}, 골드 {state.gold:g}야. "
            f"오브젝트를 위해 지금 어디에서 무엇을 준비해야 하는지 구체적으로 알려줘."
        )

    # 4. High gold → item spike timing
    if state.gold >= 2200:
        return (
            f"{team_state} 나는 {position}에서 {state.gold:g}골드를 들고 있고 KDA는 {kda}, CS는 {state.creep_score}야. "
            "지금 리콜해서 아이템 스파이크를 만들지, 오브젝트/웨이브를 한 번 더 보고 움직일지 정해줘."
        )

    # 5. Kill lead → snowball opportunity
    if state.kills >= 3 and state.deaths == 0 and state.game_time < 900:
        return (
            f"나는 {position}이고 {minute}분에 {state.kills}킬 무데스야. {team_state} "
            "이 킬 리드를 지금 어떻게 눌러야 하는지 — 타워 압박, 로밍, 오브젝트 중 우선순위를 알려줘."
        )

    # 6. Behind on kills/dying early
    if state.deaths >= 3 and minute <= 15:
        return (
            f"나는 {position}이고 {minute}분에 데스가 {state.deaths}야. {team_state} "
            "라인을 어떻게 플레이해야 데스를 줄이고 cs/골드를 회복할 수 있는지 알려줘."
        )

    # 7. Jungle: healthy + low gold → routing
    if position == "정글" and health_pct >= 70 and state.gold < 900:
        return (
            f"{team_state} 나는 정글이고 체력은 {health_pct:g}%, 골드는 {state.gold:g}야. "
            "지금 내 정글링 루트, 갱 각, 용/전령 준비, 시야 중 어디에 시간을 써야 하는지 구체적으로 말해줘."
        )

    # 8. Jungle: general
    if position == "정글":
        return (
            f"{team_state} 나는 정글이고 KDA는 {kda}, 골드는 {state.gold:g}, 레벨은 {state.level}이야. "
            "다음 60초 동안 정글링, 갱, 오브젝트, 시야 중 무엇을 먼저 해야 하는지 우선순위로 알려줘."
        )

    # 9. Support: low vision
    if position == "서폿" and state.ward_score < 5:
        return (
            f"{team_state} 나는 서폿이고 시야 점수가 {state.ward_score:g}로 낮아. "
            "지금 어느 쪽 강가/정글 시야를 먼저 잡아야 하는지 알려줘."
        )

    # 10. CS deficit
    if state.creep_score < cs_floor:
        return (
            f"{minute}분인데 CS가 {state.creep_score}라 낮은 편이야. {team_state} "
            f"{position}에서 웨이브를 밀어야 하는지, 당겨야 하는지, 로밍/합류를 포기하고 파밍해야 하는지 알려줘."
        )

    # 11. Team ahead → press lead
    if gold_diff >= 1500:
        return (
            f"우리 팀이 약 {gold_diff:g}골드 앞서지만, 나는 {position}에서 KDA {kda}, 골드 {state.gold:g}야. "
            "지금 리드를 더 굴릴 구체적인 플레이 하나와 피해야 할 리스크 하나를 알려줘."
        )

    # 12. Team behind → comeback path
    if gold_diff <= -1500:
        return (
            f"우리 팀이 약 {abs(gold_diff):g}골드 밀리고 있고, 나는 {position}에서 KDA {kda}, 골드 {state.gold:g}야. "
            "지금 역전각을 만들 수 있는 현실적인 선택지 하나와 버려야 할 플레이 하나를 알려줘."
        )

    # 13. Role-specific default questions
    role_defaults = {
        "탑": (
            f"나는 탑 {state.champion_name}이고 {minute}분 KDA {kda}, CS {state.creep_score}, 골드 {state.gold:g}야. {team_state} "
            "지금 사이드 압박을 계속해야 하는지, 합류해야 하는지, 타워를 먹어야 하는지 우선순위를 알려줘."
        ),
        "미드": (
            f"나는 미드 {state.champion_name}이고 {minute}분 KDA {kda}, CS {state.creep_score}, 골드 {state.gold:g}야. {team_state} "
            "지금 로밍 타이밍인지, 웨이브 클리어 후 오브젝트인지, 라인 압박인지 판단해줘."
        ),
        "바텀": (
            f"나는 원딜 {state.champion_name}이고 {minute}분 KDA {kda}, CS {state.creep_score}, 골드 {state.gold:g}야. {team_state} "
            "지금 바텀 타워를 계속 노려야 하는지, 드래곤 합류를 준비해야 하는지, 로밍해도 되는지 알려줘."
        ),
        "서폿": (
            f"나는 서폿 {state.champion_name}이고 {minute}분 KDA {kda}, 시야점수 {state.ward_score:g}야. {team_state} "
            "지금 원딜 곁을 지켜야 하는지, 로밍 타이밍인지, 시야 작업을 먼저 해야 하는지 알려줘."
        ),
    }
    if position in role_defaults:
        return role_defaults[position]

    # 14. Generic fallback
    return (
        f"나는 {position}이고 {minute}분 현재 KDA {kda}, CS {state.creep_score}, 골드 {state.gold:g}야. "
        "지금 가장 가치 높은 다음 행동을 하나만 구체적으로 골라줘."
    )


def _build_english_question(state: GameState) -> str:
    health_pct = _health_percent(state)
    position = normalize_position(state.assigned_position)
    minute = int(state.game_time // 60)
    kda = f"{state.kills}/{state.deaths}/{state.assists}"
    near_obj = _near_objective(state.game_time)

    if health_pct < 35 and state.gold >= 1200:
        return f"I'm low HP at {health_pct:g}% holding {state.gold:g} gold. Should I recall now or stay for one more play?"
    if near_obj:
        return f"{near_obj} is spawning soon. As {position} with KDA {kda}, what should I do to prepare?"
    if state.kills >= 3 and state.deaths == 0 and state.game_time < 900:
        return f"I'm {state.kills}/0 at {minute} minutes. How do I best snowball this lead as {position}?"
    if state.gold_diff >= 1500:
        return "My team is ahead in gold. What should I do to safely close out the lead?"
    if state.gold_diff <= -1500:
        return "My team is behind in gold. What should I prioritize now to create a comeback?"
    if position == "정글":
        return "I am jungle. Should I prioritize farming route, gank, objective, or vision right now?"
    return f"I'm {position} at {minute} minutes with KDA {kda} and {state.creep_score} CS. What's my best next action?"


def _health_percent(state: GameState) -> float:
    if state.max_health <= 0:
        return 0.0
    return round((state.current_health / state.max_health) * 100, 1)


def _expected_cs_floor(game_time_seconds: float) -> int:
    return int((game_time_seconds / 60) * 5)


def _team_state_phrase(gold_diff: float) -> str:
    if gold_diff >= 1500:
        return f"우리 팀이 약 {gold_diff:g}골드 앞서는 상황이야."
    if gold_diff <= -1500:
        return f"우리 팀이 약 {abs(gold_diff):g}골드 밀리는 상황이야."
    return "전체 골드는 비슷한 상황이야."


def _near_objective(game_time: float) -> str | None:
    """Return objective name if within OBJECTIVE_WINDOW_SECONDS of a spawn."""
    def _next_spawn(first: float, interval: float) -> float:
        if game_time < first:
            return first
        elapsed = game_time - first
        return first + (int(elapsed / interval) + 1) * interval

    dragon_next = _next_spawn(_DRAGON_SPAWN_SECONDS, 300.0)
    baron_next = _next_spawn(_BARON_SPAWN_SECONDS, 360.0)

    if 0 < dragon_next - game_time <= _OBJECTIVE_WINDOW_SECONDS:
        return "드래곤"
    if 0 < baron_next - game_time <= _OBJECTIVE_WINDOW_SECONDS:
        return "바론"
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest backend/tests/test_question_planner.py -v
```

Expected: all 12 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/context/question_planner.py backend/tests/test_question_planner.py
git commit -m "feat(coach): expand question_planner with role-specific + objective timing cases"
```

---

## Task 4: Draft redesign — role tier list + team comp rec + opponent matchup winrates

**Files:**
- Create: `frontend/src/draft/components/DraftRecommendPanel.tsx`
- Create: `frontend/src/draft/components/TeamCompPanel.tsx`
- Create: `frontend/src/draft/components/OpponentMatchupPanel.tsx`
- Delete: `frontend/src/draft/components/RecommendPanel.tsx` (replaced)
- Delete: `frontend/src/draft/components/LaningPanel.tsx` (replaced)
- Delete: `frontend/src/draft/components/SynergyPanel.tsx` (replaced)
- Modify: `frontend/src/draft/hooks/useDraftAnalysis.ts`
- Modify: `frontend/src/draft/pages/DraftPage.tsx`
- Modify: `backend/draft/router.py`

### 4a: Backend — add `/draft/recommend-for-role` endpoint

This endpoint takes: `ally` champs, `my_role`, optionally `my_champion` (if already chosen).
It fetches meta tier list from op.gg, then asks LLM to pick top 3 considering team comp.
Returns: `{ recommendations: [{champion, reason, tier}] }`.

- [ ] **Step 1: Add endpoint to `backend/draft/router.py`**

Append to the file (after existing routes):
```python
class RecommendForRoleRequest(BaseModel):
    ally: list[str]
    enemy: list[str]
    my_role: str
    language: str = "ko"


@router.post("/draft/recommend-for-role")
async def recommend_for_role(body: RecommendForRoleRequest):
    pos = _normalize_position(body.my_role)
    try:
        meta = await get_meta_champions(pos)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"op.gg MCP error: {exc}")

    # Take top 10 by tier from meta list
    top_meta = meta[:10] if isinstance(meta, list) else []
    meta_names = [c.get("champion_name") or c.get("name") or str(c) for c in top_meta if c]

    ally_str = ", ".join(body.ally) if body.ally else "없음"
    enemy_str = ", ".join(body.enemy) if body.enemy else "없음"
    meta_str = ", ".join(meta_names) if meta_names else "정보 없음"

    if body.language == "ko":
        prompt = (
            f"현재 {pos} 포지션 메타 티어 챔피언들: {meta_str}\n"
            f"아군 조합: {ally_str}\n"
            f"상대 조합: {enemy_str}\n\n"
            f"위 메타 티어 챔피언들 중에서 아군 조합과 시너지가 좋고 상대 조합을 잘 상대할 수 있는 "
            f"{pos} 챔피언 3개를 추천해줘. "
            "반드시 다음 형식으로 답해줘:\n"
            "1. [챔피언명]: [한 줄 이유]\n"
            "2. [챔피언명]: [한 줄 이유]\n"
            "3. [챔피언명]: [한 줄 이유]"
        )
    else:
        prompt = (
            f"Meta tier {pos} champions: {meta_str}\n"
            f"Ally comp: {ally_str}\n"
            f"Enemy comp: {enemy_str}\n\n"
            f"Recommend 3 {pos} champions from the meta list that synergize with allies and counter enemies. "
            "Format:\n1. [Champion]: [one-line reason]\n2. [Champion]: [one-line reason]\n3. [Champion]: [one-line reason]"
        )

    dummy_packet = ContextPacket(health_percent=100.0, gold=0.0, level=1, game_time_minutes=0.0, summary=prompt)
    try:
        raw_advice = await get_advice(dummy_packet, user_query=prompt, language=body.language)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM error: {exc}")

    recommendations = _parse_recommendations(raw_advice)
    return {"recommendations": recommendations, "meta": meta_names}


def _normalize_position(role: str) -> str:
    from backend.draft.opgg_client import _POSITION_MAP
    return _POSITION_MAP.get(role.lower(), role.lower())


def _parse_recommendations(text: str) -> list[dict]:
    import re
    lines = text.strip().split("\n")
    results = []
    for line in lines:
        m = re.match(r"\d+\.\s*(.+?):\s*(.+)", line.strip())
        if m:
            results.append({"champion": m.group(1).strip(), "reason": m.group(2).strip()})
    return results[:3]
```

- [ ] **Step 2: Add `fetchRecommendForRole` to `useDraftAnalysis.ts`**

Add new interface and function. Add to the `DraftState` interface:
```ts
  recommendForRole: { recommendations: {champion: string; reason: string}[]; meta: string[] } | null
  loadingRecommend: boolean
  loadingMatchups: boolean
  loadingStrategy: boolean
```

Add `fetchRecommendForRole` callback:
```ts
const fetchRecommendForRole = useCallback(async (ally: string[], enemy: string[], myRole: string, language = 'ko') => {
  setState(prev => ({ ...prev, loadingRecommend: true }))
  try {
    const res = await fetch(`${BASE}/draft/recommend-for-role`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ally, enemy, my_role: myRole, language }),
    })
    if (!res.ok) throw new Error(`recommend-for-role ${res.status}`)
    const data = await res.json()
    setState(prev => ({ ...prev, recommendForRole: data, loadingRecommend: false }))
  } catch (e) {
    setState(prev => ({ ...prev, loadingRecommend: false }))
  }
}, [])
```

Full updated `DraftState` interface in `useDraftAnalysis.ts`:
```ts
export interface DraftState {
  analysis: ChampionAnalysis | null
  matchup: MatchupGuide | null
  matchups: Record<number, MatchupGuide>
  runes: RuneRecommendation | null
  teamStrategy: TeamStrategy | null
  recommendForRole: { recommendations: {champion: string; reason: string}[]; meta: string[] } | null
  loading: boolean
  loadingRecommend: boolean
  loadingMatchups: boolean
  loadingStrategy: boolean
  error: string | null
}
```

Update initial state in `useDraftAnalysis`:
```ts
const [state, setState] = useState<DraftState>({
  analysis: null,
  matchup: null,
  matchups: {},
  runes: null,
  teamStrategy: null,
  recommendForRole: null,
  loading: false,
  loadingRecommend: false,
  loadingMatchups: false,
  loadingStrategy: false,
  error: null,
})
```

Update `fetchMatchup` to use `loadingMatchups`:
```ts
setState(prev => ({ ...prev, loadingMatchups: true }))
// ... on success:
setState(prev => ({ ...prev, loadingMatchups: false, matchup, matchups: ... }))
// ... on error:
setState(prev => ({ ...prev, loadingMatchups: false }))
```

Update `fetchTeamStrategy` to use `loadingStrategy`:
```ts
setState(prev => ({ ...prev, loadingStrategy: true }))
// ... on success:
setState(prev => ({ ...prev, loadingStrategy: false, teamStrategy: ... }))
// ... on error:
setState(prev => ({ ...prev, loadingStrategy: false }))
```

Return `fetchRecommendForRole` from the hook.

- [ ] **Step 3: Create `DraftRecommendPanel.tsx`**

```tsx
// frontend/src/draft/components/DraftRecommendPanel.tsx
interface Recommendation {
  champion: string
  reason: string
}

interface Props {
  recommendations: Recommendation[]
  meta: string[]
  myRole: string
  loading: boolean
}

const cardStyle: React.CSSProperties = {
  background: '#12131f',
  border: '1px solid #2a2d4a',
  borderRadius: 8,
  padding: 14,
  flex: 1,
  minWidth: 0,
}

export default function DraftRecommendPanel({ recommendations, meta, myRole, loading }: Props) {
  return (
    <div style={cardStyle}>
      <div style={{ fontSize: 11, color: '#888', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 1 }}>
        {myRole} 추천 픽
      </div>
      {loading && <div style={{ color: '#888', fontSize: 12 }}>분석 중...</div>}
      {!loading && recommendations.length === 0 && (
        <div style={{ color: '#555', fontSize: 12 }}>챔피언 선택 진행 중 자동 추천됩니다</div>
      )}
      {recommendations.map((rec, i) => (
        <div key={rec.champion} style={{ marginBottom: 10 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{
              background: i === 0 ? '#f0c040' : '#3a8fd1',
              color: '#0d0e1a',
              borderRadius: 4,
              padding: '1px 7px',
              fontSize: 11,
              fontWeight: 700,
            }}>{i + 1}</span>
            <span style={{ color: '#e0e0e0', fontWeight: 600, fontSize: 14 }}>{rec.champion}</span>
          </div>
          <div style={{ color: '#aaa', fontSize: 12, marginTop: 4, lineHeight: 1.5, paddingLeft: 4 }}>{rec.reason}</div>
        </div>
      ))}
      {meta.length > 0 && !loading && (
        <div style={{ marginTop: 8, borderTop: '1px solid #1a1d2e', paddingTop: 8 }}>
          <div style={{ fontSize: 10, color: '#555', marginBottom: 4 }}>메타 티어 ({meta.length})</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
            {meta.slice(0, 8).map(c => (
              <span key={c} style={{ fontSize: 11, color: '#666', background: '#1a1d2e', borderRadius: 3, padding: '1px 5px' }}>{c}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
```

Add `import React from 'react'` at the top.

- [ ] **Step 4: Create `OpponentMatchupPanel.tsx`**

```tsx
// frontend/src/draft/components/OpponentMatchupPanel.tsx
import React from 'react'
import { MatchupGuide } from '../hooks/useDraftAnalysis'

interface Props {
  recommendedChampion: string
  enemyChampions: string[]
  matchups: Record<number, MatchupGuide>
  loading: boolean
  myRole: string
}

const cardStyle: React.CSSProperties = {
  background: '#12131f',
  border: '1px solid #2a2d4a',
  borderRadius: 8,
  padding: 14,
  flex: 1,
  minWidth: 0,
}

function winRateColor(wr: number | undefined): string {
  if (wr === undefined) return '#888'
  if (wr >= 52) return '#56f39a'
  if (wr <= 47) return '#f35656'
  return '#f0c040'
}

export default function OpponentMatchupPanel({ recommendedChampion, enemyChampions, matchups, loading, myRole }: Props) {
  const filled = enemyChampions.filter(Boolean)
  return (
    <div style={cardStyle}>
      <div style={{ fontSize: 11, color: '#888', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 1 }}>
        상대 챔피언 승률 {recommendedChampion ? `vs ${recommendedChampion}` : ''}
      </div>
      {loading && <div style={{ color: '#888', fontSize: 12 }}>불러오는 중...</div>}
      {!loading && filled.length === 0 && (
        <div style={{ color: '#555', fontSize: 12 }}>상대 챔피언이 픽되면 승률이 표시됩니다</div>
      )}
      {filled.map((enemy, i) => {
        const matchup = Object.values(matchups).find(m => m.enemyChampion === enemy)
        const wr = matchup?.winRate
        return (
          <div key={enemy} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <span style={{ color: '#e05050', fontSize: 13 }}>{enemy}</span>
            <span style={{ color: winRateColor(wr), fontWeight: 700, fontSize: 14 }}>
              {wr !== undefined ? `${wr.toFixed(1)}%` : loading ? '...' : 'N/A'}
            </span>
          </div>
        )
      })}
    </div>
  )
}
```

- [ ] **Step 5: Create `TeamCompPanel.tsx`**

```tsx
// frontend/src/draft/components/TeamCompPanel.tsx
import React from 'react'
import { TeamStrategy } from '../hooks/useDraftAnalysis'

interface Props {
  strategy: TeamStrategy | null
  loading: boolean
}

const cardStyle: React.CSSProperties = {
  background: '#12131f',
  border: '1px solid #2a2d4a',
  borderRadius: 8,
  padding: 14,
  flex: 1,
  minWidth: 0,
  overflowY: 'auto',
  maxHeight: 280,
}

export default function TeamCompPanel({ strategy, loading }: Props) {
  return (
    <div style={cardStyle}>
      <div style={{ fontSize: 11, color: '#888', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 1 }}>
        팀 조합 분석
      </div>
      {loading && <div style={{ color: '#888', fontSize: 12 }}>분석 중...</div>}
      {!loading && !strategy && (
        <div style={{ color: '#555', fontSize: 12 }}>아군 챔피언이 2명 이상 선택되면 자동으로 팀 시너지를 분석합니다</div>
      )}
      {strategy && (
        <p style={{ fontSize: 13, lineHeight: 1.7, color: '#ccc', margin: 0, whiteSpace: 'pre-wrap' }}>
          {strategy.strategy}
        </p>
      )}
    </div>
  )
}
```

- [ ] **Step 6: Rewrite `DraftPage.tsx` — new 3-panel layout**

Replace entire file:
```tsx
import React, { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import ChampionSlot from '../components/ChampionSlot'
import DraftRecommendPanel from '../components/DraftRecommendPanel'
import TeamCompPanel from '../components/TeamCompPanel'
import OpponentMatchupPanel from '../components/OpponentMatchupPanel'
import { useDraftAnalysis } from '../hooks/useDraftAnalysis'
import { ChampSelectSlot, useChampSelect } from '../hooks/useChampSelect'

const ROLES = ['탑', '정글', '미드', '바텀', '서폿']
const ROLE_BY_LCU: Record<string, string> = {
  top: '탑', jungle: '정글', middle: '미드', bottom: '바텀', utility: '서폿',
}

type Team = [string, string, string, string, string]
const EMPTY_TEAM: Team = ['', '', '', '', '']

function toTeam(arr: string[]): Team {
  const t: Team = [...EMPTY_TEAM]
  arr.slice(0, 5).forEach((v, i) => { t[i] = v })
  return t
}

function slotsToTeam(slots: ChampSelectSlot[], fallback: string[]): Team {
  const t = toTeam(fallback)
  slots.slice(0, 5).forEach((slot, i) => { t[i] = slot.champion || t[i] || '' })
  return t
}

function roleLabel(slot: ChampSelectSlot | undefined, fallback: string): string {
  const raw = slot?.assignedPosition?.toLowerCase()
  return raw ? ROLE_BY_LCU[raw] ?? fallback : fallback
}

export default function DraftPage() {
  const navigate = useNavigate()
  const [ally, setAlly] = useState<Team>([...EMPTY_TEAM])
  const [enemy, setEnemy] = useState<Team>([...EMPTY_TEAM])
  const [myRole, setMyRole] = useState('바텀')
  const prevAllyRef = useRef('')
  const prevEnemyRef = useRef('')
  const prevRoleRef = useRef('')
  const prevRecommendKeyRef = useRef('')
  const prevStrategyKeyRef = useRef('')
  const prevMatchupKeyRef = useRef('')

  const {
    matchups, teamStrategy, recommendForRole,
    loadingRecommend, loadingMatchups, loadingStrategy,
    fetchRecommendForRole, fetchMatchup, fetchTeamStrategy, reset,
  } = useDraftAnalysis()

  const champSelect = useChampSelect(true)
  const roleLabels = ROLES.map((role, i) => roleLabel(champSelect.allySlots[i], role))
  const mySlotIndex = Math.max(0, champSelect.allySlots.findIndex(slot => slot.cellId === champSelect.myCell))

  // Sync LCU picks
  useEffect(() => {
    if (!champSelect.inProgress) return
    const allyKey = JSON.stringify(champSelect.allySlots)
    const enemyKey = JSON.stringify(champSelect.enemySlots)
    if (allyKey !== prevAllyRef.current) {
      prevAllyRef.current = allyKey
      setAlly(prev => slotsToTeam(champSelect.allySlots, prev))
    }
    if (enemyKey !== prevEnemyRef.current) {
      prevEnemyRef.current = enemyKey
      setEnemy(prev => slotsToTeam(champSelect.enemySlots, prev))
    }
  }, [champSelect])

  // Auto-detect my role from LCU (handles role swaps)
  useEffect(() => {
    if (!champSelect.inProgress || mySlotIndex < 0) return
    const detectedRole = roleLabels[mySlotIndex]
    if (detectedRole && detectedRole !== prevRoleRef.current) {
      prevRoleRef.current = detectedRole
      setMyRole(detectedRole)
    }
  }, [champSelect.inProgress, mySlotIndex, roleLabels.join('|')])

  // Auto-fetch recommend when ally/enemy/role changes
  useEffect(() => {
    const allyList = ally.filter(Boolean)
    const key = `${allyList.join(',')}|${enemy.filter(Boolean).join(',')}|${myRole}`
    if (key === prevRecommendKeyRef.current) return
    prevRecommendKeyRef.current = key
    fetchRecommendForRole(allyList, enemy.filter(Boolean), myRole)
  }, [ally, enemy, myRole, fetchRecommendForRole])

  // Auto-fetch team strategy when 2+ ally picks
  useEffect(() => {
    const allyList = ally.filter(Boolean)
    const enemyList = enemy.filter(Boolean)
    if (allyList.length < 2) return
    const key = `${allyList.join(',')}|${enemyList.join(',')}|${myRole}`
    if (key === prevStrategyKeyRef.current) return
    prevStrategyKeyRef.current = key
    const myChampion = ally[mySlotIndex] || allyList[0] || ''
    fetchTeamStrategy(allyList, enemyList, myChampion, myRole)
  }, [ally, enemy, myRole, mySlotIndex, fetchTeamStrategy])

  // Auto-fetch opponent matchup winrates vs recommended pick
  useEffect(() => {
    const recommendedChamp = recommendForRole?.recommendations?.[0]?.champion
    if (!recommendedChamp) return
    const enemyList = enemy.filter(Boolean)
    if (!enemyList.length) return
    const key = `${recommendedChamp}|${enemyList.join(',')}|${myRole}`
    if (key === prevMatchupKeyRef.current) return
    prevMatchupKeyRef.current = key
    enemyList.forEach((enemyChamp, i) => {
      fetchMatchup(recommendedChamp, enemyChamp, myRole, i)
    })
  }, [recommendForRole, enemy, myRole, fetchMatchup])

  // Reset on champ select end
  useEffect(() => {
    if (!champSelect.inProgress) {
      reset()
      prevRecommendKeyRef.current = ''
      prevStrategyKeyRef.current = ''
      prevMatchupKeyRef.current = ''
    }
  }, [champSelect.inProgress, reset])

  const recommendedChamp = recommendForRole?.recommendations?.[0]?.champion ?? ''

  const pageStyle: React.CSSProperties = {
    display: 'flex',
    flexDirection: 'column',
    height: '100vh',
    background: 'radial-gradient(circle at 20% -10%, rgba(49,83,122,0.24), transparent 34%), #080a12',
    color: '#e0e0e0',
    fontFamily: 'sans-serif',
    padding: 16,
    boxSizing: 'border-box',
    gap: 12,
  }

  return (
    <div style={pageStyle}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: 18, color: '#f0c040' }}>RiftBuddy — 챔피언 선택</h2>
          <div style={{ fontSize: 11, color: champSelect.inProgress ? '#56f39a' : '#777', marginTop: 3 }}>
            {champSelect.inProgress
              ? `LCU 연결됨 · 내 역할: ${myRole}`
              : champSelect.available ? 'League 클라이언트 연결됨 · 챔피언 선택 대기 중'
              : 'League 클라이언트 실행 대기 중'}
          </div>
        </div>
      </div>

      {/* Pick Grid */}
      <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
        <div>
          <div style={{ fontSize: 11, color: '#888', marginBottom: 6, textTransform: 'uppercase', letterSpacing: 1 }}>아군</div>
          <div style={{ display: 'flex', gap: 6 }}>
            {ally.map((id, i) => (
              <ChampionSlot
                key={i}
                championId={id || undefined}
                role={roleLabels[i]}
                isAlly={true}
                size={56}
                selected={mySlotIndex === i}
                completed={champSelect.allySlots[i]?.completed ?? true}
                cellId={champSelect.allySlots[i]?.cellId}
                onClick={() => {}}
              />
            ))}
          </div>
        </div>
        <div style={{ flex: 1 }} />
        <div>
          <div style={{ fontSize: 11, color: '#888', marginBottom: 6, textTransform: 'uppercase', letterSpacing: 1 }}>적군</div>
          <div style={{ display: 'flex', gap: 6 }}>
            {enemy.map((id, i) => (
              <ChampionSlot
                key={i}
                championId={id || undefined}
                role={roleLabels[i]}
                isAlly={false}
                size={56}
                selected={false}
                completed={champSelect.enemySlots[i]?.completed ?? true}
                cellId={champSelect.enemySlots[i]?.cellId}
                onClick={() => {}}
              />
            ))}
          </div>
        </div>
      </div>

      {/* Analysis Panels */}
      <div style={{ display: 'flex', gap: 12, flex: 1, minHeight: 0 }}>
        <DraftRecommendPanel
          recommendations={recommendForRole?.recommendations ?? []}
          meta={recommendForRole?.meta ?? []}
          myRole={myRole}
          loading={loadingRecommend}
        />
        <OpponentMatchupPanel
          recommendedChampion={recommendedChamp}
          enemyChampions={enemy}
          matchups={matchups}
          loading={loadingMatchups}
          myRole={myRole}
        />
        <TeamCompPanel
          strategy={teamStrategy}
          loading={loadingStrategy}
        />
      </div>
    </div>
  )
}
```

- [ ] **Step 7: Delete old panel components**

```bash
rm frontend/src/draft/components/RecommendPanel.tsx
rm frontend/src/draft/components/LaningPanel.tsx
rm frontend/src/draft/components/SynergyPanel.tsx
```

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat(draft): new 3-panel layout — tier picks, opponent matchup winrates, team comp"
```

---

## Task 5: Post-game — timeline-style LLM feedback + auto-trigger

**Files:**
- Modify: `backend/postgame/router.py`
- Modify: `backend/game_session.py`
- Modify: `frontend/src/draft/pages/PostGamePage.tsx`
- Modify: `frontend/src/draft/DraftApp.tsx`
- Modify: `frontend/src/hooks/useWebSocket.ts` (check game_end event handling)

### 5a: Backend — timeline prompt + same-role CS/gold comparison

- [ ] **Step 1: Update `game_session.py` — richer summary lines**

Replace `summary_lines` method:
```python
def summary_lines(self) -> list[str]:
    lines = []
    prev_gold = 0.0
    prev_cs = 0
    for s in self.snapshots:
        minutes = int(s.game_time // 60)
        seconds = int(s.game_time % 60)
        timestamp = f"{minutes}:{seconds:02d}"
        hp_pct = round((s.current_health / s.max_health) * 100, 1) if s.max_health else 0
        recent = getattr(s, "recent_events", ())
        gold_delta = s.gold - prev_gold if prev_gold else 0
        cs_delta = s.creep_score - prev_cs if prev_cs else 0
        prev_gold = s.gold
        prev_cs = s.creep_score
        lines.append(
            f"[{timestamp}] {s.champion_name} ({s.assigned_position}) | "
            f"HP {hp_pct}% | 골드 {s.gold:g} (팀차이 {s.gold_diff:+g}) | "
            f"KDA {s.kills}/{s.deaths}/{s.assists} | CS {s.creep_score} | "
            f"이벤트: {', '.join(recent) if recent else '없음'}"
        )
    return lines
```

- [ ] **Step 2: Rewrite post-game prompt in `backend/postgame/router.py`**

Replace the `coach()` function prompt:
```python
@router.post("/postgame/coach")
async def coach():
    if game_session.is_empty:
        raise HTTPException(status_code=400, detail="No game snapshots recorded.")

    lines_text = "\n".join(game_session.summary_lines())
    prompt = f"""다음은 리그 오브 레전드 게임 중 30초 간격으로 기록된 상태 스냅샷입니다:

{lines_text}

위 데이터를 분석해서 타임라인 형식의 코칭 리포트를 한국어로 작성해줘.

각 섹션은 다음 형식을 따라야 해:
- 구체적인 타임스탬프(e.g. 10:35)를 포함한 분석
- "분석: [상황 설명]" → "피드백: [구체적인 개선 방법]" 형식

반드시 다음 네 섹션을 포함해야 합니다:

[잘한 점]
(e.g. "분석: 8:20에 CS 72로 상위 파밍이었음. 피드백: 이 템포를 유지하면 아이템 스파이크가 빨라짐")

[개선할 점]
(e.g. "분석: 10:35에 상대 원딜보다 골드가 1200 낮아졌음. 피드백: 9분에 데스 2개가 직접적인 원인. 피가 없거나 적 정글이 바텀에 보이면 즉시 귀환해.")
(e.g. "분석: 15:20 한타에서 딜링 없이 빠르게 사망. 피드백: 원딜의 핵심은 DPS 유지. 뒤에서 포지션 잡고 안전하게 딜 넣어야 함")

[주요 순간]
(타임스탬프별 중요한 게임 전환점들)

[다음 게임 목표]
(위 분석을 바탕으로 다음 게임에서 집중해야 할 2-3가지 구체적 목표)"""

    dummy_packet = ContextPacket(
        health_percent=100.0, gold=0.0, level=1, game_time_minutes=0.0, summary=prompt,
    )
    try:
        raw = await get_advice(dummy_packet, user_query=prompt, language="ko")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM error: {exc}")

    sections = _parse_sections(raw)
    return sections
```

- [ ] **Step 3: Commit backend changes**

```bash
git add backend/postgame/router.py backend/game_session.py
git commit -m "feat(postgame): timeline-style LLM prompt with timestamps and CS/gold comparison"
```

### 5b: Frontend — post-game auto-trigger on game_end event

The `game_end` WS event is already broadcast from `backend/main.py` when `fetch_game_state()` returns None (game over). The draft window needs to navigate to `/post-game` on this event.

- [ ] **Step 4: Check `useWebSocket.ts` for game_end handling**

Read `frontend/src/hooks/useWebSocket.ts` and confirm `game_end` type is handled. If not, add:
```ts
if (parsed.type === 'game_end') {
  // signal game ended — consumers subscribe via onGameEnd
  setGameEnded(true)
}
```

Add `gameEnded: boolean` to the returned state and a `useEffect` that resets it after being read.

- [ ] **Step 5: Update `DraftApp.tsx` — listen for game_end, navigate to post-game**

Read `frontend/src/draft/DraftApp.tsx` first. It likely has React Router routes. The draft window needs access to `gameEnded` signal.

Add a top-level effect in `DraftApp.tsx`:
```tsx
// Inside DraftApp, after setting up navigate:
const { gameEnded } = useWebSocket()
const navigate = useNavigate()
useEffect(() => {
  if (gameEnded) navigate('/post-game')
}, [gameEnded, navigate])
```

Remove the `/post-lock-in` route entirely from the router.

- [ ] **Step 6: Update `PostGamePage.tsx` — render timeline sections**

Replace the four fixed card sections with timeline-aware rendering. The sections already contain pre-formatted text with timestamps from the new prompt. Just ensure `whiteSpace: 'pre-wrap'` renders them correctly — current code already does this.

Add a "새 게임 시작" button that calls `clearSnapshots()` and navigates back to `/draft`:
```tsx
<button
  onClick={() => { clearSnapshots(); navigate('/draft') }}
  style={{ background: '#3a8fd1', color: '#fff', border: 'none', borderRadius: 4, padding: '6px 18px', cursor: 'pointer', fontSize: 13 }}
>
  새 게임 시작
</button>
```

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat(postgame): auto-navigate on game_end, timeline rendering, restart button"
```

---

## Task 6: Update docs — reflect current 3-goal scope

**Files:**
- Modify: `docs/todo/26-05-03.md` (create new)

- [ ] **Step 1: Create `docs/todo/26-05-03.md`**

```markdown
# RiftBuddy — Current Scope (2026-05-03)

## Three Goals

### Goal 1: In-Game AI Coach
- Hotkeys: Cmd+Shift+B (auto-prompt), Cmd+Shift+Space (push-to-talk voice)
- TTS output via ElevenLabs
- Context-aware planned questions: role-specific, objective-timing, CS/gold/kill cases
- Korean + English support
- Status: ✅ implemented, question_planner expanded

### Goal 2: Draft Pick Recommender
- Auto-reads picks from LCU (role swap detection included)
- Panel 1: Meta tier picks for my role + team-comp-aware LLM recommendation (top 3)
- Panel 2: Opponent champion winrates vs my recommended pick (from op.gg matchup data)
- Panel 3: Team composition analysis (synergy + win conditions)
- Status: ✅ implemented

### Goal 3: Post-Game Analyzer
- Snapshots collected every ~3s during game (via existing polling loop)
- On game end: LLM generates timeline-style feedback with timestamps
- Format: Analysis: [situation] → Feedback: [specific improvement]
- Auto-navigates draft window to post-game screen on game_end event
- Status: ✅ implemented

## Known Gaps / Future Work
- [ ] Korean champion name slugs for edge cases (오공=MonkeyKing, 크산테=KSante)
- [ ] Test full ranked draft flow end-to-end
- [ ] op.gg MCP may return variable field names — monitor and patch `extractNumber` if winrates show as N/A
- [ ] Post-game: same-role opponent stats not available from Live Client (no enemy player stats API)
```

- [ ] **Step 2: Commit**

```bash
git add docs/todo/26-05-03.md docs/superpowers/plans/2026-05-03-riftbuddy-three-goals.md
git commit -m "docs: update scope to three goals, add 26-05-03 todo"
```

---

## Self-Review

**Spec coverage check:**

| Requirement | Task |
|---|---|
| Remove extra overlay tabs (Timers/Gold/Buffs/Ults) | Task 1 + Task 2 |
| Remove auth | Task 1 |
| Delete old docs | Task 1 |
| Expand question_planner per-role + objective timing | Task 3 |
| Draft: role tier list from op.gg | Task 4 (DraftRecommendPanel + /recommend-for-role) |
| Draft: team comp recommendation | Task 4 (TeamCompPanel + LLM in endpoint) |
| Draft: opponent winrate vs my recommended pick | Task 4 (OpponentMatchupPanel + fetchMatchup loop) |
| Draft: role auto-detect + swap detection | Task 4 (DraftPage useEffect on roleLabels) |
| Post-game: timeline-style feedback with timestamps | Task 5a |
| Post-game: auto-show on game end | Task 5b |
| Docs cleanup | Task 6 |

**Type consistency check:**
- `fetchRecommendForRole(ally, enemy, myRole, language?)` — consistent between hook definition and DraftPage call ✅
- `recommendForRole.recommendations[].champion` — used in OpponentMatchupPanel as `recommendForRole?.recommendations?.[0]?.champion` ✅
- `matchups: Record<number, MatchupGuide>` — OpponentMatchupPanel uses `Object.values(matchups).find(m => m.enemyChampion === enemy)` which is correct since matchups are keyed by index ✅
- `loadingRecommend`, `loadingMatchups`, `loadingStrategy` — all added to DraftState and returned from hook ✅

**Placeholder scan:** No TBD/TODO in task steps. All code blocks complete. ✅
