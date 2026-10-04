import { Link } from "react-router-dom";
import { ChevronRight, Upload, UserPlus } from "lucide-react";
import { useState } from "react";
import { useApi } from "../hooks/useApi";
import { api } from "../services/api";
import { Button, EmptyState, ErrorState, PageHeader, Panel, Spinner, useToast } from "../components/ui";
import { fmtDateTime, titleCase } from "../utils/format";

interface Dash {
  has_demo_data: boolean;
  prospects: { total: number; new: number; analyzed: number; high_priority: number };
  sales: { contacted: number; responses: number; qualified: number; meetings: number; proposals: number; won: number };
  ai: { average_score: number | null; hot_count: number; average_confidence: number | null; top_opportunity: string | null };
  meetings: { upcoming: number; this_week: number; booked: number; next: { id: number; title: string; start_at: string; prospect_id: number; prospect_name: string }[] };
  recent_activity: { action: string; entity_type: string; entity_id: number | null; created_at: string; details: Record<string, unknown> }[];
}

const ACTIONS: Record<string, string> = {
  "prospect.created": "Prospect added", "prospect.analyzed": "Prospect analyzed", "prospect.updated": "Prospect updated",
  "message.generated": "Messages drafted", "conversation.analyzed": "Conversation analyzed", "lead.qualified": "Lead qualified",
  "meeting.booked": "Meeting booked", "prospect.status_changed": "Status changed", "prospect.imported": "Prospects imported",
  "conversation.created": "Conversation added", "lead.taken_over": "Conversation taken over", "demo.seeded": "Demo data added", "user.registered": "Account created", "settings.updated": "Settings updated",
  "integration.connected": "Integration connected", "demo.cleared": "Demo data removed",
};

function Stat({ label, value, to }: { label: string; value: string | number; to?: string }) {
  const body = (<><dt className="text-sm text-ink-muted">{label}</dt><dd className="tnum mt-0.5 font-display text-2xl font-semibold">{value}</dd></>);
  return to ? <Link to={to} className="rounded-md p-2 hover:bg-paper">{body}</Link> : <div className="p-2">{body}</div>;
}

export default function Dashboard() {
  const [includeDemo, setIncludeDemo] = useState(true);
  const { data, error, loading, reload } = useApi<Dash>(`/api/dashboard?include_demo=${includeDemo}`);
  const toast = useToast();
  if (loading && !data) return <Spinner />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (!data) return null;

  const empty = data.prospects.total === 0;
  const pipeline = [
    ["Contacted", data.sales.contacted], ["Responses", data.sales.responses], ["Qualified", data.sales.qualified],
    ["Meetings", data.sales.meetings], ["Proposals", data.sales.proposals], ["Won", data.sales.won],
  ] as const;

  return (
    <>
      <PageHeader title="Dashboard" description="Where your pipeline stands today."
        actions={data.has_demo_data && (
          <label className="flex min-h-[44px] items-center gap-2 rounded-md border border-line bg-white px-3 text-sm">
            <input type="checkbox" className="h-4 w-4" checked={includeDemo} onChange={(e) => setIncludeDemo(e.target.checked)} /> Include demo data
          </label>)} />

      {empty ? (
        <EmptyState title="No prospects yet." body="Import your first prospect list to begin, or add someone you already have in mind."
          action={<>
            <Link to="/prospects?import=1"><Button variant="primary" icon={<Upload className="h-4 w-4" />}>Import CSV</Button></Link>
            <Link to="/prospects?add=1"><Button icon={<UserPlus className="h-4 w-4" />}>Add prospect</Button></Link>
            {!data.has_demo_data && <Button variant="ghost" onClick={async () => { await api.post("/api/demo/seed"); toast("Demo data added"); reload(); }}>Explore with demo data</Button>}
          </>} />
      ) : (
        <div className="space-y-5">
          <section aria-labelledby="pipe" className="panel overflow-hidden">
            <h2 id="pipe" className="sr-only">Sales pipeline</h2>
            <ol className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6">
              {pipeline.map(([label, v], i) => (
                <li key={label} className={`relative border-line px-4 py-4 sm:px-5 ${i % 2 ? "border-l" : ""} sm:border-l ${i % 3 === 0 ? "sm:border-l-0" : ""} lg:border-l ${i === 0 ? "lg:border-l-0" : ""} ${i >= 2 ? "border-t" : ""} ${i >= 3 ? "sm:border-t" : "sm:border-t-0"} lg:border-t-0`}>
                  <p className="text-sm text-ink-muted">{label}</p>
                  <p className="tnum font-display text-[32px] font-semibold leading-tight">{v}</p>
                  {i < pipeline.length - 1 && <ChevronRight className="absolute right-1 top-1/2 hidden h-4 w-4 -translate-y-1/2 text-line lg:block" aria-hidden />}
                </li>
              ))}
            </ol>
          </section>

          <div className="grid grid-cols-1 gap-5 lg:grid-cols-3 [&>*]:min-w-0">
            <Panel title="Prospects" action={<Link className="tap -my-3 text-sm font-medium underline" to="/prospects">View all</Link>}>
              <dl className="grid grid-cols-2 gap-1">
                <Stat label="Total" value={data.prospects.total} to="/prospects" />
                <Stat label="New" value={data.prospects.new} to="/prospects?status=NEW" />
                <Stat label="Analyzed" value={data.prospects.analyzed} to="/analysis" />
                <Stat label="High priority (75+)" value={data.prospects.high_priority} to="/hot-leads" />
              </dl>
            </Panel>
            <Panel title="AI insight">
              <dl className="grid grid-cols-2 gap-1">
                <Stat label="Average lead score" value={data.ai.average_score ?? "—"} />
                <Stat label="Hot leads (90+)" value={data.ai.hot_count} to="/hot-leads" />
                <Stat label="Average confidence" value={data.ai.average_confidence != null ? `${Math.round(data.ai.average_confidence * 100)}%` : "—"} />
                <div className="p-2"><dt className="text-sm text-ink-muted">Top opportunity</dt><dd className="mt-1 font-semibold leading-snug">{data.ai.top_opportunity ?? "—"}</dd></div>
              </dl>
            </Panel>
            <Panel title="Meetings" action={<Link className="tap -my-3 text-sm font-medium underline" to="/meetings">Open</Link>}>
              <dl className="grid grid-cols-3 gap-1">
                <Stat label="Upcoming" value={data.meetings.upcoming} />
                <Stat label="This week" value={data.meetings.this_week} />
                <Stat label="Booked" value={data.meetings.booked} />
              </dl>
              {data.meetings.next.length > 0 ? (
                <ul className="mt-3 divide-y divide-line border-t border-line">
                  {data.meetings.next.map((m) => (
                    <li key={m.id} className="flex items-center justify-between gap-2 text-sm">
                      <Link to={`/prospects/${m.prospect_id}`} className="tap truncate font-medium hover:underline">{m.prospect_name}</Link>
                      <span className="tnum shrink-0 text-ink-muted">{fmtDateTime(m.start_at)}</span>
                    </li>))}
                </ul>
              ) : <p className="mt-3 border-t border-line pt-3 text-sm text-ink-muted">No upcoming consultations.</p>}
            </Panel>
          </div>

          <Panel title="Recent activity">
            {data.recent_activity.length === 0 ? <p className="text-ink-muted">Nothing yet.</p> : (
              <ul className="divide-y divide-line">
                {data.recent_activity.map((a, i) => (
                  <li key={i} className="flex flex-col gap-0.5 py-1 sm:flex-row sm:items-center sm:justify-between">
                    <span>{ACTIONS[a.action] ?? titleCase(a.action.replace(".", " "))}
                      {a.entity_type === "prospect" && a.entity_id && <Link className="tap ml-2 text-sm text-ink-muted underline" to={`/prospects/${a.entity_id}`}>open</Link>}</span>
                    <span className="tnum text-sm text-ink-muted">{fmtDateTime(a.created_at)}</span>
                  </li>))}
              </ul>
            )}
          </Panel>
        </div>
      )}
    </>
  );
}
