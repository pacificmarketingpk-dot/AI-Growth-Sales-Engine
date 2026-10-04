import httpx
from sqlalchemy.orm import Session

from app.services.google.oauth import access_token

SHEETS = "https://sheets.googleapis.com/v4/spreadsheets"
DRIVE = "https://www.googleapis.com/drive/v3/files"


async def list_spreadsheets(db: Session, user_id: int) -> list[dict]:
    token = await access_token(db, user_id, "google_sheets")
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get(DRIVE, headers={"Authorization": f"Bearer {token}"},
                        params={"q": "mimeType='application/vnd.google-apps.spreadsheet' and trashed=false",
                                "fields": "files(id,name,modifiedTime)", "pageSize": 50, "orderBy": "modifiedTime desc"})
    r.raise_for_status()
    return r.json().get("files", [])


async def list_sheets(db: Session, user_id: int, spreadsheet_id: str) -> list[str]:
    token = await access_token(db, user_id, "google_sheets")
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get(f"{SHEETS}/{spreadsheet_id}", headers={"Authorization": f"Bearer {token}"},
                        params={"fields": "sheets.properties.title"})
    r.raise_for_status()
    return [s["properties"]["title"] for s in r.json().get("sheets", [])]


async def read_rows(db: Session, user_id: int, spreadsheet_id: str, sheet: str) -> list[list[str]]:
    token = await access_token(db, user_id, "google_sheets")
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(f"{SHEETS}/{spreadsheet_id}/values/{sheet}", headers={"Authorization": f"Bearer {token}"})
    r.raise_for_status()
    return r.json().get("values", [])


async def write_rows(db: Session, user_id: int, spreadsheet_id: str, sheet: str, rows: list[list]) -> int:
    token = await access_token(db, user_id, "google_sheets")
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.put(f"{SHEETS}/{spreadsheet_id}/values/{sheet}!A1", headers={"Authorization": f"Bearer {token}"},
                        params={"valueInputOption": "RAW"}, json={"values": rows})
    r.raise_for_status()
    return r.json().get("updatedRows", 0)
