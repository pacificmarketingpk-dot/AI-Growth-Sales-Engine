import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.session import SessionLocal
from app.models import AnalysisJob, Outreach, Prospect, ProspectAnalysis, ProspectStatus, UserSettings
from app.services.ai import prompts
from app.services.ai.factory import provider_for_user
from app.services.ai.provider import AIError
from app.services.ai.schemas import ProspectAnalysisResult, WebsiteFindings
from app.services.audit import audit
from app.services.scoring import lead_category
from app.services.website import fetch_homepage

log = logging.getLogger(__name__)
PROSPECT_FIELDS = ["name", "company", "job_title", "industry", "country", "company_size", "website",
                   "company_description", "notes", "linkedin_url"]
OUTREACH_KINDS = ["connection_message", "follow_up_1", "follow_up_2"]


class AlreadyAnalyzed(Exception):
    pass


def _settings(db: Session, user_id: int) -> UserSettings:
    s = db.query(UserSettings).filter_by(user_id=user_id).first()
    if not s:
        s = UserSettings(user_id=user_id)
        db.add(s)
        db.flush()
    return s


async def analyze_prospect(db: Session, prospect: Prospect, *, force: bool = False,
                           include_website: bool = True, provider=None) -> ProspectAnalysis:
    if prospect.analyses and not force:
        raise AlreadyAnalyzed("Prospect already analyzed. Confirm re-analysis to run it again.")
    us = _settings(db, prospect.user_id)
    provider = provider or provider_for_user(us, prospect.is_demo)
    previous_status = prospect.status
    prospect.status = ProspectStatus.ANALYZING
    db.commit()
    try:
        website_raw, website_findings, ws_tokens = None, None, (0, 0)
        if include_website and prospect.website and not prospect.is_demo:
            website_raw = await fetch_homepage(prospect.website)
            if website_raw:
                try:
                    wres = await provider.generate(prompts.WEBSITE_SYSTEM, str(website_raw), WebsiteFindings)
                    website_findings = wres.data.model_dump()
                    ws_tokens = (wres.input_tokens, wres.output_tokens)
                except AIError:
                    website_findings = None

        data = {f: getattr(prospect, f) for f in PROSPECT_FIELDS}
        consultant = {"role": us.role, "business": us.business}
        website_ctx = None
        if website_raw:
            website_ctx = {"findings": website_findings, "facts": {k: website_raw[k] for k in
                           ("title", "meta_description", "h1", "cta_candidates", "form_count", "has_viewport_meta")}}
        result = await provider.generate(prompts.analysis_system(us.message_tone),
                                         prompts.analysis_user(data, consultant, website_ctx),
                                         ProspectAnalysisResult, retries=get_settings().ai_max_retries)
    except Exception:
        prospect.status = previous_status if previous_status != ProspectStatus.ANALYZING else ProspectStatus.NEW
        db.commit()
        raise

    out: ProspectAnalysisResult = result.data
    version = (prospect.analyses[-1].analysis_version + 1) if prospect.analyses else 1
    analysis = ProspectAnalysis(
        prospect_id=prospect.id, analysis_version=version, lead_score=out.lead_score,
        category=lead_category(out.lead_score), score_breakdown=out.score_breakdown.model_dump(),
        result=out.model_dump(), website_analysis=website_findings, website_retrieved=bool(website_raw),
        confidence=out.confidence, provider=result.provider, model=result.model,
        input_tokens=result.input_tokens + ws_tokens[0], output_tokens=result.output_tokens + ws_tokens[1],
        estimated_cost=result.estimated_cost,
    )
    db.add(analysis)
    prospect.lead_score = out.lead_score
    if previous_status in (ProspectStatus.NEW, ProspectStatus.ANALYZING, ProspectStatus.ANALYZED):
        prospect.status = ProspectStatus.ANALYZED
    else:
        prospect.status = previous_status

    # Store generated drafts (replace un-sent, un-edited drafts only)
    for kind in OUTREACH_KINDS:
        existing = next((o for o in prospect.outreach if o.kind == kind and not o.contacted_at), None)
        if existing and existing.edited:
            continue
        if existing:
            existing.message = getattr(out, kind)
        else:
            db.add(Outreach(prospect_id=prospect.id, kind=kind, message=getattr(out, kind)))
    audit(db, prospect.user_id, "prospect.analyzed", "prospect", prospect.id,
          version=version, score=out.lead_score, model=result.model)
    audit(db, prospect.user_id, "message.generated", "prospect", prospect.id, kinds=OUTREACH_KINDS)
    db.commit()
    db.refresh(prospect)
    return analysis


# ---------- bulk queue: bounded concurrency, retries handled in provider, failures isolated ----------
_semaphore: asyncio.Semaphore | None = None


def _sem() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(max(1, get_settings().ai_max_concurrency))
    return _semaphore


async def run_bulk_job(job_id: int, force: bool = False, session_factory=SessionLocal, provider=None) -> None:
    db = session_factory()
    try:
        job = db.get(AnalysisJob, job_id)
        job.status = "running"
        db.commit()
        for pid in job.prospect_ids:
            async with _sem():
                p = db.get(Prospect, pid)
                try:
                    if not p or p.user_id != job.user_id:
                        raise ValueError("Prospect not found")
                    await analyze_prospect(db, p, force=force, provider=provider)
                    job.completed += 1
                except AlreadyAnalyzed:
                    job.completed += 1
                    job.errors = job.errors + [{"prospect_id": pid, "error": "Skipped: already analyzed"}]
                except Exception as e:  # keep going with the rest
                    db.rollback()
                    job = db.get(AnalysisJob, job_id)
                    job.failed += 1
                    msg = str(e) if isinstance(e, (AIError, ValueError)) else "Unexpected error"
                    job.errors = job.errors + [{"prospect_id": pid, "error": msg[:300]}]
                    log.exception("bulk analysis failed for prospect %s", pid)
                job.updated_at = datetime.now(timezone.utc)
                db.commit()
        job.status = "done"
        db.commit()
    finally:
        db.close()
