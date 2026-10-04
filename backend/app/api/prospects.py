import asyncio
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from app.api.common import ai_http_error, prospect_detail, prospect_out
from app.auth.deps import get_current_user, get_owned_prospect
from app.database.session import get_db
from app.models import (AnalysisJob, LeadQualification, Outreach, Prospect, ProspectAnalysis, ProspectStatus,
                        User, UserSettings)
from app.schemas.api import (AnalysisOut, BulkAnalyzeIn, MarkContactedIn, OutreachOut, OutreachUpdate,
                             ProspectCreate, ProspectDetail, ProspectList, ProspectUpdate, QualificationIn)
from app.services import analysis_service
from app.services.ai import prompts
from app.services.ai.factory import provider_for_user
from app.services.ai.schemas import MessageRegeneration
from app.services.audit import audit
from app.services.scoring import qualification_score, qualification_status
from app.utils.rate_limit import ai_limiter

router = APIRouter(prefix="/api", tags=["prospects"])
_background: set = set()


@router.get("/prospects", response_model=ProspectList)
def list_prospects(q: str = "", status: ProspectStatus | None = None, min_score: int | None = None,
                   analyzed: bool | None = None, demo: bool | None = None,
                   sort: str = Query("created_at", pattern="^(created_at|lead_score|name|company|updated_at)$"),
                   order: str = Query("desc", pattern="^(asc|desc)$"),
                   limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0),
                   user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(Prospect).filter(Prospect.user_id == user.id)
    if q:
        like = f"%{q.strip()[:100]}%"
        query = query.filter(or_(Prospect.name.ilike(like), Prospect.company.ilike(like),
                                 Prospect.email.ilike(like), Prospect.job_title.ilike(like)))
    if status:
        query = query.filter(Prospect.status == status)
    if min_score is not None:
        query = query.filter(Prospect.lead_score >= min_score)
    if analyzed is not None:
        query = query.filter(Prospect.lead_score.isnot(None) if analyzed else Prospect.lead_score.is_(None))
    if demo is not None:
        query = query.filter(Prospect.is_demo == demo)
    total = query.count()
    col = getattr(Prospect, sort)
    col = col.desc().nullslast() if order == "desc" else col.asc().nullsfirst()
    items = query.options(selectinload(Prospect.analyses)).order_by(col, Prospect.id.desc()).offset(offset).limit(limit).all()
    return {"items": [prospect_out(p) for p in items], "total": total}


@router.post("/prospects", response_model=ProspectDetail, status_code=201)
def create_prospect(data: ProspectCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = Prospect(user_id=user.id, source="manual", **data.model_dump())
    db.add(p)
    db.flush()
    audit(db, user.id, "prospect.created", "prospect", p.id, name=p.name)
    db.commit()
    db.refresh(p)
    return prospect_detail(p)


@router.get("/prospects/{prospect_id}", response_model=ProspectDetail)
def get_prospect(prospect_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return prospect_detail(get_owned_prospect(prospect_id, db, user))


@router.put("/prospects/{prospect_id}", response_model=ProspectDetail)
def update_prospect(prospect_id: int, data: ProspectUpdate, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    p = get_owned_prospect(prospect_id, db, user)
    changes = data.model_dump(exclude_unset=True)
    if "name" in changes and not changes["name"]:
        raise HTTPException(422, "Name cannot be empty")
    old_status = p.status
    for k, v in changes.items():
        setattr(p, k, v)
    if "status" in changes and changes["status"] != old_status:
        if changes["status"] == ProspectStatus.CONTACTED and not p.last_contacted_at:
            p.last_contacted_at = datetime.now(timezone.utc)
        audit(db, user.id, "prospect.status_changed", "prospect", p.id, old=old_status.value, new=p.status.value)
    audit(db, user.id, "prospect.updated", "prospect", p.id, fields=list(changes))
    db.commit()
    db.refresh(p)
    return prospect_detail(p)


@router.delete("/prospects/{prospect_id}", status_code=204)
def delete_prospect(prospect_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = get_owned_prospect(prospect_id, db, user)
    audit(db, user.id, "prospect.deleted", "prospect", p.id, name=p.name)
    db.delete(p)
    db.commit()


# ---------- analysis ----------
@router.post("/prospects/{prospect_id}/analyze", response_model=ProspectDetail)
async def analyze(prospect_id: int, request: Request, force: bool = False, include_website: bool = True,
                  user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ai_limiter.check(f"ai:{user.id}")
    p = get_owned_prospect(prospect_id, db, user)
    try:
        await analysis_service.analyze_prospect(db, p, force=force, include_website=include_website,
                                                provider=getattr(request.app.state, "ai_override", None))
    except analysis_service.AlreadyAnalyzed as e:
        raise HTTPException(409, str(e))
    except Exception as e:
        raise ai_http_error(e)
    db.refresh(p)
    return prospect_detail(p)


@router.get("/prospects/{prospect_id}/analyses", response_model=list[AnalysisOut])
def analysis_history(prospect_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_owned_prospect(prospect_id, db, user).analyses


@router.post("/prospects/bulk-analyze")
async def bulk_analyze(data: BulkAnalyzeIn, request: Request, background: BackgroundTasks,
                       user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ids = list(dict.fromkeys(data.prospect_ids))
    owned = {pid for (pid,) in db.query(Prospect.id).filter(Prospect.user_id == user.id, Prospect.id.in_(ids))}
    ids = [i for i in ids if i in owned]
    if not ids:
        raise HTTPException(404, "No matching prospects")
    job = AnalysisJob(user_id=user.id, prospect_ids=ids, total=len(ids), errors=[])
    db.add(job)
    db.commit()
    factory = getattr(request.app.state, "session_factory", None)
    kwargs = {"force": data.force, "provider": getattr(request.app.state, "ai_override", None)}
    if factory:
        kwargs["session_factory"] = factory
    task = asyncio.create_task(analysis_service.run_bulk_job(job.id, **kwargs))
    _background.add(task)
    task.add_done_callback(_background.discard)
    return {"job_id": job.id, "total": job.total}


@router.get("/analysis-jobs/{job_id}")
def job_status(job_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.get(AnalysisJob, job_id)
    if not job or job.user_id != user.id:
        raise HTTPException(404, "Job not found")
    db.refresh(job)
    return {"id": job.id, "status": job.status, "total": job.total, "completed": job.completed,
            "failed": job.failed, "errors": job.errors}


@router.get("/analysis/usage")
def usage(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(ProspectAnalysis).join(Prospect).filter(Prospect.user_id == user.id).all()
    return {"analyses": len(rows), "input_tokens": sum(r.input_tokens for r in rows),
            "output_tokens": sum(r.output_tokens for r in rows),
            "estimated_cost": round(sum(r.estimated_cost for r in rows), 4)}


# ---------- outreach ----------
def _owned_outreach(outreach_id: int, db: Session, user: User) -> Outreach:
    o = db.get(Outreach, outreach_id)
    if not o or o.prospect.user_id != user.id:
        raise HTTPException(404, "Message not found")
    return o


@router.put("/outreach/{outreach_id}", response_model=OutreachOut)
def edit_outreach(outreach_id: int, data: OutreachUpdate, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    o = _owned_outreach(outreach_id, db, user)
    if data.message is not None and data.message != o.message:
        o.message, o.edited = data.message, True
    if data.channel:
        o.channel = data.channel
    if data.response is not None:
        o.response = data.response
    db.commit()
    return o


@router.post("/outreach/{outreach_id}/regenerate", response_model=OutreachOut)
async def regenerate(outreach_id: int, request: Request, user: User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    ai_limiter.check(f"ai:{user.id}")
    o = _owned_outreach(outreach_id, db, user)
    p = o.prospect
    us = db.query(UserSettings).filter_by(user_id=user.id).first() or UserSettings(user_id=user.id)
    provider = getattr(request.app.state, "ai_override", None) or provider_for_user(us, p.is_demo)
    ctx = {"kind": o.kind, "previous": o.message,
           "prospect": {k: getattr(p, k) for k in ("name", "company", "job_title", "industry", "country")},
           "analysis": (p.latest_analysis.result if p.latest_analysis else None)}
    try:
        res = await provider.generate(prompts.regenerate_system(us.message_tone), str(ctx), MessageRegeneration)
    except Exception as e:
        raise ai_http_error(e)
    o.message, o.edited = res.data.message, False
    audit(db, user.id, "message.generated", "prospect", p.id, kind=o.kind, regenerated=True)
    db.commit()
    return o


@router.post("/prospects/{prospect_id}/contacted", response_model=ProspectDetail)
def mark_contacted(prospect_id: int, data: MarkContactedIn, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    p = get_owned_prospect(prospect_id, db, user)
    now = datetime.now(timezone.utc)
    us = db.query(UserSettings).filter_by(user_id=user.id).first() or UserSettings(user_id=user.id)
    o = None
    if data.outreach_id:
        o = _owned_outreach(data.outreach_id, db, user)
        if o.prospect_id != p.id:
            raise HTTPException(400, "Message does not belong to this prospect")
    else:
        o = next((x for x in p.outreach if x.kind == "connection_message" and not x.contacted_at), None)
    if o:
        o.contacted_at, o.channel = now, data.channel
        days = {"connection_message": us.followup_1_days, "follow_up_1": us.followup_2_days}.get(o.kind)
        if days:
            o.follow_up_due = now + timedelta(days=days)
    p.last_contacted_at = now
    old = p.status
    if p.status in (ProspectStatus.NEW, ProspectStatus.ANALYZED, ProspectStatus.REVIEW, ProspectStatus.APPROVED):
        p.status = ProspectStatus.CONTACTED
    audit(db, user.id, "prospect.status_changed", "prospect", p.id, old=old.value, new=p.status.value,
          channel=data.channel)
    db.commit()
    db.refresh(p)
    return prospect_detail(p)


@router.get("/outreach")
def outreach_tracking(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (db.query(Outreach).join(Prospect).filter(Prospect.user_id == user.id)
            .order_by(Outreach.updated_at.desc()).limit(500).all())
    return [{**OutreachOut.model_validate(o).model_dump(), "prospect_id": o.prospect_id,
             "prospect_name": o.prospect.name, "prospect_company": o.prospect.company,
             "prospect_status": o.prospect.status.value, "is_demo": o.prospect.is_demo,
             "last_activity": max(filter(None, [o.updated_at, o.contacted_at, o.prospect.updated_at]))}
            for o in rows]


# ---------- qualification / takeover ----------
@router.put("/prospects/{prospect_id}/qualification", response_model=ProspectDetail)
def set_qualification(prospect_id: int, data: QualificationIn, user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    p = get_owned_prospect(prospect_id, db, user)
    q = p.qualification or LeadQualification(prospect_id=p.id)
    for k, v in data.model_dump().items():
        setattr(q, k, v)
    q.score = qualification_score(data.model_dump())
    q.status = qualification_status(q.score)
    if not p.qualification:
        db.add(q)
    if q.status in ("HOT", "QUALIFIED") and p.status not in (ProspectStatus.PROPOSAL, ProspectStatus.WON,
                                                             ProspectStatus.LOST, ProspectStatus.QUALIFIED):
        p.status = ProspectStatus.QUALIFIED
        audit(db, user.id, "lead.qualified", "prospect", p.id, score=q.score, manual=True)
    db.commit()
    db.refresh(p)
    return prospect_detail(p)


@router.post("/prospects/{prospect_id}/takeover", response_model=ProspectDetail)
def take_over(prospect_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = get_owned_prospect(prospect_id, db, user)
    p.taken_over_at, p.takeover_required = datetime.now(timezone.utc), False
    audit(db, user.id, "lead.taken_over", "prospect", p.id)
    db.commit()
    db.refresh(p)
    return prospect_detail(p)
