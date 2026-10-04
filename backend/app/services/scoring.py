"""Pure scoring functions. Kept free of I/O so they are easy to test."""

QUALIFICATION_WEIGHTS = {"need": 25, "budget": 15, "authority": 20, "timeline": 15, "current_solution": 10, "urgency": 15}


def lead_category(score: int | None) -> str | None:
    if score is None:
        return None
    if score >= 90:
        return "HOT"
    if score >= 75:
        return "HIGH"
    if score >= 60:
        return "MEDIUM"
    return "LOW"


def qualification_score(signals: dict) -> int:
    total = 0
    for key, cap in QUALIFICATION_WEIGHTS.items():
        total += max(0, min(int(signals.get(key, 0) or 0), cap))
    return total


def qualification_status(score: int) -> str:
    if score >= 80:
        return "HOT"
    if score >= 60:
        return "QUALIFIED"
    if score >= 35:
        return "NURTURE"
    return "UNQUALIFIED"


def safe_rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator * 100, 1) if denominator else 0.0
