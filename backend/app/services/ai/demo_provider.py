"""Deterministic provider used ONLY for prospects flagged is_demo. Output is labelled DEMO."""
import json

from app.services.ai.provider import AIProvider, AIRawResponse


class DemoProvider(AIProvider):
    name = "demo"

    def __init__(self):
        super().__init__(api_key="demo", model="demo")

    async def complete(self, system: str, user: str, max_tokens: int = 2000) -> AIRawResponse:
        if '"intent"' in system:
            return AIRawResponse(json.dumps(DEMO_CONVERSATION))
        if '"message"' in system and "lead_score" not in system:
            return AIRawResponse(json.dumps({"message": "[DEMO] Following up on the landing page idea - happy to share two quick examples if useful."}))
        return AIRawResponse(json.dumps(DEMO_ANALYSIS))


DEMO_ANALYSIS = {
    "lead_score": 0,
    "score_breakdown": {"business_fit": 17, "marketing_opportunity": 22, "company_potential": 12,
                        "decision_maker_relevance": 14, "digital_opportunity": 12, "outreach_potential": 8},
    "business_fit": "[DEMO] SaaS company in a segment that commonly buys growth consulting.",
    "marketing_opportunity": "[DEMO] Potential opportunity in paid acquisition and landing pages.",
    "decision_maker_relevance": "[DEMO] Title suggests budget authority for marketing.",
    "digital_opportunity": "[DEMO] Insufficient evidence about current campaigns.",
    "outreach_potential": "[DEMO] Active role, relevant to the offer.",
    "business_problem": "[DEMO] Potential difficulty converting paid traffic into qualified demos.",
    "evidence": [
        {"type": "FACT", "statement": "[DEMO] Record lists industry as SaaS.", "source": "prospect record"},
        {"type": "ASSUMPTION", "statement": "[DEMO] Likely runs some paid campaigns.", "source": "industry norm"},
        {"type": "OPPORTUNITY", "statement": "[DEMO] Dedicated landing pages per campaign.", "source": "analysis"},
    ],
    "insufficient_evidence": ["Revenue", "Ad spend", "Traffic"],
    "growth_opportunity": "[DEMO] Landing page optimisation tied to paid campaigns.",
    "primary_service": "Landing Pages",
    "secondary_service": "Meta Ads",
    "personalization": "[DEMO] Reference their product-led onboarding.",
    "connection_message": "[DEMO] Hi there - I work with SaaS teams on turning paid clicks into booked demos. Would be glad to connect and compare notes.",
    "follow_up_1": "[DEMO] Thanks for connecting. One pattern I see often: campaign traffic landing on the homepage rather than a focused page. Is that something you've looked at?",
    "follow_up_2": "[DEMO] Last note from me - if improving demo conversion is on this quarter's list, I'm happy to share a short teardown. No pressure either way.",
    "confidence": 0.7,
}

DEMO_CONVERSATION = {
    "intent": "HIGH INTENT",
    "summary": "[DEMO] Prospect reports difficulty getting qualified leads from Meta.",
    "pain_point": "Qualified lead generation",
    "need": "More qualified demo requests from paid social",
    "budget_signal": "Insufficient evidence.",
    "timeline_signal": "Wants to fix it this quarter",
    "decision_maker": "Appears to be the decision maker",
    "current_solution": "Running Meta campaigns in-house",
    "interest_level": "HIGH",
    "recommended_service": "Meta Ads + Landing Page Optimization",
    "recommended_next_action": "Human takeover",
    "human_takeover": True,
    "suggested_reply": "[DEMO] That's a common gap - often the targeting is fine and the landing page is where leads drop. Would a 30-minute call next week to look at your funnel be useful?",
    "qualification_questions": ["What does a qualified lead look like for you?", "What monthly budget is allocated to Meta?",
                                "Who else is involved in choosing a partner?"],
    "qualification": {"need": 22, "budget": 6, "authority": 16, "timeline": 12, "current_solution": 8, "urgency": 12},
    "confidence": 0.8,
}
