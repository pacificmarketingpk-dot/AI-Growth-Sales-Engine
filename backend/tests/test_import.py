CSV = b"""Name,LinkedIn URL,Company,Job Title,Email,Website
Sam Lee,https://linkedin.com/in/samlee,Acme,CEO,sam@acme.io,acme.io
Sam Lee,https://linkedin.com/in/samlee2,Acme,CEO,sam@acme.io,acme.io
,https://linkedin.com/in/nobody,NoName,CTO,,
Bad Email,,Beta,CMO,not-an-email,
Rita Ray,https://www.linkedin.com/in/rita/,Gamma,Founder,,=HYPERLINK("x")
"""


def upload(c, dry_run=True, skip="[]", content=CSV, name="p.csv"):
    return c.post("/api/import/csv", files={"file": (name, content, "text/csv")},
                  data={"dry_run": str(dry_run).lower(), "skip_rows": skip})


def test_preview_flags_duplicates_and_invalid(authed):
    r = upload(authed).json()
    statuses = [row["status"] for row in r["rows"]]
    assert statuses == ["ready", "duplicate", "invalid", "invalid", "ready"]
    assert r["summary"] == {"ready": 2, "duplicate": 1, "invalid": 2}


def test_import_and_reimport_detects_existing(authed):
    r = upload(authed, dry_run=False).json()
    assert (r["imported"], r["duplicates"], r["invalid"], r["skipped"]) == (2, 1, 2, 0)
    r = upload(authed, dry_run=False).json()
    assert r["imported"] == 0 and r["duplicates"] == 3


def test_skip_rows(authed):
    r = upload(authed, dry_run=False, skip="[1]").json()
    assert r["imported"] == 1 and r["skipped"] == 1


def test_linkedin_url_normalised_for_duplicates(authed):
    authed.post("/api/prospects", json={"name": "X", "linkedin_url": "https://linkedin.com/in/rita"})
    rows = upload(authed).json()["rows"]
    assert rows[4]["duplicate"] == "linkedin_url"


def test_rejects_non_csv_and_missing_name_column(authed):
    assert upload(authed, name="p.txt").status_code == 422
    assert upload(authed, content=b"Company,Email\nAcme,a@b.co\n").status_code == 422


def test_export_neutralises_formulas(authed):
    upload(authed, dry_run=False)
    body = authed.get("/api/export/csv").text
    assert "lead_score" in body.splitlines()[0]
    assert "Rita Ray" in body and "'=HYPERLINK" in body
