"""CSV import: validate -> preview -> detect duplicates -> confirm -> import."""
import csv
import io
import re

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Prospect

FIELD_ALIASES = {
    "name": ["name", "full name", "full_name", "contact"],
    "linkedin_url": ["linkedin url", "linkedin_url", "linkedin", "linkedin profile"],
    "company": ["company", "company name", "organization"],
    "job_title": ["job title", "job_title", "title", "position", "role"],
    "industry": ["industry"],
    "country": ["country", "location"],
    "company_size": ["company size", "company_size", "employees", "size"],
    "website": ["website", "url", "domain", "company website"],
    "email": ["email", "email address", "e-mail"],
    "notes": ["notes", "note", "comments"],
}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MAX_ROWS = 5000


def _norm_url(u: str | None) -> str:
    return (u or "").lower().strip().rstrip("/").replace("https://", "").replace("http://", "").replace("www.", "")


def parse_csv(content: bytes) -> list[dict]:
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("The file has no header row.")
    header_map = {}
    for h in reader.fieldnames:
        key = (h or "").strip().lower()
        for field, aliases in FIELD_ALIASES.items():
            if key in aliases:
                header_map[h] = field
    if "name" not in header_map.values():
        raise ValueError("A 'Name' column is required.")
    rows = []
    for i, raw in enumerate(reader):
        if i >= MAX_ROWS:
            break
        row = {field: (raw.get(h) or "").strip()[:500] for h, field in header_map.items()}
        rows.append(row)
    return rows


def validate_row(row: dict) -> list[str]:
    errors = []
    if not row.get("name"):
        errors.append("Name is missing")
    if row.get("email") and not EMAIL_RE.match(row["email"]):
        errors.append("Email is not valid")
    if row.get("linkedin_url") and "linkedin.com" not in row["linkedin_url"].lower():
        errors.append("LinkedIn URL is not a linkedin.com address")
    return errors


def preview(db: Session, user_id: int, rows: list[dict]) -> list[dict]:
    existing = db.query(Prospect.email, Prospect.linkedin_url, Prospect.name, Prospect.company).filter(
        Prospect.user_id == user_id).all()
    emails = {e.lower() for e, *_ in existing if e}
    urls = {_norm_url(u) for _, u, *_ in existing if u}
    name_co = {(n.lower(), (c or "").lower()) for _, _, n, c in existing}
    seen_emails, seen_urls, seen_nc = set(), set(), set()
    out = []
    for idx, row in enumerate(rows):
        errors = validate_row(row)
        email, url = (row.get("email") or "").lower(), _norm_url(row.get("linkedin_url"))
        nc = ((row.get("name") or "").lower(), (row.get("company") or "").lower())
        duplicate = None
        if email and (email in emails or email in seen_emails):
            duplicate = "email"
        elif url and (url in urls or url in seen_urls):
            duplicate = "linkedin_url"
        elif nc[0] and (nc in name_co or nc in seen_nc):
            duplicate = "name_company"
        if email:
            seen_emails.add(email)
        if url:
            seen_urls.add(url)
        seen_nc.add(nc)
        out.append({"row": idx + 1, "data": row, "errors": errors, "duplicate": duplicate,
                    "status": "invalid" if errors else ("duplicate" if duplicate else "ready")})
    return out


def import_rows(db: Session, user_id: int, rows: list[dict], skip_rows: set[int], source: str = "csv") -> dict:
    result = {"imported": 0, "duplicates": 0, "invalid": 0, "skipped": 0, "ids": []}
    for item in preview(db, user_id, rows):
        if item["row"] in skip_rows:
            result["skipped"] += 1
            continue
        if item["status"] == "invalid":
            result["invalid"] += 1
            continue
        if item["status"] == "duplicate":
            result["duplicates"] += 1
            continue
        d = {k: (v or None) for k, v in item["data"].items()}
        p = Prospect(user_id=user_id, source=source, **d)
        db.add(p)
        db.flush()
        result["ids"].append(p.id)
        result["imported"] += 1
    return result
