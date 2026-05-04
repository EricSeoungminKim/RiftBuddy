import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from fastapi import FastAPI
from backend.draft.router import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_champion_analysis_returns_200():
    mock_data = {"win_rate": 52.3, "tier": "A"}
    with patch("backend.draft.router.get_champion_analysis", new_callable=AsyncMock, return_value=mock_data):
        res = client.get("/draft/champion-analysis?champion=Rumble&role=TOP")
    assert res.status_code == 200
    assert res.json()["win_rate"] == 52.3


def test_champion_analysis_missing_param_returns_422():
    res = client.get("/draft/champion-analysis?champion=Rumble")
    assert res.status_code == 422


def test_matchup_returns_200():
    mock_data = {"laning_strength": 55.0}
    with patch("backend.draft.router.get_matchup", new_callable=AsyncMock, return_value=mock_data):
        res = client.get("/draft/matchup?my_champion=Rumble&enemy_champion=Darius&role=TOP")
    assert res.status_code == 200
    assert res.json()["laning_strength"] == 55.0


def test_runes_returns_200():
    mock_data = {"primary_path": "Precision", "shards": [5005, 5002, 5001]}
    with patch("backend.draft.router.get_runes", new_callable=AsyncMock, return_value=mock_data):
        res = client.get("/draft/runes?champion=Rumble&role=TOP")
    assert res.status_code == 200
    assert "primary_path" in res.json()


def test_meta_champions_returns_200():
    mock_data = [{"champion": "Darius", "win_rate": 53.0}]
    with patch("backend.draft.router.get_meta_champions", new_callable=AsyncMock, return_value=mock_data):
        res = client.get("/draft/meta-champions?role=TOP")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_team_strategy_returns_strategy():
    mock_advice = "초반 견제를 피하고 6레벨에 교환을 시도하세요."
    with patch("backend.draft.router.get_advice", new_callable=AsyncMock, return_value=mock_advice):
        res = client.post("/draft/team-strategy", json={
            "ally": ["Rumble", "Lee Sin", "Orianna", "Jinx", "Thresh"],
            "enemy": ["Darius", "Vi", "Syndra", "Caitlyn", "Blitzcrank"],
            "my_champion": "Rumble",
            "my_role": "TOP"
        })
    assert res.status_code == 200
    assert "strategy" in res.json()
    assert res.json()["strategy"] == mock_advice


def test_team_strategy_returns_fallback_when_llm_fails():
    with patch("backend.draft.router.get_advice", new_callable=AsyncMock, side_effect=RuntimeError("llm down")):
        res = client.post("/draft/team-strategy", json={
            "ally": ["Shyvana", "Nami", "Galio"],
            "enemy": ["Morgana", "Poppy", "Ashe"],
            "my_champion": "Galio",
            "my_role": "미드"
        })

    assert res.status_code == 200
    assert "Galio" in res.json()["strategy"]


def test_recommend_for_role_falls_back_to_meta_when_llm_output_is_unparseable():
    mock_meta = [
        {"champion": "Ahri", "win_rate": 52.1},
        {"champion_name": "Galio", "win_rate": 51.8},
        {"name": "Orianna", "win_rate": 50.9},
    ]
    with patch("backend.draft.router.get_meta_champions", new_callable=AsyncMock, return_value=mock_meta), \
         patch("backend.draft.router.get_advice", new_callable=AsyncMock, return_value="Use lane control."), \
         patch("backend.draft.router.get_matchup", new_callable=AsyncMock, side_effect=RuntimeError("no matchup")):
        res = client.post("/draft/recommend-for-role", json={
            "ally": ["Shyvana", "Nami", "Galio"],
            "enemy": ["Morgana", "Poppy", "Ashe"],
            "my_role": "미드",
            "language": "en"
        })

    assert res.status_code == 200
    data = res.json()
    assert [item["champion"] for item in data["recommendations"][:2]] == ["Ahri", "Orianna"]
    assert "Galio" not in [item["champion"] for item in data["recommendations"]]
    assert "Counters" in data["recommendations"][0]["reason"] or "OP.GG" in data["recommendations"][0]["reason"]
    assert data["meta"] == ["Ahri", "Galio", "Orianna"]


def test_recommend_for_role_ranks_candidates_by_enemy_matchup_win_rates():
    mock_meta = [
        {"champion": "XinZhao", "win_rate": 52.0},
        {"champion": "LeeSin", "win_rate": 53.0},
        {"champion": "Viego", "win_rate": 54.0},
    ]
    matchup_rates = {
        ("XinZhao", "Karthus"): 54.2,
        ("XinZhao", "Pyke"): 50.1,
        ("LeeSin", "Karthus"): 51.2,
        ("LeeSin", "Pyke"): 52.6,
        ("Viego", "Karthus"): 50.3,
        ("Viego", "Pyke"): 49.8,
    }

    async def matchup_for(my_champion: str, enemy_champion: str, role: str):
        return {"data": {"lane_matchup": {"win_rate": matchup_rates[(my_champion, enemy_champion)]}}}

    with patch("backend.draft.router.get_meta_champions", new_callable=AsyncMock, return_value=mock_meta), \
         patch("backend.draft.router.get_matchup", new_callable=AsyncMock, side_effect=matchup_for):
        res = client.post("/draft/recommend-for-role", json={
            "ally": ["KhaZix", "TwistedFate", "Draven", "Leona"],
            "enemy": ["Karthus", "Pyke"],
            "my_role": "정글",
            "language": "en"
        })

    assert res.status_code == 200
    recommendations = res.json()["recommendations"]
    assert recommendations[0]["champion"] == "LeeSin"
    assert recommendations[0]["winRate"] == 51.9
    assert "Counters Pyke at 52.6% from OP.GG" in recommendations[0]["reason"]
    assert recommendations[1]["champion"] == "XinZhao"
    assert "Counters Karthus at 54.2% from OP.GG" in recommendations[1]["reason"]


def test_bottom_recommendations_prioritize_bot_relevant_enemy_matchups():
    adc_meta = [
        {"champion": "Ashe", "win_rate": 50.4},
        {"champion": "Caitlyn", "win_rate": 50.1},
        {"champion": "Sivir", "win_rate": 50.8},
    ]
    support_meta = [
        {"champion": "Leona", "win_rate": 51.2},
    ]
    matchup_rates = {
        ("Ashe", "Sivir"): 53.8,
        ("Caitlyn", "Sivir"): 50.7,
    }

    async def meta_for(role: str):
        if role == "adc":
            return adc_meta
        if role == "support":
            return support_meta
        return []

    async def matchup_for(my_champion: str, enemy_champion: str, role: str):
        assert enemy_champion == "Sivir"
        return {"data": {"lane_matchup": {"win_rate": matchup_rates[(my_champion, enemy_champion)]}}}

    with patch("backend.draft.router.get_meta_champions", new_callable=AsyncMock, side_effect=meta_for), \
         patch("backend.draft.router.get_matchup", new_callable=AsyncMock, side_effect=matchup_for) as mock_matchup:
        res = client.post("/draft/recommend-for-role", json={
            "ally": ["Qiyana", "Velkoz", "Gangplank", "Caitlyn"],
            "enemy": ["Malzahar", "Urgot", "Sivir"],
            "my_role": "바텀",
            "language": "en"
        })

    assert res.status_code == 200
    data = res.json()
    assert data["recommendations"][0]["champion"] == "Ashe"
    assert data["recommendations"][0]["winRate"] == 53.8
    assert "Counters Sivir at 53.8% from OP.GG" in data["recommendations"][0]["reason"]
    assert "Sivir" not in [item["champion"] for item in data["recommendations"]]
    assert {call.args[1] for call in mock_matchup.await_args_list} == {"Sivir"}


def test_recommend_for_role_returns_defaults_when_opgg_fails():
    with patch("backend.draft.router.get_meta_champions", new_callable=AsyncMock, side_effect=RuntimeError("opgg down")), \
         patch("backend.draft.router.get_matchup", new_callable=AsyncMock, side_effect=RuntimeError("no matchup")):
        res = client.post("/draft/recommend-for-role", json={
            "ally": ["Shyvana", "Nami", "Galio"],
            "enemy": ["Morgana", "Poppy", "Ashe"],
            "my_role": "미드",
            "language": "ko"
        })

    assert res.status_code == 200
    assert len(res.json()["recommendations"]) == 4
    assert "Galio" not in [item["champion"] for item in res.json()["recommendations"]]


def test_ban_counters_extracts_opgg_counter_fields():
    mock_data = {
        "data": {
            "weak_counters": [
                {"champion_name": "Syndra", "win_rate": 46.2},
                {"champion_name": "Cassiopeia", "win_rate": 47.1},
            ]
        }
    }
    with patch("backend.draft.router.get_champion_analysis", new_callable=AsyncMock, return_value=mock_data):
        res = client.get("/draft/ban-counters?champion=Galio&role=mid")

    assert res.status_code == 200
    data = res.json()
    assert data["target"] == "Galio"
    assert data["counters"][0]["champion"] == "Syndra"
    assert data["counters"][0]["source"] == "OP.GG counter analysis"
    assert "Galio" in data["counters"][0]["reason"]


def test_ban_counters_falls_back_to_role_meta_when_hover_counter_data_is_empty():
    mock_analysis = {"data": {"weak_counters": []}}
    mock_meta = [
        {"champion": "Karthus", "tier": "OP", "win_rate": 53.4},
        {"champion": "Viego", "tier": "2", "win_rate": 50.1},
        {"champion": "XinZhao", "tier_data": {"rank": 1, "tier": 1}, "win_rate": 52.2},
    ]
    with patch("backend.draft.router.get_champion_analysis", new_callable=AsyncMock, return_value=mock_analysis), \
         patch("backend.draft.router.get_meta_champions", new_callable=AsyncMock, return_value=mock_meta):
        res = client.get("/draft/ban-counters?champion=KhaZix&role=jungle")

    assert res.status_code == 200
    counters = res.json()["counters"]
    assert counters[0]["champion"] == "Karthus"
    assert counters[0]["source"] == "OP.GG role meta"
    assert "OP.GG marks Karthus as OP" in counters[0]["reason"]


def test_matchup_returns_top_level_win_rate_for_frontend():
    mock_data = {"data": {"summary": {"average_stats": {"win_rate": 0.501}}, "lane_matchup": {"win_rate": 0.527}}}
    with patch("backend.draft.router.get_matchup", new_callable=AsyncMock, return_value=mock_data):
        res = client.get("/draft/matchup?my_champion=Galio&enemy_champion=Ashe&role=mid")

    assert res.status_code == 200
    assert res.json()["winRate"] == 52.7


def test_matchup_does_not_use_generic_summary_win_rate_as_matchup_win_rate():
    mock_data = {"data": {"summary": {"average_stats": {"win_rate": 0.501}}}}
    with patch("backend.draft.router.get_matchup", new_callable=AsyncMock, return_value=mock_data), \
         patch("backend.draft.router.get_champion_analysis", new_callable=AsyncMock, return_value={}):
        res = client.get("/draft/matchup?my_champion=Caitlyn&enemy_champion=Sivir&role=adc")

    assert res.status_code == 200
    assert "winRate" not in res.json()


def test_matchup_uses_named_strong_counter_data_from_opgg_analysis():
    mock_matchup = {"data": {"summary": {"average_stats": {"win_rate": 0.483}}}}
    mock_analysis = {"data": {"strong_counters": [{"champion_name": "Yasuo", "win_rate": 0.531}]}}
    with patch("backend.draft.router.get_matchup", new_callable=AsyncMock, return_value=mock_matchup), \
         patch("backend.draft.router.get_champion_analysis", new_callable=AsyncMock, return_value=mock_analysis):
        res = client.get("/draft/matchup?my_champion=Orianna&enemy_champion=Yasuo&role=mid")

    assert res.status_code == 200
    assert res.json()["winRate"] == 53.1
    assert res.json()["matchupSource"] == "OP.GG champion counter list"


def test_matchup_inverts_named_weak_counter_data_from_opgg_analysis():
    mock_matchup = {"data": {"summary": {"average_stats": {"win_rate": 0.483}}}}
    mock_analysis = {"data": {"weak_counters": [{"champion_name": "Ahri", "win_rate": 0.54}]}}
    with patch("backend.draft.router.get_matchup", new_callable=AsyncMock, return_value=mock_matchup), \
         patch("backend.draft.router.get_champion_analysis", new_callable=AsyncMock, return_value=mock_analysis):
        res = client.get("/draft/matchup?my_champion=Orianna&enemy_champion=Ahri&role=mid")

    assert res.status_code == 200
    assert res.json()["winRate"] == 46.0
    assert res.json()["matchupSource"] == "OP.GG champion counter list"


def test_recommend_for_role_uses_analysis_counter_lists_when_lane_matchup_has_only_generic_data():
    mock_meta = [
        {"champion": "Ahri", "win_rate": 50.0},
        {"champion": "Galio", "win_rate": 50.0},
    ]
    analyses = {
        "Ahri": {"data": {"strong_counters": [{"champion_name": "Yasuo", "win_rate": 0.532}]}},
        "Galio": {"data": {"strong_counters": [{"champion_name": "Yasuo", "win_rate": 0.511}]}},
    }

    async def analysis_for(champion: str, role: str):
        return analyses[champion]

    with patch("backend.draft.router.get_meta_champions", new_callable=AsyncMock, return_value=mock_meta), \
         patch("backend.draft.router.get_matchup", new_callable=AsyncMock, return_value={"data": {"summary": {"average_stats": {"win_rate": 0.5}}}}), \
         patch("backend.draft.router.get_champion_analysis", new_callable=AsyncMock, side_effect=analysis_for):
        res = client.post("/draft/recommend-for-role", json={
            "ally": ["Caitlyn", "Senna", "Brand", "Graves"],
            "enemy": ["Leona", "Nasus", "Ashe", "Yasuo", "Diana"],
            "my_role": "mid",
            "language": "en"
        })

    assert res.status_code == 200
    recommendations = res.json()["recommendations"]
    assert recommendations[0]["champion"] == "Ahri"
    assert recommendations[0]["winRate"] == 53.2
    assert "Counters Yasuo at 53.2% from OP.GG" in recommendations[0]["reason"]
