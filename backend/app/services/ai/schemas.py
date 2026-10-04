"""Strict schemas for AI output. Anything that fails validation is never saved."""
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

OPPORTUNITY_CATEGORIES = [
    "Lead Generation", "Paid Advertising", "Google Ads", "Meta Ads", "SEO", "Local SEO",
    "Website Conversion", "Landing Pages", "Content Marketing", "Social Media",
    "LinkedIn Lead Generation", "Email Marketing", "Retargeting", "E-commerce Growth",
    "Brand Positioning", "Marketing Automation", "Customer Acquisition", "Conversion Rate Optimization",
]

SCORE_WEIGHTS = {
    "business_fit": 20,
    "marketing_opportunity": 25,
    "company_potential": 15,
    "decision_maker_relevance": 15,
    "digital_opportunity": 15,
    "outreach_potential": 10,
}

BANNED_PHRASES = [
    "i came across your profile",
    "leading digital marketing agency",
    "we are a leading",
    "i was impressed by your profile",
    "guaranteed results",
    "act now",
]

INTENTS = ["INTERESTED", "HIGH INTENT", "QUALIFIED", "NEUTRAL", "NOT INTERESTED", "NOT RELEVANT", "NEEDS FOLLOW-UP"]


class ScoreBreakdown(BaseModel):
    business_fit: int = Field(ge=0, le=20)
    marketing_opportunity: int = Field(ge=0, le=25)
    company_potential: int = Field(ge=0, le=15)
    decision_maker_relevance: int = Field(ge=0, le=15)
    digital_opportunity: int = Field(ge=0, le=15)
    outreach_potential: int = Field(ge=0, le=10)

    @property
    def total(self) -> int:
        return sum(self.model_dump().values())


class EvidenceItem(BaseModel):
    type: Literal["FACT", "ASSUMPTION", "OPPORTUNITY"]
    statement: str = Field(min_length=3, max_length=600)
    source: str = Field(default="", max_length=200)  # e.g. "prospect record", "website homepage"


def _check_banned(text: str) -> str:
    low = text.lower()
    for phrase in BANNED_PHRASES:
        if phrase in low:
            raise ValueError(f"message uses a banned generic phrase: '{phrase}'")
    return text


class ProspectAnalysisResult(BaseModel):
    lead_score: int = Field(ge=0, le=100)
    score_breakdown: ScoreBreakdown
    business_fit: str = Field(max_length=800)
    marketing_opportunity: str = Field(max_length=800)
    decision_maker_relevance: str = Field(max_length=800)
    digital_opportunity: str = Field(max_length=800)
    outreach_potential: str = Field(max_length=800)
    business_problem: str = Field(max_length=800)
    evidence: list[EvidenceItem] = Field(default_factory=list, max_length=20)
    insufficient_evidence: list[str] = Field(default_factory=list, max_length=20)
    growth_opportunity: str = Field(max_length=800)
    primary_service: str
    secondary_service: str | None = None
    personalization: str = Field(max_length=800)
    connection_message: str = Field(min_length=20, max_length=600)
    follow_up_1: str = Field(min_length=20, max_length=900)
    follow_up_2: str = Field(min_length=20, max_length=900)
    confidence: float = Field(ge=0, le=1)

    @field_validator("primary_service")
    @classmethod
    def _primary_in_categories(cls, v: str) -> str:
        if v not in OPPORTUNITY_CATEGORIES:
            raise ValueError(f"primary_service must be one of the opportunity categories, got '{v}'")
        return v

    @field_validator("secondary_service")
    @classmethod
    def _secondary_in_categories(cls, v: str | None) -> str | None:
        if v in (None, "", "None", "null"):
            return None
        if v not in OPPORTUNITY_CATEGORIES:
            raise ValueError(f"secondary_service must be one of the opportunity categories, got '{v}'")
        return v

    @field_validator("connection_message", "follow_up_1", "follow_up_2")
    @classmethod
    def _no_generic(cls, v: str) -> str:
        return _check_banned(v)

    @model_validator(mode="after")
    def _score_matches_breakdown(self):
        # The server never trusts the AI's arithmetic: the total is always the breakdown sum.
        self.lead_score = self.score_breakdown.total
        if self.secondary_service == self.primary_service:
            self.secondary_service = None
        return self


class WebsiteFindings(BaseModel):
    value_proposition: str = ""
    cta: str = ""
    lead_capture: str = ""
    services: str = ""
    trust_signals: str = ""
    content: str = ""
    seo_basics: str = ""
    conversion_opportunities: str = ""
    mobile_experience: str = ""
    messaging: str = ""


class QualificationSignals(BaseModel):
    need: int = Field(ge=0, le=25)
    budget: int = Field(ge=0, le=15)
    authority: int = Field(ge=0, le=20)
    timeline: int = Field(ge=0, le=15)
    current_solution: int = Field(ge=0, le=10)
    urgency: int = Field(ge=0, le=15)


class ConversationAnalysisResult(BaseModel):
    intent: str
    summary: str = Field(max_length=1000)
    pain_point: str = Field(max_length=500)
    need: str = Field(max_length=500)
    budget_signal: str = Field(max_length=500)
    timeline_signal: str = Field(max_length=500)
    decision_maker: str = Field(max_length=500)
    current_solution: str = Field(max_length=500)
    interest_level: Literal["LOW", "MEDIUM", "HIGH"]
    recommended_service: str = Field(max_length=200)
    recommended_next_action: str = Field(max_length=500)
    human_takeover: bool
    suggested_reply: str = Field(min_length=10, max_length=1200)
    qualification_questions: list[str] = Field(default_factory=list, max_length=8)
    qualification: QualificationSignals
    confidence: float = Field(ge=0, le=1)

    @field_validator("intent")
    @classmethod
    def _intent(cls, v: str) -> str:
        v = v.strip().upper().replace("_", " ")
        if v == "HIGH":
            v = "HIGH INTENT"
        if v not in INTENTS:
            raise ValueError(f"intent must be one of {INTENTS}")
        return v

    @field_validator("suggested_reply")
    @classmethod
    def _no_generic(cls, v: str) -> str:
        return _check_banned(v)


class MessageRegeneration(BaseModel):
    message: str = Field(min_length=20, max_length=1200)

    @field_validator("message")
    @classmethod
    def _no_generic(cls, v: str) -> str:
        return _check_banned(v)
