import type { Category } from "../types";

export const fmtDate = (s?: string | null) =>
  s ? new Date(s).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" }) : "—";
export const fmtDateTime = (s?: string | null) =>
  s ? new Date(s).toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }) : "—";
export const fmtTime = (s: string) => new Date(s).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
export const pct = (n: number | null | undefined) => (n == null ? "—" : `${n}%`);
export const titleCase = (s: string) => s.charAt(0) + s.slice(1).toLowerCase().replace(/_/g, " ");

export function categoryOf(score: number | null | undefined): Category | null {
  if (score == null) return null;
  return score >= 90 ? "HOT" : score >= 75 ? "HIGH" : score >= 60 ? "MEDIUM" : "LOW";
}

export const BREAKDOWN_PARTS: { key: keyof import("../types").Breakdown; label: string; max: number }[] = [
  { key: "business_fit", label: "Business fit", max: 20 },
  { key: "marketing_opportunity", label: "Marketing opportunity", max: 25 },
  { key: "company_potential", label: "Company potential", max: 15 },
  { key: "decision_maker_relevance", label: "Decision maker", max: 15 },
  { key: "digital_opportunity", label: "Digital opportunity", max: 15 },
  { key: "outreach_potential", label: "Outreach potential", max: 10 },
];

export const OUTREACH_LABELS: Record<string, string> = {
  connection_message: "Connection message", follow_up_1: "Follow-up 1", follow_up_2: "Follow-up 2",
  suggested_reply: "Suggested reply",
};
