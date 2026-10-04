import { useState } from "react";
import { Link } from "react-router-dom";
import { Brain } from "lucide-react";
import { useApi } from "../hooks/useApi";
import { useBulkAnalyze } from "../hooks/useBulkAnalyze";
import type { Prospect } from "../types";
import { BulkProgress } from "../components/BulkProgress";
import { ScoreBar } from "../components/ScoreBar";
import { Button, CategoryBadge, DemoTag, EmptyState, ErrorState, PageHeader, Panel, Spinner } from "../components/ui";

export default function Analysis() {
  const analyzed = useApi<{ items: Prospect[]; total: number }>("/api/prospects?analyzed=true&sort=lead_score&limit=200");
  const pending = useApi<{ items: Prospect[]; total: number }>("/api/prospects?analyzed=false&limit=200");
  const usage = useApi<{ analyses: number; input_tokens: number; output_tokens: number; estimated_cost: number }>("/api/analysis/usage");
  const [sel, setSel] = useState<Set<number>>(new Set());
  const bulk = useBulkAnalyze(() => { analyzed.reload(); pending.reload(); usage.reload(); setSel(new Set()); });

  if (analyzed.loading && !analyzed.data) return <Spinner />;
  if (analyzed.error) return <ErrorState message={analyzed.error} onRetry={analyzed.reload} />;
  const todo = pending.data?.items ?? [];
  const done = analyzed.data?.items ?? [];

  return (
    <>
      <PageHeader title="AI Analysis" description="Score prospects and find a real growth opportunity for each one. Each prospect is analyzed once unless you ask again." />
      {bulk.job && <BulkProgress job={bulk.job} onClose={bulk.clear} />}
      {bulk.error && <div className="mb-4"><ErrorState message={bulk.error} /></div>}

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,1fr)_320px] [&>*]:min-w-0">
        <div className="space-y-5">
          <Panel title={`Waiting for analysis (${pending.data?.total ?? 0})`} action={todo.length > 0 && (
            <Button size="sm" variant="primary" disabled={!sel.size || !!(bulk.job && bulk.job.status !== "done")} icon={<Brain className="h-4 w-4" />} onClick={() => bulk.start([...sel])}>Analyze selected ({sel.size})</Button>)}>
            {todo.length === 0 ? <p className="text-ink-muted">Every prospect has been analyzed.</p> : (
              <>
                <label className="mb-2 flex min-h-[44px] items-center gap-3 text-sm font-medium">
                  <input type="checkbox" className="h-5 w-5" checked={todo.slice(0, 25).every((p) => sel.has(p.id))} onChange={(e) => setSel(e.target.checked ? new Set(todo.slice(0, 25).map((p) => p.id)) : new Set())} />
                  Select first {Math.min(25, todo.length)}
                </label>
                <ul className="divide-y divide-line">{todo.map((p) => (
                  <li key={p.id} className="flex min-h-[52px] items-center gap-3">
                    <input type="checkbox" className="h-5 w-5" aria-label={`Select ${p.name}`} checked={sel.has(p.id)} onChange={() => setSel((s) => { const n = new Set(s); n.has(p.id) ? n.delete(p.id) : n.add(p.id); return n; })} />
                    <Link to={`/prospects/${p.id}`} className="tap min-w-0 flex-1 truncate hover:underline"><span className="truncate"><span className="font-medium">{p.name}</span><span className="text-ink-muted"> {p.company ? `· ${p.company}` : ""}</span></span></Link>
                    {p.is_demo && <DemoTag />}
                  </li>))}</ul>
              </>
            )}
          </Panel>

          <Panel title={`Analyzed (${analyzed.data?.total ?? 0})`}>
            {done.length === 0 ? <EmptyState title="No analyses yet." body="Select prospects above and analyze them." /> : (
              <ul className="divide-y divide-line">{done.map((p) => (
                <li key={p.id} className="py-3">
                  <Link to={`/prospects/${p.id}`} className="grid gap-2 sm:grid-cols-[1fr_220px] sm:items-center">
                    <div className="min-w-0"><p className="truncate font-medium">{p.name} {p.is_demo && <DemoTag />}</p><p className="truncate text-sm text-ink-muted">{p.company ?? "—"}</p></div>
                    <div><div className="mb-1.5"><CategoryBadge category={p.category} score={p.lead_score} /></div><ScoreBar breakdown={p.score_breakdown} score={p.lead_score} compact /></div>
                  </Link>
                </li>))}</ul>
            )}
          </Panel>
        </div>

        <Panel title="AI usage">
          {usage.data ? (
            <dl className="space-y-3">
              <div className="flex justify-between"><dt className="text-ink-muted">Analyses run</dt><dd className="tnum font-semibold">{usage.data.analyses}</dd></div>
              <div className="flex justify-between"><dt className="text-ink-muted">Input tokens</dt><dd className="tnum font-semibold">{usage.data.input_tokens.toLocaleString()}</dd></div>
              <div className="flex justify-between"><dt className="text-ink-muted">Output tokens</dt><dd className="tnum font-semibold">{usage.data.output_tokens.toLocaleString()}</dd></div>
              <div className="flex justify-between border-t border-line pt-3"><dt className="text-ink-muted">Estimated cost</dt><dd className="tnum font-semibold">${usage.data.estimated_cost.toFixed(2)}</dd></div>
              <p className="text-xs text-ink-muted">Estimates use list prices per model and may differ from your provider's bill.</p>
            </dl>
          ) : <Spinner />}
        </Panel>
      </div>
    </>
  );
}
