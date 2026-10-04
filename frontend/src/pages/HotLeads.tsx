import { useState } from "react";
import { Link } from "react-router-dom";
import { Flame } from "lucide-react";
import { useApi } from "../hooks/useApi";
import { api } from "../services/api";
import type { LeadCard } from "../types";
import { MeetingScheduler } from "../components/MeetingScheduler";
import { Button, CategoryBadge, DemoTag, EmptyState, ErrorState, IntentBadge, PageHeader, Spinner, useToast } from "../components/ui";

export default function HotLeads() {
  const [sort, setSort] = useState("score");
  const { data, error, loading, reload } = useApi<LeadCard[]>(`/api/leads/hot?sort=${sort}`);
  const [book, setBook] = useState<LeadCard | null>(null);
  const toast = useToast();

  return (
    <>
      <PageHeader title="Hot Leads" description="Prospects scoring 75+, showing buying intent, or qualified."
        actions={<label className="flex items-center gap-2 text-sm"><span className="text-ink-muted">Sort by</span>
          <select className="input w-auto" value={sort} onChange={(e) => setSort(e.target.value)}>
            <option value="score">Lead score</option><option value="intent">Intent</option><option value="recent">Recent response</option><option value="opportunity">Qualification</option>
          </select></label>} />
      {loading && !data ? <Spinner /> : error ? <ErrorState message={error} onRetry={reload} /> : !data?.length ? (
        <EmptyState icon={<Flame className="h-8 w-8" />} title="No hot leads yet." body="Qualified conversations will appear here." />
      ) : (
        <ul className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {data.map((c) => (
            <li key={c.prospect.id} className={`panel flex flex-col ${c.takeover_required ? "border-hot" : ""}`}>
              <div className="flex-1 p-4">
                {c.takeover_required && <p className="mb-2 text-xs font-semibold text-hot">Human takeover required</p>}
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0"><p className="truncate font-display text-lg font-semibold">{c.prospect.name}</p><p className="truncate text-sm text-ink-muted">{c.prospect.company ?? "—"}</p></div>
                  <CategoryBadge category={c.prospect.category} score={c.prospect.lead_score} />
                </div>
                <div className="mt-2 flex flex-wrap gap-2"><IntentBadge intent={c.intent} />{c.qualification && <span className="rounded bg-paper px-2 py-0.5 text-xs font-medium">Qualification {c.qualification.score}</span>}{c.prospect.is_demo && <DemoTag />}</div>
                <dl className="mt-3 space-y-2 text-sm">
                  <div><dt className="font-medium">Pain point</dt><dd className="text-ink-muted">{c.pain_point ?? "Insufficient evidence."}</dd></div>
                  <div><dt className="font-medium">Growth opportunity</dt><dd className="text-ink-muted">{c.growth_opportunity ?? "—"}</dd></div>
                  <div><dt className="font-medium">Recommended service</dt><dd className="text-ink-muted">{c.recommended_service ?? "—"}</dd></div>
                </dl>
              </div>
              <div className="grid grid-cols-2 gap-2 border-t border-line p-3">
                <Link to={`/prospects/${c.prospect.id}`}><Button size="sm" className="w-full">View lead</Button></Link>
                {c.conversation_id ? <Link to={`/conversations?id=${c.conversation_id}`}><Button size="sm" className="w-full">View conversation</Button></Link> : <Button size="sm" disabled>No conversation</Button>}
                <Button size="sm" disabled={!c.takeover_required} onClick={async () => { await api.post(`/api/prospects/${c.prospect.id}/takeover`); toast("You've taken over this conversation"); reload(); }}>{c.takeover_required ? "Take over" : "Taken over"}</Button>
                <Button size="sm" variant="primary" onClick={() => setBook(c)}>Book meeting</Button>
              </div>
            </li>
          ))}
        </ul>
      )}
      <MeetingScheduler open={!!book} prospect={book?.prospect ?? null} onClose={() => setBook(null)} onBooked={reload} />
    </>
  );
}
