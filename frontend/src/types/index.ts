export type ProspectStatus =
  | "NEW" | "ANALYZING" | "ANALYZED" | "REVIEW" | "APPROVED" | "CONTACTED"
  | "REPLIED" | "QUALIFIED" | "PROPOSAL" | "WON" | "LOST";
export const STATUSES: ProspectStatus[] = [
  "NEW", "ANALYZING", "ANALYZED", "REVIEW", "APPROVED", "CONTACTED", "REPLIED", "QUALIFIED", "PROPOSAL", "WON", "LOST",
];
export type Category = "HOT" | "HIGH" | "MEDIUM" | "LOW";

export interface User { id: number; email: string; name: string }

export interface Prospect {
  id: number; name: string; linkedin_url: string | null; company: string | null; job_title: string | null;
  industry: string | null; country: string | null; company_size: string | null; website: string | null;
  email: string | null; phone: string | null; company_description: string | null; notes: string | null;
  status: ProspectStatus; source: string; lead_score: number | null; category: Category | null;
  score_breakdown: Breakdown | null; is_demo: boolean;
  takeover_required: boolean; taken_over_at: string | null; created_at: string; updated_at: string;
  last_contacted_at: string | null;
}

export interface Evidence { type: "FACT" | "ASSUMPTION" | "OPPORTUNITY"; statement: string; source: string }
export interface Breakdown {
  business_fit: number; marketing_opportunity: number; company_potential: number;
  decision_maker_relevance: number; digital_opportunity: number; outreach_potential: number;
}
export interface AnalysisResult {
  lead_score: number; score_breakdown: Breakdown; business_fit: string; marketing_opportunity: string;
  decision_maker_relevance: string; digital_opportunity: string; outreach_potential: string;
  business_problem: string; evidence: Evidence[]; insufficient_evidence: string[]; growth_opportunity: string;
  primary_service: string; secondary_service: string | null; personalization: string;
  connection_message: string; follow_up_1: string; follow_up_2: string; confidence: number;
}
export interface Analysis {
  id: number; analysis_version: number; lead_score: number; category: Category; score_breakdown: Breakdown;
  result: AnalysisResult; website_analysis: Record<string, string> | null; website_retrieved: boolean;
  confidence: number; provider: string; model: string; input_tokens: number; output_tokens: number;
  estimated_cost: number; analyzed_at: string;
}
export interface Outreach {
  id: number; kind: string; channel: string; message: string; edited: boolean; contacted_at: string | null;
  follow_up_due: string | null; response: string | null; updated_at: string;
}
export interface Qualification {
  need: number; budget: number; authority: number; timeline: number; current_solution: number; urgency: number;
  score: number; status: string; notes: string | null;
}
export interface ProspectDetail extends Prospect {
  latest_analysis: Analysis | null; analysis_count: number; outreach: Outreach[]; qualification: Qualification | null;
}

export interface ConversationAnalysis {
  intent: string; summary: string; pain_point: string; need: string; budget_signal: string; timeline_signal: string;
  decision_maker: string; current_solution: string; interest_level: string; recommended_service: string;
  recommended_next_action: string; human_takeover: boolean; suggested_reply: string;
  qualification_questions: string[]; confidence: number;
}
export interface Conversation {
  id: number; prospect_id: number; prospect_name: string; prospect_company: string | null; channel: string;
  intent: string | null; analysis: ConversationAnalysis | null; analyzed_at: string | null; created_at: string;
  messages: { id: number; sender: "me" | "prospect"; body: string; sent_at: string }[];
}

export interface LeadCard {
  prospect: Prospect; intent: string | null; conversation_id: number | null; recent_response_at: string | null;
  pain_point: string | null; growth_opportunity: string | null; recommended_service: string | null;
  summary: string | null; suggested_reply: string | null; qualification_questions: string[];
  qualification: { score: number; status: string } | null; takeover_required: boolean;
}

export interface Meeting {
  id: number; prospect_id: number; title: string; meeting_type: string; start_at: string; duration_minutes: number;
  notes: string | null; meeting_notes: string | null; next_action: string | null; google_event_link: string | null;
  calendar_synced: boolean; status: string;
  prospect: { id: number; name: string; company: string | null; email: string | null; lead_score: number | null;
    is_demo: boolean; business_problem: string | null; growth_opportunity: string | null;
    recommended_service: string | null; qualification_notes: string | null };
}

export interface IntegrationItem {
  provider: string; label: string; category: string; status: string; available: boolean; note?: string | null;
  config: Record<string, string>;
}
export interface Settings {
  name: string; email: string; brand_name: string; business: string; role: string; timezone: string;
  ai_provider: string; ai_model: string; message_tone: string; followup_1_days: number; followup_2_days: number;
  meeting_title: string; meeting_duration: number; email_notifications: boolean; notification_email: string;
}
