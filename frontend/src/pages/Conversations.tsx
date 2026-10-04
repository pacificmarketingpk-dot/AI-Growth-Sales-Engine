import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { MessageSquarePlus, MessagesSquare } from "lucide-react";
import { useApi } from "../hooks/useApi";
import { api } from "../services/api";
import type { Conversation, Prospect } from "../types";
import { ConversationFormModal } from "../components/ConversationForm";
import { Button, CopyButton, EmptyState, ErrorState, IntentBadge, PageHeader, Panel, Spinner, useToast } from "../components/ui";
import { fmtDateTime, titleCase } from "../utils/format";

export default function Conversations() {
  const [params, setParams] = useSearchParams();
  const { data, error, loading, reload } = useApi<Conversation[]>("/api/conversations");
  const prospects = useApi<{ items: Prospect[] }>("/api/prospects?limit=500&sort=name&order=asc");
  const [activeId, setActiveId] = useState<number | null>(Number(params.get("id")) || null);
  const [adding, setAdding] = useState(false);
  const [busy, setBusy] = useState(false);
  const toast = useToast();

  useEffect(() => { if (!activeId && data?.length && window.innerWidth >= 1024) setActiveId(data[0].id); }, [data, activeId]);
  const active = data?.find((c) => c.id === activeId) ?? null;
  const analyze = async (c: Conversation) => {
    setBusy(true);
    try { await api.post(`/api/conversations/${c.id}/analyze`); await reload(); toast("Conversation analyzed"); }
    catch (e) { toast((e as Error).message, "error"); } finally { setBusy(false); }
  };
  const a = active?.analysis;

  return (
    <>
      <PageHeader title="Conversations" description="Paste replies from LinkedIn, email or calls. AI detects intent and qualification signals."
        actions={<Button variant="primary" icon={<MessageSquarePlus className="h-4 w-4" />} onClick={() => setAdding(true)}>Add conversation</Button>} />
      {loading && !data ? <Spinner /> : error ? <ErrorState message={error} onRetry={reload} /> : !data?.length ? (
        <EmptyState icon={<MessagesSquare className="h-8 w-8" />} title="No conversations yet." body="When a prospect replies, paste the thread here to classify intent." action={<Button variant="primary" onClick={() => setAdding(true)}>Add conversation</Button>} />
      ) : (
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-[340px_minmax(0,1fr)] [&>*]:min-w-0">
          <ul className={`panel divide-y divide-line self-start ${active ? "hidden lg:block" : ""}`}>
            {data.map((c) => (
              <li key={c.id}>
                <button onClick={() => { setActiveId(c.id); setParams({ id: String(c.id) }, { replace: true }); }} aria-current={c.id === activeId}
                  className={`w-full px-4 py-3 text-left hover:bg-paper ${c.id === activeId ? "bg-paper shadow-[inset_3px_0_0_#D98E04]" : ""}`}>
                  <div className="flex items-center justify-between gap-2"><span className="truncate font-medium">{c.prospect_name}</span><span className="tnum shrink-0 text-xs text-ink-muted">{fmtDateTime(c.created_at)}</span></div>
                  <p className="truncate text-sm text-ink-muted">{c.messages[c.messages.length - 1]?.body}</p>
                  <div className="mt-1.5"><IntentBadge intent={c.intent} /></div>
                </button>
              </li>))}
          </ul>

          {active && (
            <div className="space-y-5">
              <button className="min-h-[44px] text-sm text-ink-muted underline lg:hidden" onClick={() => { setActiveId(null); setParams({}, { replace: true }); }}>All conversations</button>
              <Panel title={active.prospect_name} action={<Link className="text-sm underline" to={`/prospects/${active.prospect_id}`}>Open prospect</Link>}>
                <ol className="space-y-2">{active.messages.map((m) => (
                  <li key={m.id} className={`max-w-[85%] rounded-lg px-3 py-2 ${m.sender === "me" ? "ml-auto bg-pine text-white" : "bg-paper"}`}>
                    <span className="sr-only">{m.sender === "me" ? "You" : active.prospect_name}: </span>{m.body}</li>))}</ol>
                {!a && <div className="mt-4"><Button variant="primary" loading={busy} onClick={() => analyze(active)}>Analyze conversation</Button></div>}
              </Panel>
              {a && (
                <>
                  <Panel title="Intent" action={<Button size="sm" loading={busy} onClick={() => analyze(active)}>Re-analyze</Button>}>
                    <div className="flex flex-wrap items-center gap-3"><IntentBadge intent={active.intent} /><span className="text-sm text-ink-muted">Interest {titleCase(a.interest_level)} · confidence {Math.round(a.confidence * 100)}%</span></div>
                    <p className="mt-3">{a.summary}</p>
                    {a.human_takeover && <p className="mt-3 rounded-md bg-hot-soft px-3 py-2 text-sm font-semibold text-hot">Recommended: human takeover</p>}
                  </Panel>
                  <Panel title="Signals">
                    <dl className="grid gap-4 sm:grid-cols-2">
                      {([["Pain point", a.pain_point], ["Need", a.need], ["Budget signal", a.budget_signal], ["Timeline signal", a.timeline_signal], ["Decision maker", a.decision_maker],
                        ["Current solution", a.current_solution], ["Recommended service", a.recommended_service], ["Recommended next action", a.recommended_next_action]] as const).map(([k, v]) => (
                        <div key={k}><dt className="text-sm font-medium">{k}</dt><dd className="text-ink-muted">{v}</dd></div>))}
                    </dl>
                  </Panel>
                  <Panel title="Suggested reply">
                    <p className="whitespace-pre-wrap leading-relaxed">{a.suggested_reply}</p>
                    <div className="mt-3"><CopyButton text={a.suggested_reply} /></div>
                    {a.qualification_questions.length > 0 && (<><p className="mt-4 text-sm font-medium">Questions to qualify</p><ul className="mt-1 list-disc space-y-1 pl-5 text-ink-muted">{a.qualification_questions.map((q) => <li key={q}>{q}</li>)}</ul></>)}
                  </Panel>
                </>
              )}
            </div>
          )}
        </div>
      )}
      {adding && <ConversationFormModal open prospects={prospects.data?.items ?? []} onClose={() => setAdding(false)}
        onSaved={(c) => { setAdding(false); reload(); setActiveId(c.id); }} />}
    </>
  );
}
