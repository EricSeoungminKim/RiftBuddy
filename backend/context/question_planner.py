from backend.context.engine import normalize_position
from backend.riot.live_client import GameState


def build_planned_question(state: GameState, language: str = "ko") -> str:
    if language != "ko":
        return _build_english_question(state)
    return _build_korean_question(state)


def _build_korean_question(state: GameState) -> str:
    health_percent = _health_percent(state)
    position = normalize_position(state.assigned_position)
    gold_diff = state.gold_diff
    kda = f"{state.kills}/{state.deaths}/{state.assists}"
    minute = int(state.game_time // 60)
    cs_floor = _expected_cs_floor(state.game_time)
    team_state = _team_state_phrase(gold_diff)

    if health_percent < 35 and state.gold >= 1200:
        return (
            f"{team_state} 나는 {position}이고 체력이 {health_percent:g}%인데 {state.gold:g}골드를 들고 있어. "
            "지금 바로 귀환해야 하는지, 안전하게 한 웨이브나 캠프만 더 보고 귀환해도 되는지 판단해줘."
        )
    if state.gold >= 2200:
        return (
            f"{team_state} 나는 {position}에서 {state.gold:g}골드를 들고 있고 KDA는 {kda}, CS는 {state.creep_score}야. "
            "지금 리콜해서 아이템 스파이크를 만들지, 오브젝트/웨이브를 한 번 더 보고 움직일지 정해줘."
        )
    if position == "정글" and health_percent >= 70 and state.gold < 900:
        return (
            f"{team_state} 나는 정글이고 체력은 {health_percent:g}%, 골드는 {state.gold:g}야. "
            "지금 내 정글링 루트, 갱 각, 용/전령 준비, 시야 중 어디에 시간을 써야 하는지 구체적으로 말해줘."
        )
    if position == "정글":
        return (
            f"{team_state} 나는 정글이고 KDA는 {kda}, 골드는 {state.gold:g}, 레벨은 {state.level}이야. "
            "다음 60초 동안 정글링, 갱, 오브젝트, 시야 중 무엇을 먼저 해야 하는지 우선순위로 알려줘."
        )
    if health_percent < 35:
        return f"{team_state} 나는 {position}이고 체력이 {health_percent:g}%야. 라인에 남아도 되는지, 바로 귀환/합류해야 하는지 판단해줘."
    if state.creep_score < cs_floor:
        return (
            f"{minute}분인데 CS가 {state.creep_score}라 낮은 편이야. {team_state} "
            f"{position}에서 웨이브를 밀어야 하는지, 당겨야 하는지, 로밍/합류를 포기하고 파밍해야 하는지 알려줘."
        )
    if position == "서폿" and state.ward_score < 5:
        return f"{team_state} 나는 서폿이고 시야 점수가 {state.ward_score:g}로 낮아. 지금 어느 쪽 강가/정글 시야를 먼저 잡아야 하는지 알려줘."
    if gold_diff >= 1500:
        return (
            f"우리 팀이 약 {gold_diff:g}골드 앞서지만, 나는 {position}에서 KDA {kda}, 골드 {state.gold:g}야. "
            "지금 리드를 더 굴릴 구체적인 플레이 하나와 피해야 할 리스크 하나를 알려줘."
        )
    if gold_diff <= -1500:
        return (
            f"우리 팀이 약 {abs(gold_diff):g}골드 밀리고 있고, 나는 {position}에서 KDA {kda}, 골드 {state.gold:g}야. "
            "지금 역전각을 만들 수 있는 현실적인 선택지 하나와 버려야 할 플레이 하나를 알려줘."
        )
    return (
        f"나는 {position}이고 {minute}분 현재 KDA {kda}, CS {state.creep_score}, 골드 {state.gold:g}야. "
        "지금 가장 가치 높은 다음 행동을 하나만 구체적으로 골라줘."
    )


def _build_english_question(state: GameState) -> str:
    health_percent = _health_percent(state)
    if health_percent < 35 and state.gold >= 1200:
        return f"I am low HP at {health_percent:g}% and holding {state.gold:g} gold. Should I recall now or stay for one more play?"
    if state.gold_diff >= 1500:
        return "My team seems ahead in gold. What should I do now to safely close out the lead?"
    if state.gold_diff <= -1500:
        return "My team seems behind in gold. What should I prioritize now to create a comeback?"
    if normalize_position(state.assigned_position) == "정글":
        return "I am jungle. Should I prioritize farming route, gank, objective, or vision right now?"
    return "What should I do right now based on the current game state?"


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
