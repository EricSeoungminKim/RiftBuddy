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
    q = build_planned_question(_state(assigned_position="bottom", kills=3, deaths=0, game_time=480.0), "ko")
    assert len(q) > 20


def test_objective_timing_pre_dragon():
    # game_time ~4:45 = dragon spawns at 5:00, should detect objective window
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
