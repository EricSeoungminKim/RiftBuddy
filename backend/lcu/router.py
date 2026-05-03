import base64
import sys
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

_LOCKFILE_PATHS = {
    "darwin": Path("/Applications/League of Legends.app/Contents/LoL/lockfile"),
    "win32": Path(r"C:\Riot Games\League of Legends\lockfile"),
}


def _read_lockfile() -> dict:
    """Read LCU lockfile and return connection info."""
    os_key = "darwin" if sys.platform == "darwin" else "win32"
    lockfile_path = _LOCKFILE_PATHS.get(os_key)
    if not lockfile_path or not lockfile_path.exists():
        raise HTTPException(status_code=503, detail="League client lockfile not found")
    content = lockfile_path.read_text()
    parts = content.split(":")
    # format: ProcessName:PID:Port:Password:Protocol
    if len(parts) < 5:
        raise HTTPException(status_code=503, detail="Malformed lockfile")
    return {"port": parts[2], "password": parts[3]}


def _make_lcu_client(port: str, password: str) -> httpx.AsyncClient:
    token = base64.b64encode(f"riot:{password}".encode()).decode()
    return httpx.AsyncClient(
        base_url=f"https://127.0.0.1:{port}",
        headers={"Authorization": f"Basic {token}", "Content-Type": "application/json"},
        verify=False,
        timeout=5.0,
    )


class RunePage(BaseModel):
    name: str
    primaryStyleId: int
    subStyleId: int
    selectedPerkIds: list[int]


@router.post("/lcu/apply-runes")
async def apply_runes(page: RunePage):
    """Read LCU lockfile, delete current rune page, create new one."""
    info = _read_lockfile()
    port, password = info["port"], info["password"]

    async with _make_lcu_client(port, password) as client:
        # Get current page id
        resp = await client.get("/lol-perks/v1/currentpage")
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail="Failed to get current rune page")
        current_page = resp.json()
        page_id = current_page.get("id")

        # Delete current page if it exists
        if page_id:
            await client.delete(f"/lol-perks/v1/pages/{page_id}")

        # Create new page
        payload = {
            "name": page.name,
            "primaryStyleId": page.primaryStyleId,
            "subStyleId": page.subStyleId,
            "selectedPerkIds": page.selectedPerkIds,
            "current": True,
            "isActive": True,
            "isDeletable": True,
            "isEditable": True,
        }
        create_resp = await client.post("/lol-perks/v1/pages", json=payload)
        if create_resp.status_code not in (200, 201):
            raise HTTPException(status_code=502, detail=f"Failed to create rune page: {create_resp.text}")

    return {"success": True, "message": f"Rune page '{page.name}' applied"}


@router.get("/lcu/champ-select/status")
async def champ_select_status():
    """Poll-friendly champion select status that avoids noisy 503/404 logs."""
    try:
        return await _read_champ_select_state()
    except HTTPException as exc:
        if exc.status_code == 503:
            return {
                "available": False,
                "inProgress": False,
                "reason": "league_client_unavailable",
                "message": exc.detail,
            }
        if exc.status_code == 404:
            return {
                "available": True,
                "inProgress": False,
                "reason": "not_in_champ_select",
                "message": exc.detail,
            }
        raise


@router.get("/lcu/champ-select")
async def champ_select():
    """Return current champion select state: ally picks, enemy picks, local player cell."""
    state = await _read_champ_select_state()
    state.pop("available", None)
    return state


async def _read_champ_select_state() -> dict:
    info = _read_lockfile()
    port, password = info["port"], info["password"]

    async with _make_lcu_client(port, password) as client:
        resp = await client.get("/lol-champ-select/v1/session")
        if resp.status_code == 404:
            raise HTTPException(status_code=404, detail="Not in champion select")
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail="LCU error")
        session = resp.json()

    champion_id_map = await _get_champion_id_map()
    my_cell = session.get("localPlayerCellId", -1)
    my_team_cells = {player.get("cellId") for player in session.get("myTeam", [])}
    action_by_cell = _pick_actions_by_cell(session)

    ally_slots = _team_slots(session.get("myTeam", []), action_by_cell, champion_id_map)
    enemy_team = session.get("theirTeam", []) or _enemy_team_from_actions(action_by_cell, my_team_cells)
    enemy_slots = _team_slots(enemy_team, action_by_cell, champion_id_map)
    ally = [slot["champion"] for slot in ally_slots if slot.get("champion") and slot.get("completed")]
    enemy = [slot["champion"] for slot in enemy_slots if slot.get("champion") and slot.get("completed")]

    return {
        "available": True,
        "myCell": my_cell,
        "ally": ally,
        "enemy": enemy,
        "allySlots": ally_slots,
        "enemySlots": enemy_slots,
        "inProgress": True,
    }


_champion_id_map_cache: dict[str, str] = {}


async def _get_champion_id_map() -> dict[str, str]:
    """Fetch champion int-id → English name from DDragon (cached per process)."""
    if _champion_id_map_cache:
        return _champion_id_map_cache
    async with httpx.AsyncClient(timeout=5.0) as client:
        ver_resp = await client.get("https://ddragon.leagueoflegends.com/api/versions.json")
        version = ver_resp.json()[0] if ver_resp.status_code == 200 else "16.9.1"
        resp = await client.get(f"https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/champion.json")
        if resp.status_code != 200:
            return {}
        data = resp.json()
    _champion_id_map_cache.update({str(v["key"]): v["id"] for v in data["data"].values()})
    return _champion_id_map_cache


def _pick_actions_by_cell(session: dict) -> dict[int, dict]:
    actions: dict[int, dict] = {}
    for action_group in session.get("actions", []):
        for action in action_group:
            if action.get("type") != "pick":
                continue
            cell_id = action.get("actorCellId", -1)
            champion_id = action.get("championId", 0)
            if cell_id < 0 or not champion_id:
                continue
            existing = actions.get(cell_id)
            if not existing or action.get("completed", False) or not existing.get("completed", False):
                actions[cell_id] = action
    return actions


def _team_slots(team: list[dict], action_by_cell: dict[int, dict], champion_id_map: dict[str, str]) -> list[dict]:
    slots: list[dict] = []
    for index, player in enumerate(team):
        cell_id = player.get("cellId", index)
        action = action_by_cell.get(cell_id, {})
        champion_id = action.get("championId") or player.get("championId") or 0
        champion = champion_id_map.get(str(champion_id), str(champion_id)) if champion_id else ""
        slots.append(
            {
                "cellId": cell_id,
                "slot": index,
                "champion": champion,
                "championId": champion_id,
                "completed": bool(action.get("completed", False)),
                "assignedPosition": player.get("assignedPosition") or player.get("position") or "",
                "summonerId": player.get("summonerId"),
            }
        )
    return slots


def _enemy_team_from_actions(action_by_cell: dict[int, dict], my_team_cells: set[int]) -> list[dict]:
    enemy_cells = sorted(cell_id for cell_id in action_by_cell if cell_id not in my_team_cells)
    return [{"cellId": cell_id} for cell_id in enemy_cells[:5]]
