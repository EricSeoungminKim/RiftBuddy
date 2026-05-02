import base64
import platform
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


@router.get("/lcu/champ-select")
async def champ_select():
    """Return current champion select state: ally picks, enemy picks, local player cell."""
    info = _read_lockfile()
    port, password = info["port"], info["password"]

    async with _make_lcu_client(port, password) as client:
        resp = await client.get("/lol-champ-select/v1/session")
        if resp.status_code == 404:
            raise HTTPException(status_code=404, detail="Not in champion select")
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail="LCU error")
        session = resp.json()

    my_cell = session.get("localPlayerCellId", -1)
    ally_picks: list[dict] = []
    enemy_picks: list[dict] = []

    for action_group in session.get("actions", []):
        for action in action_group:
            if action.get("type") != "pick":
                continue
            cell_id = action.get("actorCellId", -1)
            champion_id = action.get("championId", 0)
            completed = action.get("completed", False)
            if champion_id == 0:
                continue
            entry = {"cellId": cell_id, "championId": champion_id, "completed": completed}
            # Determine ally vs enemy by team membership
            my_team = {p["cellId"] for p in session.get("myTeam", [])}
            if cell_id in my_team:
                ally_picks.append(entry)
            else:
                enemy_picks.append(entry)

    # Resolve champion IDs to names via DDragon
    champion_id_map = await _get_champion_id_map()

    def resolve(picks: list[dict]) -> list[str]:
        return [champion_id_map.get(str(p["championId"]), str(p["championId"])) for p in picks]

    return {
        "myCell": my_cell,
        "ally": resolve(ally_picks),
        "enemy": resolve(enemy_picks),
        "inProgress": True,
    }


async def _get_champion_id_map() -> dict[str, str]:
    """Fetch champion int-id → English name from DDragon."""
    url = "https://ddragon.leagueoflegends.com/cdn/14.24.1/data/en_US/champion.json"
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(url)
        if resp.status_code != 200:
            return {}
        data = resp.json()
    return {str(v["key"]): v["id"] for v in data["data"].values()}
