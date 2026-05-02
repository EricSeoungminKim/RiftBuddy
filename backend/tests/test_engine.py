from backend.context.engine import ContextPacket, build_context_packet
from backend.riot.live_client import GameState


def test_build_context_packet_healthy_player():
    state = GameState(
        current_health=1800,
        max_health=2000,
        gold=2500,
        level=10,
        game_time=600.0,
        champion_name="럼블",
        position="BOTTOM",
        assigned_position="BOTTOM",
        ally_champions=("럼블", "소나"),
        enemy_champions=("니달리", "갈리오"),
        all_champions=("럼블", "소나", "니달리", "갈리오"),
        kills=3,
        deaths=1,
        assists=2,
        creep_score=82,
        items=("Doran's Shield", "Boots"),
    )
    packet = build_context_packet(state)
    assert isinstance(packet, ContextPacket)
    assert packet.health_percent == 90.0
    assert packet.gold == 2500
    assert packet.game_time_minutes == 10.0
    assert "체력 안정" in packet.summary
    assert "럼블" in packet.summary
    assert "내 배정 포지션 바텀" in packet.summary
    assert "현재 표시 포지션 바텀" in packet.summary
    assert "현재 게임 챔피언: 럼블, 소나, 니달리, 갈리오" in packet.summary
    assert "상대 챔피언: 니달리, 갈리오" in packet.summary
    assert "CS 82" in packet.summary
    assert "KDA 3/1/2" in packet.summary


def test_build_context_packet_low_health():
    state = GameState(
        current_health=400, max_health=2000, gold=800, level=5, game_time=300.0
    )
    packet = build_context_packet(state)
    assert packet.health_percent == 20.0
    assert "체력 낮음" in packet.summary


def test_context_packet_includes_champion_and_position():
    state = GameState(
        current_health=1000,
        max_health=2000,
        gold=1500,
        level=7,
        game_time=300,
        champion_name="Renekton",
        assigned_position="TOP",
        kills=2,
        deaths=1,
        assists=3,
        creep_score=50,
    )
    packet = build_context_packet(state)
    assert packet.champion_name == "Renekton"
    assert packet.assigned_position == "TOP"
    assert packet.creep_score == 50
