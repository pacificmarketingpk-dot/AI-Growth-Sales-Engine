from fastapi import HTTPException

from app.models import Prospect
from app.schemas.api import ProspectDetail, ProspectOut
from app.services.ai.provider import AIError, AINotConfigured
from app.services.scoring import lead_category

AI_UNAVAILABLE = "AI analysis is temporarily unavailable. Check your AI provider connection."


def prospect_out(p: Prospect) -> ProspectOut:
    out = ProspectOut.model_validate(p)
    out.category = lead_category(p.lead_score)
    out.score_breakdown = p.latest_analysis.score_breakdown if p.latest_analysis else None
    return out


def prospect_detail(p: Prospect) -> ProspectDetail:
    d = ProspectDetail.model_validate(p)
    d.category = lead_category(p.lead_score)
    d.score_breakdown = p.latest_analysis.score_breakdown if p.latest_analysis else None
    d.analysis_count = len(p.analyses)
    return d


def ai_http_error(e: Exception) -> HTTPException:
    if isinstance(e, AINotConfigured):
        return HTTPException(503, AI_UNAVAILABLE + " No API key is configured for the selected provider.")
    if isinstance(e, AIError):
        return HTTPException(502, AI_UNAVAILABLE)
    return HTTPException(500, "Something went wrong. Please try again.")
