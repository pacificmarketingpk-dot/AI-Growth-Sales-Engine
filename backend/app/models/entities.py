"""Database models. Every user-owned row is reachable through user_id for authorization checks."""
from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    JSON, Boolean, CheckConstraint, DateTime, Enum, Float, ForeignKey, Index,
    Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ProspectStatus(str, enum.Enum):
    NEW = "NEW"
    ANALYZING = "ANALYZING"
    ANALYZED = "ANALYZED"
    REVIEW = "REVIEW"
    APPROVED = "APPROVED"
    CONTACTED = "CONTACTED"
    REPLIED = "REPLIED"
    QUALIFIED = "QUALIFIED"
    PROPOSAL = "PROPOSAL"
    WON = "WON"
    LOST = "LOST"


class Timestamped:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class User(Timestamped, Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(200), default="")
    token_version: Mapped[int] = mapped_column(Integer, default=0)  # bump to revoke all sessions
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    settings: Mapped["UserSettings"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")


class UserSettings(Timestamped, Base):
    __tablename__ = "settings"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    brand_name: Mapped[str] = mapped_column(String(120), default="AI Growth Sales Engine")
    business: Mapped[str] = mapped_column(String(200), default="")
    role: Mapped[str] = mapped_column(String(200), default="Digital Marketing Specialist & Consultant")
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    ai_provider: Mapped[str] = mapped_column(String(32), default="")  # empty = use env default
    ai_model: Mapped[str] = mapped_column(String(100), default="")
    message_tone: Mapped[str] = mapped_column(String(50), default="professional and warm")
    followup_1_days: Mapped[int] = mapped_column(Integer, default=4)
    followup_2_days: Mapped[int] = mapped_column(Integer, default=7)
    meeting_title: Mapped[str] = mapped_column(String(200), default="Digital Growth Consultation")
    meeting_duration: Mapped[int] = mapped_column(Integer, default=30)
    email_notifications: Mapped[bool] = mapped_column(Boolean, default=False)
    notification_email: Mapped[str] = mapped_column(String(255), default="")
    user: Mapped[User] = relationship(back_populates="settings")


class Prospect(Timestamped, Base):
    __tablename__ = "prospects"
    __table_args__ = (
        Index("ix_prospect_user_status", "user_id", "status"),
        Index("ix_prospect_user_score", "user_id", "lead_score"),
        CheckConstraint("lead_score IS NULL OR (lead_score >= 0 AND lead_score <= 100)", name="ck_lead_score"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    linkedin_url: Mapped[str | None] = mapped_column(String(500), index=True)
    company: Mapped[str | None] = mapped_column(String(200), index=True)
    job_title: Mapped[str | None] = mapped_column(String(200))
    industry: Mapped[str | None] = mapped_column(String(200))
    country: Mapped[str | None] = mapped_column(String(100))
    company_size: Mapped[str | None] = mapped_column(String(50))
    website: Mapped[str | None] = mapped_column(String(500))
    email: Mapped[str | None] = mapped_column(String(255), index=True)
    phone: Mapped[str | None] = mapped_column(String(50))
    company_description: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ProspectStatus] = mapped_column(Enum(ProspectStatus), default=ProspectStatus.NEW, index=True)
    source: Mapped[str] = mapped_column(String(50), default="manual")
    lead_score: Mapped[int | None] = mapped_column(Integer, index=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    takeover_required: Mapped[bool] = mapped_column(Boolean, default=False)
    taken_over_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_contacted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    analyses: Mapped[list["ProspectAnalysis"]] = relationship(
        back_populates="prospect", cascade="all, delete-orphan", order_by="ProspectAnalysis.analysis_version")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="prospect", cascade="all, delete-orphan")
    outreach: Mapped[list["Outreach"]] = relationship(back_populates="prospect", cascade="all, delete-orphan")
    meetings: Mapped[list["Meeting"]] = relationship(back_populates="prospect", cascade="all, delete-orphan")
    qualification: Mapped["LeadQualification | None"] = relationship(
        back_populates="prospect", uselist=False, cascade="all, delete-orphan")

    @property
    def latest_analysis(self) -> "ProspectAnalysis | None":
        return self.analyses[-1] if self.analyses else None


class ProspectAnalysis(Base):
    __tablename__ = "prospect_analyses"
    __table_args__ = (UniqueConstraint("prospect_id", "analysis_version", name="uq_analysis_version"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    prospect_id: Mapped[int] = mapped_column(ForeignKey("prospects.id", ondelete="CASCADE"), index=True)
    analysis_version: Mapped[int] = mapped_column(Integer, default=1)
    lead_score: Mapped[int] = mapped_column(Integer, index=True)
    category: Mapped[str] = mapped_column(String(10))
    score_breakdown: Mapped[dict] = mapped_column(JSON)
    result: Mapped[dict] = mapped_column(JSON)  # full validated AI output
    website_analysis: Mapped[dict | None] = mapped_column(JSON)
    website_retrieved: Mapped[bool] = mapped_column(Boolean, default=False)
    confidence: Mapped[float] = mapped_column(Float)
    provider: Mapped[str] = mapped_column(String(32))
    model: Mapped[str] = mapped_column(String(100))
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0.0)
    analyzed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    prospect: Mapped[Prospect] = relationship(back_populates="analyses")


class AnalysisJob(Timestamped, Base):
    __tablename__ = "analysis_jobs"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    prospect_ids: Mapped[list] = mapped_column(JSON)
    total: Mapped[int] = mapped_column(Integer)
    completed: Mapped[int] = mapped_column(Integer, default=0)
    failed: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="queued")  # queued / running / done
    errors: Mapped[list] = mapped_column(JSON, default=list)


class Conversation(Timestamped, Base):
    __tablename__ = "conversations"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    prospect_id: Mapped[int] = mapped_column(ForeignKey("prospects.id", ondelete="CASCADE"), index=True)
    channel: Mapped[str] = mapped_column(String(20), default="LinkedIn")
    intent: Mapped[str | None] = mapped_column(String(30), index=True)
    analysis: Mapped[dict | None] = mapped_column(JSON)
    analyzed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    prospect: Mapped[Prospect] = relationship(back_populates="conversations")
    messages: Mapped[list["ConversationMessage"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="ConversationMessage.id")


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    sender: Mapped[str] = mapped_column(String(20))  # me / prospect
    body: Mapped[str] = mapped_column(Text)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class LeadQualification(Timestamped, Base):
    __tablename__ = "lead_qualifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    prospect_id: Mapped[int] = mapped_column(ForeignKey("prospects.id", ondelete="CASCADE"), unique=True)
    need: Mapped[int] = mapped_column(Integer, default=0)
    budget: Mapped[int] = mapped_column(Integer, default=0)
    authority: Mapped[int] = mapped_column(Integer, default=0)
    timeline: Mapped[int] = mapped_column(Integer, default=0)
    current_solution: Mapped[int] = mapped_column(Integer, default=0)
    urgency: Mapped[int] = mapped_column(Integer, default=0)
    score: Mapped[int] = mapped_column(Integer, default=0, index=True)
    status: Mapped[str] = mapped_column(String(20), default="UNQUALIFIED")
    notes: Mapped[str | None] = mapped_column(Text)
    prospect: Mapped[Prospect] = relationship(back_populates="qualification")


class Outreach(Timestamped, Base):
    __tablename__ = "outreach"
    id: Mapped[int] = mapped_column(primary_key=True)
    prospect_id: Mapped[int] = mapped_column(ForeignKey("prospects.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(30))  # connection_message / follow_up_1 / follow_up_2 / suggested_reply
    channel: Mapped[str] = mapped_column(String(20), default="LinkedIn")
    message: Mapped[str] = mapped_column(Text)
    edited: Mapped[bool] = mapped_column(Boolean, default=False)
    contacted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    follow_up_due: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    response: Mapped[str | None] = mapped_column(Text)
    prospect: Mapped[Prospect] = relationship(back_populates="outreach")


class Meeting(Timestamped, Base):
    __tablename__ = "meetings"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    prospect_id: Mapped[int] = mapped_column(ForeignKey("prospects.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    meeting_type: Mapped[str] = mapped_column(String(100), default="Digital Growth Consultation")
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30)
    notes: Mapped[str | None] = mapped_column(Text)
    meeting_notes: Mapped[str | None] = mapped_column(Text)
    next_action: Mapped[str | None] = mapped_column(Text)
    google_event_id: Mapped[str | None] = mapped_column(String(255))
    google_event_link: Mapped[str | None] = mapped_column(String(500))
    calendar_synced: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default="scheduled")
    prospect: Mapped[Prospect] = relationship(back_populates="meetings")


class Integration(Timestamped, Base):
    __tablename__ = "integrations"
    __table_args__ = (UniqueConstraint("user_id", "provider", name="uq_user_integration"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20), default="NOT_CONNECTED")
    encrypted_tokens: Mapped[str | None] = mapped_column(Text)  # Fernet-encrypted JSON
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    scopes: Mapped[str | None] = mapped_column(Text)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    action: Mapped[str] = mapped_column(String(60), index=True)
    entity_type: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[int | None] = mapped_column(Integer)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
