from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, field_validator

from app.models import ProspectStatus


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---- auth ----
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    name: str = Field(default="", max_length=200)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=10, max_length=128)


class UserOut(ORM):
    id: int
    email: str
    name: str


# ---- prospects ----
class ProspectBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    linkedin_url: str | None = Field(default=None, max_length=500)
    company: str | None = Field(default=None, max_length=200)
    job_title: str | None = Field(default=None, max_length=200)
    industry: str | None = Field(default=None, max_length=200)
    country: str | None = Field(default=None, max_length=100)
    company_size: str | None = Field(default=None, max_length=50)
    website: str | None = Field(default=None, max_length=500)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    company_description: str | None = Field(default=None, max_length=5000)
    notes: str | None = Field(default=None, max_length=5000)

    @field_validator("*", mode="before")
    @classmethod
    def _blank_to_none(cls, v):
        return None if isinstance(v, str) and not v.strip() else v

    @field_validator("linkedin_url")
    @classmethod
    def _linkedin(cls, v):
        if v and "linkedin.com" not in v.lower():
            raise ValueError("Must be a linkedin.com URL")
        return v

    @field_validator("website")
    @classmethod
    def _website(cls, v):
        if v:
            url = v if v.startswith(("http://", "https://")) else "https://" + v
            HttpUrl(url)
            return url
        return v


class ProspectCreate(ProspectBase):
    pass


class ProspectUpdate(ProspectBase):
    name: str | None = Field(default=None, max_length=200)
    status: ProspectStatus | None = None


class QualificationOut(ORM):
    need: int
    budget: int
    authority: int
    timeline: int
    current_solution: int
    urgency: int
    score: int
    status: str
    notes: str | None


class QualificationIn(BaseModel):
    need: int = Field(ge=0, le=25)
    budget: int = Field(ge=0, le=15)
    authority: int = Field(ge=0, le=20)
    timeline: int = Field(ge=0, le=15)
    current_solution: int = Field(ge=0, le=10)
    urgency: int = Field(ge=0, le=15)
    notes: str | None = Field(default=None, max_length=5000)


class AnalysisOut(ORM):
    id: int
    analysis_version: int
    lead_score: int
    category: str
    score_breakdown: dict
    result: dict
    website_analysis: dict | None
    website_retrieved: bool
    confidence: float
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    estimated_cost: float
    analyzed_at: datetime


class OutreachOut(ORM):
    id: int
    kind: str
    channel: str
    message: str
    edited: bool
    contacted_at: datetime | None
    follow_up_due: datetime | None
    response: str | None
    updated_at: datetime


class OutreachUpdate(BaseModel):
    message: str | None = Field(default=None, min_length=1, max_length=3000)
    channel: str | None = Field(default=None, pattern="^(LinkedIn|Email|Other)$")
    response: str | None = Field(default=None, max_length=5000)


class ProspectOut(ORM):
    id: int
    name: str
    linkedin_url: str | None
    company: str | None
    job_title: str | None
    industry: str | None
    country: str | None
    company_size: str | None
    website: str | None
    email: str | None
    phone: str | None
    company_description: str | None
    notes: str | None
    status: ProspectStatus
    source: str
    lead_score: int | None
    category: str | None = None
    score_breakdown: dict | None = None
    is_demo: bool
    takeover_required: bool
    taken_over_at: datetime | None
    created_at: datetime
    updated_at: datetime
    last_contacted_at: datetime | None


class ProspectDetail(ProspectOut):
    latest_analysis: AnalysisOut | None
    analysis_count: int = 0
    outreach: list[OutreachOut]
    qualification: QualificationOut | None


class ProspectList(BaseModel):
    items: list[ProspectOut]
    total: int


class BulkAnalyzeIn(BaseModel):
    prospect_ids: list[int] = Field(min_length=1, max_length=100)
    force: bool = False


class MarkContactedIn(BaseModel):
    channel: str = Field(default="LinkedIn", pattern="^(LinkedIn|Email|Other)$")
    outreach_id: int | None = None


# ---- conversations ----
class MessageIn(BaseModel):
    sender: str = Field(pattern="^(me|prospect)$")
    body: str = Field(min_length=1, max_length=10000)
    sent_at: datetime | None = None


class ConversationCreate(BaseModel):
    prospect_id: int
    channel: str = Field(default="LinkedIn", pattern="^(LinkedIn|Email|Other)$")
    messages: list[MessageIn] = Field(default_factory=list, max_length=200)
    raw_text: str | None = Field(default=None, max_length=50000)  # pasted transcript


class MessageOut(ORM):
    id: int
    sender: str
    body: str
    sent_at: datetime


class ConversationOut(ORM):
    id: int
    prospect_id: int
    prospect_name: str = ""
    prospect_company: str | None = None
    channel: str
    intent: str | None
    analysis: dict | None
    analyzed_at: datetime | None
    created_at: datetime
    messages: list[MessageOut]


# ---- meetings ----
class MeetingCreate(BaseModel):
    prospect_id: int
    meeting_type: str | None = Field(default=None, max_length=100)
    title: str | None = Field(default=None, max_length=200)
    start_at: datetime
    duration_minutes: int | None = Field(default=None, ge=10, le=240)
    notes: str | None = Field(default=None, max_length=5000)
    invite_prospect: bool = False
    sync_to_google: bool = True


class MeetingUpdate(BaseModel):
    meeting_notes: str | None = Field(default=None, max_length=20000)
    next_action: str | None = Field(default=None, max_length=2000)
    status: str | None = Field(default=None, pattern="^(scheduled|completed|cancelled|no_show)$")


class MeetingOut(ORM):
    id: int
    prospect_id: int
    title: str
    meeting_type: str
    start_at: datetime
    duration_minutes: int
    notes: str | None
    meeting_notes: str | None
    next_action: str | None
    google_event_link: str | None
    calendar_synced: bool
    status: str
    prospect: dict = {}


# ---- settings ----
class SettingsIn(BaseModel):
    brand_name: str | None = Field(default=None, max_length=120)
    name: str | None = Field(default=None, max_length=200)
    business: str | None = Field(default=None, max_length=200)
    role: str | None = Field(default=None, max_length=200)
    timezone: str | None = Field(default=None, max_length=64)
    ai_provider: str | None = Field(default=None, pattern="^(|openai|anthropic)$")
    ai_model: str | None = Field(default=None, max_length=100)
    message_tone: str | None = Field(default=None, max_length=50)
    followup_1_days: int | None = Field(default=None, ge=1, le=60)
    followup_2_days: int | None = Field(default=None, ge=1, le=90)
    meeting_title: str | None = Field(default=None, max_length=200)
    meeting_duration: int | None = Field(default=None, ge=10, le=240)
    email_notifications: bool | None = None
    notification_email: EmailStr | None | str = None
