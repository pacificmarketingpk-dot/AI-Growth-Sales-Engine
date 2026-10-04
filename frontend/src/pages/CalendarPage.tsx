import { Link } from "react-router-dom";
import { CalendarDays, ExternalLink } from "lucide-react";
import { useApi } from "../hooks/useApi";
import type { Meeting } from "../types";
import { Button, EmptyState, ErrorState, PageHeader, Panel, Spinner } from "../components/ui";
import { fmtTime } from "../utils/format";

interface Ev { id: string; summary: string; start: string; end: string; link?: string }

export default function CalendarPage() {
  const cal = useApi<{ connected: boolean; message?: string; events: Ev[]; free_slots: string[] }>("/api/calendar/events?days=14");
  const meetings = useApi<Meeting[]>("/api/meetings?scope=upcoming");
  if (cal.loading && !cal.data) return <Spinner />;
  if (cal.error) return <ErrorState message={cal.error} onRetry={cal.reload} />;

  const ownByEvent = new Set((meetings.data ?? []).map((m) => m.google_event_link).filter(Boolean));
  const days = new Map<string, { label: string; items: { time: string; title: string; link?: string; ours: boolean }[] }>();
  const add = (iso: string, title: string, link?: string, ours = false) => {
    const d = new Date(iso);
    const key = d.toDateString();
    if (!days.has(key)) days.set(key, { label: d.toLocaleDateString(undefined, { weekday: "long", month: "short", day: "numeric" }), items: [] });
    days.get(key)!.items.push({ time: iso.length > 10 ? fmtTime(iso) : "All day", title, link, ours });
  };
  (cal.data?.events ?? []).forEach((e) => add(e.start, e.summary, e.link, ownByEvent.has(e.link ?? "")));
  (meetings.data ?? []).filter((m) => !m.calendar_synced).forEach((m) => add(m.start_at, `${m.title} (not on Google Calendar)`, undefined, true));
  const sorted = [...days.entries()].sort((a, b) => new Date(a[0]).getTime() - new Date(b[0]).getTime());

  return (
    <>
      <PageHeader title="Calendar" description="The next two weeks." />
      {!cal.data?.connected ? (
        <EmptyState icon={<CalendarDays className="h-8 w-8" />} title="No calendar connected." body={cal.data?.message?.includes("expired") ? cal.data.message : "Connect Google Calendar to schedule consultations."}
          action={<Link to="/settings?tab=google"><Button variant="primary">Connect Google Calendar</Button></Link>} />
      ) : (
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,1fr)_300px] [&>*]:min-w-0">
          <div className="space-y-4">
            {sorted.length === 0 ? <EmptyState title="Nothing scheduled in the next two weeks." /> : sorted.map(([k, d]) => (
              <Panel key={k} title={d.label}>
                <ul className="divide-y divide-line">{d.items.map((it, i) => (
                  <li key={i} className="flex min-h-[48px] items-center gap-4 py-2">
                    <span className="tnum w-20 shrink-0 text-sm text-ink-muted">{it.time}</span>
                    <span className={`min-w-0 flex-1 ${it.ours ? "font-semibold" : ""}`}>{it.title}</span>
                    {it.link && <a href={it.link} target="_blank" rel="noopener noreferrer" aria-label={`Open ${it.title} in Google Calendar`} className="flex h-11 w-11 items-center justify-center rounded-md hover:bg-paper"><ExternalLink className="h-4 w-4" /></a>}
                  </li>))}</ul>
              </Panel>))}
          </div>
          <Panel title="Open times">
            <p className="mb-3 text-sm text-ink-muted">Weekdays 9:00–17:00 UTC, minus busy events.</p>
            <ul className="space-y-1.5 text-sm">{cal.data.free_slots.slice(0, 14).map((s) => (
              <li key={s} className="tnum rounded bg-paper px-3 py-2">{new Date(s).toLocaleString(undefined, { weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })}</li>))}</ul>
          </Panel>
        </div>
      )}
    </>
  );
}
