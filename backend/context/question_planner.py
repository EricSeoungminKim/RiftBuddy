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
