import { useState } from "react";
import { Link } from "react-router-dom";
import { Send } from "lucide-react";
import { useApi } from "../hooks/useApi";
import type { Outreach as O } from "../types";
import { MessageCard } from "../components/MessageCard";
import { DemoTag, EmptyState, ErrorState, Notice, PageHeader, Spinner, StatusBadge, Tabs } from "../components/ui";
import { fmtDate, OUTREACH_LABELS } from "../utils/format";

type Row = O & { prospect_id: number; prospect_name: string; prospect_company: string | null; prospect_status: string; is_demo: boolean; last_activity: string };

export default function Outreach() {
  const { data, error, loading, reload, setData } = useApi<Row[]>("/api/outreach");
  const [tab, setTab] = useState<"drafts" | "tracking">("drafts");
  if (loading && !data) return <Spinner />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  const rows = data ?? [];
  const drafts = rows.filter((r) => !r.contacted_at);
  const sent = rows.filter((r) => r.contacted_at);
  const due = sent.filter((r) => r.follow_up_due && new Date(r.follow_up_due) <= new Date());

  return (
    <>
      <PageHeader title="Outreach" description="Review, edit and copy AI-drafted messages. You send them; nothing is sent automatically." />
      <div className="mb-4"><Notice>LinkedIn integration not connected. Use Copy, send from LinkedIn, then mark it as sent on the prospect.</Notice></div>
      {due.length > 0 && <div className="mb-4"><Notice tone="warn">{due.length} follow-up{due.length > 1 ? "s are" : " is"} due: {due.slice(0, 3).map((d) => d.prospect_name).join(", ")}{due.length > 3 ? "…" : ""}</Notice></div>}
      <Tabs value={tab} onChange={setTab} tabs={[{ id: "drafts", label: `Drafts (${drafts.length})` }, { id: "tracking", label: `Tracking (${sent.length})` }]} />
      {tab === "drafts" ? (drafts.length === 0 ? <EmptyState icon={<Send className="h-8 w-8" />} title="No drafts waiting." body="Analyze a prospect to generate personalised messages." /> : (
        <ul className="space-y-5">{drafts.map((r) => (
          <li key={r.id}>
            <p className="mb-1 flex flex-wrap items-center gap-2 text-sm"><Link className="tap font-semibold hover:underline" to={`/prospects/${r.prospect_id}`}>{r.prospect_name}</Link><span className="text-ink-muted">{r.prospect_company}</span>{r.is_demo && <DemoTag />}</p>
            <MessageCard item={r} onChange={(n) => setData(rows.map((x) => (x.id === n.id ? { ...x, ...n } : x)))} />
          </li>))}</ul>
      )) : sent.length === 0 ? <EmptyState title="Nothing sent yet." body="Mark a message as sent from the prospect's Outreach tab to track it here." /> : (
        <>
          <div className="panel hidden overflow-x-auto md:block">
            <table className="w-full text-sm">
              <thead className="border-b border-line bg-paper text-left text-ink-muted"><tr>
                <th className="p-3 font-medium">Prospect</th><th className="p-3 font-medium">Message</th><th className="p-3 font-medium">Channel</th><th className="p-3 font-medium">Date contacted</th><th className="p-3 font-medium">Next follow-up</th><th className="p-3 font-medium">Status</th><th className="p-3 font-medium">Last activity</th></tr></thead>
              <tbody className="divide-y divide-line">{sent.map((r) => (
                <tr key={r.id}><td className="p-3"><Link className="tap font-medium hover:underline" to={`/prospects/${r.prospect_id}`}>{r.prospect_name}</Link></td>
                  <td className="p-3">{OUTREACH_LABELS[r.kind]}</td><td className="p-3">{r.channel}</td><td className="tnum p-3">{fmtDate(r.contacted_at)}</td>
                  <td className="tnum p-3">{r.follow_up_due ? fmtDate(r.follow_up_due) : "—"}</td><td className="p-3"><StatusBadge status={r.prospect_status} /></td><td className="tnum p-3 text-ink-muted">{fmtDate(r.last_activity)}</td></tr>))}</tbody>
            </table>
          </div>
          <ul className="space-y-3 md:hidden">{sent.map((r) => (
            <li key={r.id} className="panel p-4"><div className="flex items-center justify-between gap-2"><Link className="tap font-semibold" to={`/prospects/${r.prospect_id}`}>{r.prospect_name}</Link><StatusBadge status={r.prospect_status} /></div>
              <p className="mt-1 text-sm text-ink-muted">{OUTREACH_LABELS[r.kind]} via {r.channel} on {fmtDate(r.contacted_at)}</p>
              {r.follow_up_due && <p className="text-sm">Next follow-up {fmtDate(r.follow_up_due)}</p>}</li>))}</ul>
        </>
      )}
    </>
  );
}
