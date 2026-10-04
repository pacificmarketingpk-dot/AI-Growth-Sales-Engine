"""Optional email notifications to the USER only. No automated emails are sent to prospects."""
import logging
import smtplib
from email.message import EmailMessage

from app.config import get_settings

log = logging.getLogger(__name__)


def smtp_configured() -> bool:
    s = get_settings()
    return bool(s.smtp_host and s.smtp_from)


def notify_qualified_lead(user_settings, prospect, analysis) -> bool:
    s = get_settings()
    to = user_settings.notification_email
    if not (smtp_configured() and to):
        return False
    msg = EmailMessage()
    msg["Subject"] = f"🔥 New Qualified Lead: {prospect.name} from {prospect.company or 'unknown company'}"
    msg["From"], msg["To"] = s.smtp_from, to
    msg.set_content(
        f"Lead score: {prospect.lead_score if prospect.lead_score is not None else 'not analyzed'}\n"
        f"Pain point: {analysis.pain_point}\nOpportunity: {analysis.recommended_service}\n"
        f"Recommended action: {analysis.recommended_next_action}\n\n{s.frontend_url}/prospects/{prospect.id}")
    try:
        with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=10) as smtp:
            smtp.starttls()
            if s.smtp_user:
                smtp.login(s.smtp_user, s.smtp_password)
            smtp.send_message(msg)
        return True
    except Exception:
        log.exception("notification email failed")
        return False
