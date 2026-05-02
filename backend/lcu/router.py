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
