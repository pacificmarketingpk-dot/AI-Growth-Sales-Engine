import csv
import io
import json

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.database.session import get_db
from app.models import Integration, Prospect, User
from app.services import csv_import
from app.services.audit import audit
from app.services.google import sheets
from app.services.google.oauth import GoogleNotConnected

router = APIRouter(prefix="/api", tags=["import-export"])
MAX_UPLOAD = 5 * 1024 * 1024
EXPORT_COLUMNS = ["id", "name", "company", "job_title", "industry", "country", "company_size", "website", "email",
                  "linkedin_url", "status", "source", "lead_score", "category", "business_problem",
                  "growth_opportunity", "primary_service", "secondary_service", "confidence", "connection_message",
                  "is_demo", "created_at", "last_contacted_at"]


def _safe_cell(v) -> str:
    """Neutralise spreadsheet formula injection."""
    s = "" if v is None else str(v)
    return "'" + s if s[:1] in ("=", "+", "-", "@", "\t", "\r") else s


@router.post("/import/csv")
async def import_csv(file: UploadFile = File(...), dry_run: bool = Form(True), skip_rows: str = Form("[]"),
                     user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    content = await file.read(MAX_UPLOAD + 1)
    if len(content) > MAX_UPLOAD:
        raise HTTPException(413, "File is larger than 5 MB.")
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(422, "Upload a .csv file.")
    try:
        rows = csv_import.parse_csv(content)
        skip = {int(x) for x in json.loads(skip_rows or "[]")}
    except (ValueError, TypeError) as e:
        raise HTTPException(422, str(e))
    if dry_run:
        items = csv_import.preview(db, user.id, rows)
        summary = {k: sum(1 for i in items if i["status"] == k) for k in ("ready", "duplicate", "invalid")}
        return {"rows": items, "summary": summary}
    result = csv_import.import_rows(db, user.id, rows, skip, source="csv")
    audit(db, user.id, "prospect.imported", "prospect", None, source="csv",
          **{k: v for k, v in result.items() if k != "ids"})
    db.commit()
    return result


def _export_rows(db: Session, user_id: int, include_demo: bool) -> list[list]:
    q = db.query(Prospect).filter(Prospect.user_id == user_id)
    if not include_demo:
        q = q.filter(Prospect.is_demo.is_(False))
    out = [EXPORT_COLUMNS]
    for p in q.order_by(Prospect.id):
        a = p.latest_analysis
        r = a.result if a else {}
        vals = {**{c: getattr(p, c, None) for c in EXPORT_COLUMNS}, "status": p.status.value,
                "category": a.category if a else None, "confidence": a.confidence if a else None,
                **{k: r.get(k) for k in ("business_problem", "growth_opportunity", "primary_service",
                                         "secondary_service", "connection_message")}}
        out.append([_safe_cell(vals.get(c)) for c in EXPORT_COLUMNS])
    return out


@router.get("/export/csv")
def export_csv(include_demo: bool = False, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    buf = io.StringIO()
    csv.writer(buf).writerows(_export_rows(db, user.id, include_demo))
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=prospects.csv"})


# ---------- Google Sheets ----------
def _sheets_error(e: Exception) -> HTTPException:
    if isinstance(e, GoogleNotConnected):
        return HTTPException(409, "Google Sheets is not connected. Connect it in Settings.")
    return HTTPException(502, "Google Sheets is unavailable right now.")


@router.get("/sheets/spreadsheets")
async def list_spreadsheets(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return await sheets.list_spreadsheets(db, user.id)
    except (GoogleNotConnected, httpx.HTTPError) as e:
        raise _sheets_error(e)


@router.get("/sheets/{spreadsheet_id}/tabs")
async def list_tabs(spreadsheet_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return await sheets.list_sheets(db, user.id, spreadsheet_id)
    except (GoogleNotConnected, httpx.HTTPError) as e:
        raise _sheets_error(e)


class SheetSyncIn(BaseModel):
    spreadsheet_id: str = Field(min_length=10, max_length=200, pattern=r"^[A-Za-z0-9_-]+$")
    sheet: str = Field(min_length=1, max_length=100)
    dry_run: bool = True


@router.post("/sheets/sync")
async def sync_sheet(data: SheetSyncIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        values = await sheets.read_rows(db, user.id, data.spreadsheet_id, data.sheet)
    except (GoogleNotConnected, httpx.HTTPError) as e:
        raise _sheets_error(e)
    if not values:
        raise HTTPException(422, "That sheet is empty.")
    buf = io.StringIO()
    csv.writer(buf).writerows(values)
    try:
        rows = csv_import.parse_csv(buf.getvalue().encode())
    except ValueError as e:
        raise HTTPException(422, str(e))
    integ = db.query(Integration).filter_by(user_id=user.id, provider="google_sheets").first()
    if integ:
        integ.config = {**(integ.config or {}), "spreadsheet_id": data.spreadsheet_id, "sheet": data.sheet}
    if data.dry_run:
        items = csv_import.preview(db, user.id, rows)
        db.commit()
        return {"rows": items, "summary": {k: sum(1 for i in items if i["status"] == k)
                                           for k in ("ready", "duplicate", "invalid")}}
    result = csv_import.import_rows(db, user.id, rows, set(), source="google_sheets")
    audit(db, user.id, "prospect.imported", "prospect", None, source="google_sheets",
          **{k: v for k, v in result.items() if k != "ids"})
    db.commit()
    return result


@router.post("/sheets/export")
async def export_sheet(data: SheetSyncIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = _export_rows(db, user.id, include_demo=False)
    try:
        n = await sheets.write_rows(db, user.id, data.spreadsheet_id, data.sheet, rows)
    except (GoogleNotConnected, httpx.HTTPError) as e:
        raise _sheets_error(e)
    audit(db, user.id, "prospect.exported", "prospect", None, destination="google_sheets", rows=n)
    db.commit()
    return {"updated_rows": n}
