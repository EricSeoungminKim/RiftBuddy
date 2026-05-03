from backend.context.question_planner import build_planned_question
from backend.riot.live_client import GameState


def test_planned_question_prioritizes_low_health_and_high_gold():
    state = GameState(current_health=300, max_health=1000, gold=1600, level=7, game_time=480)

    question = build_planned_question(state, "ko")

    assert "체력" in question
    assert "골드" in question
    assert "귀환" in question


def test_planned_question_uses_ahead_global_gold_context():
    state = GameState(current_health=900, max_health=1000, gold=700, level=8, game_time=600, gold_diff=2200, creep_score=70)

    question = build_planned_question(state, "ko")

    assert "앞서" in question
    assert "구체적인 플레이" in question


def test_planned_question_uses_behind_global_gold_context():
    state = GameState(current_health=900, max_health=1000, gold=700, level=8, game_time=600, gold_diff=-2200, creep_score=70)

    question = build_planned_question(state, "ko")

    assert "밀리" in question
    assert "역전" in question


def test_planned_question_uses_jungle_route_when_healthy_low_gold():
    state = GameState(
        current_health=900,
        max_health=1000,
        gold=500,
        level=5,
        game_time=360,
        assigned_position="JUNGLE",
    )

    question = build_planned_question(state, "ko")

    assert "정글" in question
    assert "정글링 루트" in question
