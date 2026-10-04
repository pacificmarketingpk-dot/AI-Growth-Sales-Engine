import { useState } from "react";
import { Link } from "react-router-dom";
import { CalendarPlus, ExternalLink, Handshake } from "lucide-react";
import { useApi } from "../hooks/useApi";
import { api } from "../services/api";
import type { Meeting, Prospect } from "../types";
import { MeetingScheduler } from "../components/MeetingScheduler";
import { Button, CategoryBadge, DemoTag, EmptyState, ErrorState, Field, Modal, PageHeader, Spinner, Tabs, useToast } from "../components/ui";
import { categoryOf, fmtDateTime, titleCase } from "../utils/format";

function MeetingCard({ m, onSaved }: { m: Meeting; onSaved: (m: Meeting) => void }) {
  const [notes, setNotes] = useState(m.meeting_notes ?? "");
  const [next, setNext] = useState(m.next_action ?? "");
  const [busy, setBusy] = useState(false);
  const toast = useToast();
  const save = async (extra: Record<string, string> = {}) => {
    setBusy(true);
    try { onSaved(await api.put<Meeting>(`/api/meetings/${m.id}`, { meeting_notes: notes, next_action: next, ...extra })); toast("Meeting updated"); }
    catch (e) { toast((e as Error).message, "error"); } finally { setBusy(false); }
  };
  const p = m.prospect;
  return (
    <article className="panel">
      <header className="flex flex-col gap-2 border-b border-line px-4 py-3 sm:flex-row sm:items-center sm:justify-between sm:px-5">
        <div className="min-w-0">
          <p className="tnum font-display text-lg font-semibold">{fmtDateTime(m.start_at)} <span className="font-sans text-sm font-normal text-ink-muted">· {m.duration_minutes} min</span></p>
          <p className="truncate text-sm text-ink-muted">{m.meeting_type}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {p.is_demo && <DemoTag />}
          <span className="rounded bg-paper px-2 py-0.5 text-xs font-medium">{titleCase(m.status)}</span>
          {m.calendar_synced ? (m.google_event_link && <a href={m.google_event_link} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-sm underline">Google Calendar<ExternalLink className="h-3 w-3" /></a>)
            : <span className="text-xs text-ink-muted">Not on a calendar</span>}
        </div>
      </header>
      <div className="grid gap-5 p-4 sm:p-5 lg:grid-cols-2">
        <dl className="space-y-2.5 text-sm">
          <div className="flex items-center gap-2"><Link className="font-semibold hover:underline" to={`/prospects/${p.id}`}>{p.name}</Link><span className="text-ink-muted">{p.company}</span><CategoryBadge category={categoryOf(p.lead_score)} score={p.lead_score} /></div>
          <div><dt className="font-medium">Business problem</dt><dd className="text-ink-muted">{p.business_problem ?? "—"}</dd></div>
          <div><dt className="font-medium">Growth opportunity</dt><dd className="text-ink-muted">{p.growth_opportunity ?? "—"}</dd></div>
          <div><dt className="font-medium">Recommended service</dt><dd className="text-ink-muted">{p.recommended_service ?? "—"}</dd></div>
          <div><dt className="font-medium">Qualification</dt><dd className="text-ink-muted">{p.qualification_notes ?? "Not qualified yet"}</dd></div>
          {m.notes && <div><dt className="font-medium">Booking notes</dt><dd className="text-ink-muted">{m.notes}</dd></div>}
        </dl>
        <div className="space-y-3">
          <Field label="Meeting notes">{(id) => <textarea id={id} className="input min-h-[110px]" value={notes} onChange={(e) => setNotes(e.target.value)} />}</Field>
          <Field label="Next action">{(id) => <input id={id} className="input" value={next} onChange={(e) => setNext(e.target.value)} placeholder="Send proposal by Friday" />}</Field>
          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="primary" loading={busy} onClick={() => save()}>Save notes</Button>
            {m.status === "scheduled" && <><Button size="sm" onClick={() => save({ status: "completed" })}>Mark completed</Button><Button size="sm" variant="ghost" onClick={() => save({ status: "no_show" })}>No-show</Button></>}
          </div>
        </div>
      </div>
    </article>
  );
}

export default function Meetings() {
  const [tab, setTab] = useState<"upcoming" | "past">("upcoming");
  const { data, error, loading, reload, setData } = useApi<Meeting[]>(`/api/meetings?scope=${tab}`);
  const prospects = useApi<{ items: Prospect[] }>("/api/prospects?limit=500&sort=lead_score");
  const [pick, setPick] = useState(false);
  const [chosen, setChosen] = useState<Prospect | null>(null);
  const [pid, setPid] = useState("");

  return (
    <>
      <PageHeader title="Meetings" description="Every consultation, with the research you need to walk in prepared."
        actions={<Button variant="primary" icon={<CalendarPlus className="h-4 w-4" />} onClick={() => setPick(true)}>Book consultation</Button>} />
      <Tabs value={tab} onChange={setTab} tabs={[{ id: "upcoming", label: "Upcoming" }, { id: "past", label: "Past" }]} />
      {loading && !data ? <Spinner /> : error ? <ErrorState message={error} onRetry={reload} /> : !data?.length ? (
        <EmptyState icon={<Handshake className="h-8 w-8" />} title={tab === "upcoming" ? "No upcoming meetings." : "No past meetings."} body="Book a consultation from a qualified lead." action={<Link to="/hot-leads"><Button>Open Hot Leads</Button></Link>} />
      ) : (
        <ul className="space-y-4">{(tab === "past" ? [...data].reverse() : data).map((m) => (
          <li key={m.id}><MeetingCard m={m} onSaved={(n) => setData(data.map((x) => (x.id === n.id ? n : x)))} /></li>))}</ul>
      )}
      <Modal open={pick} onClose={() => setPick(false)} title="Who is the meeting with?"
        footer={<><Button onClick={() => setPick(false)}>Cancel</Button><Button variant="primary" disabled={!pid} onClick={() => { setChosen(prospects.data?.items.find((p) => p.id === Number(pid)) ?? null); setPick(false); }}>Continue</Button></>}>
        <Field label="Prospect">{(id) => (
          <select id={id} className="input" value={pid} onChange={(e) => setPid(e.target.value)}>
            <option value="">Choose a prospect</option>
            {prospects.data?.items.map((p) => <option key={p.id} value={p.id}>{p.name}{p.company ? ` — ${p.company}` : ""}{p.lead_score != null ? ` (${p.lead_score})` : ""}</option>)}
          </select>)}</Field>
      </Modal>
      <MeetingScheduler open={!!chosen} prospect={chosen} onClose={() => setChosen(null)} onBooked={() => { setTab("upcoming"); reload(); }} />
    </>
  );
}
