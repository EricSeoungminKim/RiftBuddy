from backend.context.engine import ContextPacket, build_context_packet
from backend.riot.live_client import GameState


def test_build_context_packet_healthy_player():
    state = GameState(
        current_health=1800,
        max_health=2000,
        gold=2500,
        level=10,
        game_time=600.0,
        champion_name="Rumble",
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
    assert "healthy" in packet.summary.lower()
    assert "Rumble" in packet.summary
    assert "82 CS" in packet.summary
    assert "KDA 3/1/2" in packet.summary


def test_build_context_packet_low_health():
    state = GameState(
        current_health=400, max_health=2000, gold=800, level=5, game_time=300.0
    )
    packet = build_context_packet(state)
    assert packet.health_percent == 20.0
    assert "low health" in packet.summary.lower()
