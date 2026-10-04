import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Brain, CalendarPlus, CheckCircle2, ExternalLink, Hand, MessageSquarePlus, Pencil, Trash2 } from "lucide-react";
import { useApi } from "../hooks/useApi";
import { api } from "../services/api";
import { STATUSES, type Conversation, type ProspectDetail as PD, type Qualification } from "../types";
import { ConversationFormModal } from "../components/ConversationForm";
import { MeetingScheduler } from "../components/MeetingScheduler";
import { MessageCard } from "../components/MessageCard";
import { ProspectFormModal } from "../components/ProspectForm";
import { ScoreBar, ScoreBreakdownTable } from "../components/ScoreBar";
import { Button, CategoryBadge, CopyButton, DemoTag, EmptyState, ErrorState, IntentBadge, Notice, Panel, Spinner, Tabs, useToast } from "../components/ui";
import { fmtDate, fmtDateTime, titleCase } from "../utils/format";

type Tab = "analysis" | "outreach" | "conversations" | "qualification" | "details";

const EVIDENCE_TONE = { FACT: "border-ok/40 bg-ok-soft text-ok", ASSUMPTION: "border-signal/40 bg-signal-soft text-high", OPPORTUNITY: "border-medium/40 bg-medium-soft text-medium" };

function AnalysisView({ p, onAnalyze, busy }: { p: PD; onAnalyze: () => void; busy: boolean }) {
  const a = p.latest_analysis;
  if (!a) return (
    <EmptyState icon={<Brain className="h-8 w-8" />} title="Not analyzed yet." body="AI will score fit, find a genuine growth opportunity and draft personalised outreach. It only uses the data on this record and the website, if one is available."
      action={<Button variant="primary" loading={busy} onClick={onAnalyze} icon={<Brain className="h-4 w-4" />}>Analyze prospect</Button>} />
  );
  const r = a.result;
  return (
    <div className="space-y-5">
      <Panel>
        <div className="flex flex-col gap-5 sm:flex-row sm:items-start">
          <div className="shrink-0">
            <p className="text-sm text-ink-muted">Lead score</p>
            <p className="tnum font-display text-[56px] font-semibold leading-none">{a.lead_score}</p>
            <div className="mt-2"><CategoryBadge category={a.category} /></div>
          </div>
          <div className="min-w-0 flex-1">
            <ScoreBar breakdown={a.score_breakdown} score={a.lead_score} />
            <ScoreBreakdownTable breakdown={a.score_breakdown} />
          </div>
        </div>
        <p className="mt-4 border-t border-line pt-3 text-xs text-ink-muted">
          Confidence {Math.round(a.confidence * 100)}% · Version {a.analysis_version} of {p.analysis_count} · {a.model} · {fmtDateTime(a.analyzed_at)} · {a.input_tokens + a.output_tokens} tokens · est. ${a.estimated_cost.toFixed(4)}
        </p>
      </Panel>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2 [&>*]:min-w-0">
        <Panel title="Business problem"><p className="leading-relaxed">{r.business_problem}</p></Panel>
        <Panel title="Growth opportunity"><p className="leading-relaxed">{r.growth_opportunity}</p></Panel>
        <Panel title="Recommended service">
          <p className="font-display text-xl font-semibold">{r.primary_service}</p>
          {r.secondary_service && <p className="mt-1 text-ink-muted">Secondary: {r.secondary_service}</p>}
        </Panel>
        <Panel title="Personalization angle"><p className="leading-relaxed">{r.personalization}</p></Panel>
      </div>

      <Panel title="Why this score">
        <dl className="space-y-3">
          {([["Business fit", r.business_fit], ["Marketing opportunity", r.marketing_opportunity], ["Decision maker relevance", r.decision_maker_relevance],
            ["Digital opportunity", r.digital_opportunity], ["Outreach potential", r.outreach_potential]] as const).map(([k, v]) => (
            <div key={k} className="grid gap-1 sm:grid-cols-[200px_1fr]"><dt className="font-medium">{k}</dt><dd className="text-ink-muted">{v}</dd></div>
          ))}
        </dl>
      </Panel>

      <Panel title="Evidence">
        <p className="mb-3 text-sm text-ink-muted">Facts come from the record or website. Assumptions and opportunities are the AI's reasoning, not verified information.</p>
        <ul className="space-y-2">
          {r.evidence.map((e, i) => (
            <li key={i} className="flex flex-col gap-1 sm:flex-row sm:items-start sm:gap-3">
              <span className={`w-fit shrink-0 rounded border px-2 py-0.5 text-xs font-semibold ${EVIDENCE_TONE[e.type]}`}>{titleCase(e.type)}</span>
              <span>{e.statement}{e.source && <span className="text-sm text-ink-muted"> — {e.source}</span>}</span>
            </li>
          ))}
        </ul>
        {r.insufficient_evidence.length > 0 && (
          <div className="mt-4 border-t border-line pt-3">
            <p className="text-sm font-medium">Insufficient evidence</p>
            <div className="mt-2 flex flex-wrap gap-2">{r.insufficient_evidence.map((x) => <span key={x} className="rounded bg-paper px-2 py-1 text-sm text-ink-muted">{x}</span>)}</div>
          </div>
        )}
      </Panel>

      <Panel title="Website analysis">
        {a.website_retrieved && a.website_analysis ? (
          <dl className="grid gap-x-6 gap-y-3 sm:grid-cols-2">
            {Object.entries(a.website_analysis).map(([k, v]) => <div key={k}><dt className="text-sm font-medium">{titleCase(k)}</dt><dd className="text-ink-muted">{v}</dd></div>)}
          </dl>
        ) : <p className="text-ink-muted">Website analysis unavailable.{!p.website && " No website on this record."}</p>}
      </Panel>
    </div>
  );
}

const Q_FIELDS: { key: keyof Qualification; label: string; max: number }[] = [
  { key: "need", label: "Need", max: 25 }, { key: "budget", label: "Budget", max: 15 }, { key: "authority", label: "Authority", max: 20 },
  { key: "timeline", label: "Timeline", max: 15 }, { key: "current_solution", label: "Current solution", max: 10 }, { key: "urgency", label: "Urgency", max: 15 },
];

function QualificationView({ p, onSaved }: { p: PD; onSaved: (d: PD) => void }) {
  const init = p.qualification;
  const [v, setV] = useState<Record<string, number | string>>(() => ({ ...Object.fromEntries(Q_FIELDS.map((f) => [f.key, (init?.[f.key] as number) ?? 0])), notes: init?.notes ?? "" }));
  const [busy, setBusy] = useState(false);
  const toast = useToast();
  const total = Q_FIELDS.reduce((s, f) => s + Number(v[f.key] || 0), 0);
  const st = total >= 80 ? "Hot" : total >= 60 ? "Qualified" : total >= 35 ? "Nurture" : "Unqualified";
  const save = async () => {
    setBusy(true);
    try { onSaved(await api.put<PD>(`/api/prospects/${p.id}/qualification`, { ...v, notes: v.notes || null })); toast("Qualification saved"); }
    catch (e) { toast((e as Error).message, "error"); } finally { setBusy(false); }
  };
  return (
    <Panel title="Lead qualification" action={<span className="text-sm"><span className="tnum font-display text-xl font-semibold">{total}</span> / 100 · <strong>{st}</strong></span>}>
      <p className="mb-4 text-sm text-ink-muted">Conversation analysis fills these in automatically. Adjust them with what you know.</p>
      <div className="grid gap-x-8 gap-y-5 sm:grid-cols-2">
        {Q_FIELDS.map((f) => (
          <div key={f.key}>
            <div className="flex justify-between text-sm"><label htmlFor={`q-${f.key}`} className="font-medium">{f.label}</label><span className="tnum text-ink-muted">{v[f.key]} / {f.max}</span></div>
            <input id={`q-${f.key}`} type="range" min={0} max={f.max} value={Number(v[f.key])} onChange={(e) => setV({ ...v, [f.key]: Number(e.target.value) })} className="mt-2 h-8 w-full accent-[#245654]" />
          </div>
        ))}
      </div>
      <label className="label mt-5" htmlFor="q-notes">Qualification notes</label>
      <textarea id="q-notes" className="input min-h-[90px]" value={String(v.notes)} onChange={(e) => setV({ ...v, notes: e.target.value })} />
      <div className="mt-4"><Button variant="primary" loading={busy} onClick={save}>Save qualification</Button></div>
    </Panel>
  );
}

export default function ProspectDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const toast = useToast();
  const { data: p, error, loading, reload, setData } = useApi<PD>(`/api/prospects/${id}`);
  const convs = useApi<Conversation[]>(`/api/conversations?prospect_id=${id}`);
  const [tab, setTab] = useState<Tab>("analysis");
  const [busy, setBusy] = useState<string | null>(null);
  const [modal, setModal] = useState<"edit" | "meeting" | "conv" | null>(null);

  if (loading && !p) return <Spinner />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (!p) return null;

  const act = async (key: string, fn: () => Promise<PD>, ok: string) => {
    setBusy(key);
    try { setData(await fn()); toast(ok); } catch (e) { toast((e as Error).message, "error"); } finally { setBusy(null); }
  };
  const analyze = () => {
    const force = !!p.latest_analysis;
    if (force && !confirm("This prospect already has an analysis. Run it again? This uses AI credits and creates a new version.")) return;
    act("analyze", () => api.post<PD>(`/api/prospects/${p.id}/analyze?force=${force}`), "Analysis complete");
  };
  const latestConv = (convs.data ?? []).find((c) => c.analysis);

  return (
    <>
      <Link to="/prospects" className="mb-4 inline-flex min-h-[44px] items-center gap-1 text-sm text-ink-muted hover:text-ink"><ArrowLeft className="h-4 w-4" /> Prospects</Link>

      <header className="mb-5 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2"><h1 className="text-2xl font-semibold sm:text-3xl">{p.name}</h1>{p.is_demo && <DemoTag />}</div>
          <p className="mt-1 text-ink-muted">{[p.job_title, p.company].filter(Boolean).join(" at ") || "No title or company yet"}</p>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <CategoryBadge category={p.category} score={p.lead_score} />
            <label className="sr-only" htmlFor="status">Status</label>
            <select id="status" className="input !min-h-[36px] w-auto !py-1 text-sm" value={p.status}
              onChange={(e) => act("status", () => api.put<PD>(`/api/prospects/${p.id}`, { status: e.target.value }), "Status updated")}>
              {STATUSES.map((s) => <option key={s} value={s}>{titleCase(s)}</option>)}
            </select>
            {p.last_contacted_at && <span className="text-sm text-ink-muted">Last contacted {fmtDate(p.last_contacted_at)}</span>}
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2 sm:flex sm:flex-wrap">
          <Button variant="primary" loading={busy === "analyze"} icon={<Brain className="h-4 w-4" />} onClick={analyze}>{p.latest_analysis ? "Re-analyze" : "Analyze prospect"}</Button>
          <Button loading={busy === "contacted"} icon={<CheckCircle2 className="h-4 w-4" />}
            onClick={() => act("contacted", () => api.post<PD>(`/api/prospects/${p.id}/contacted`, { channel: "LinkedIn" }), "Marked as contacted")}>Mark contacted</Button>
          <Button icon={<CalendarPlus className="h-4 w-4" />} onClick={() => setModal("meeting")}>Book consultation</Button>
          <Button icon={<Pencil className="h-4 w-4" />} onClick={() => setModal("edit")}>Edit</Button>
        </div>
      </header>

      {p.takeover_required && (
        <section className="mb-5 rounded-lg border-2 border-hot bg-white" aria-labelledby="takeover">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-hot/20 bg-hot-soft px-4 py-3 sm:px-5">
            <div><h2 id="takeover" className="font-display text-lg font-semibold text-hot">Human takeover required</h2>
              <p className="text-sm text-ink">AI has identified strong buying intent. This conversation needs you now.</p></div>
            <Button variant="primary" icon={<Hand className="h-4 w-4" />} loading={busy === "takeover"}
              onClick={() => act("takeover", () => api.post<PD>(`/api/prospects/${p.id}/takeover`), "You've taken over this conversation")}>Take over conversation</Button>
          </div>
          {latestConv?.analysis && (
            <div className="grid gap-4 p-4 sm:p-5 lg:grid-cols-2">
              <dl className="space-y-2 text-sm">
                <div><dt className="font-medium">Summary</dt><dd className="text-ink-muted">{latestConv.analysis.summary}</dd></div>
                <div><dt className="font-medium">Pain point</dt><dd className="text-ink-muted">{latestConv.analysis.pain_point}</dd></div>
                <div><dt className="font-medium">Opportunity</dt><dd className="text-ink-muted">{p.latest_analysis?.result.growth_opportunity ?? "—"}</dd></div>
                <div><dt className="font-medium">Recommended service</dt><dd className="text-ink-muted">{latestConv.analysis.recommended_service}</dd></div>
              </dl>
              <div className="space-y-3">
                <div className="rounded-md border border-line p-3"><p className="text-sm font-medium">Suggested response</p><p className="mt-1 whitespace-pre-wrap">{latestConv.analysis.suggested_reply}</p><div className="mt-2"><CopyButton text={latestConv.analysis.suggested_reply} /></div></div>
                {latestConv.analysis.qualification_questions.length > 0 && (
                  <div><p className="text-sm font-medium">Qualification questions</p><ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-ink-muted">{latestConv.analysis.qualification_questions.map((q) => <li key={q}>{q}</li>)}</ul></div>)}
              </div>
            </div>
          )}
        </section>
      )}

      <Tabs<Tab> value={tab} onChange={setTab} tabs={[
        { id: "analysis", label: "AI analysis" }, { id: "outreach", label: "Outreach" },
        { id: "conversations", label: `Conversations${convs.data?.length ? ` (${convs.data.length})` : ""}` },
        { id: "qualification", label: "Qualification" }, { id: "details", label: "Details" },
      ]} />

      {tab === "analysis" && <AnalysisView p={p} onAnalyze={analyze} busy={busy === "analyze"} />}

      {tab === "outreach" && (p.outreach.length === 0 ? (
        <EmptyState title="No messages drafted yet." body="Analyze this prospect to generate a connection message and two follow-ups." action={<Button variant="primary" onClick={analyze} loading={busy === "analyze"}>Analyze prospect</Button>} />
      ) : (
        <div className="space-y-4">
          <Notice>LinkedIn integration not connected. Copy each message and send it yourself, then mark the prospect as contacted.</Notice>
          {[...p.outreach].sort((a, b) => a.kind.localeCompare(b.kind)).map((o) => (
            <div key={o.id}>
              <MessageCard item={o} onChange={(n) => setData({ ...p, outreach: p.outreach.map((x) => (x.id === n.id ? n : x)) })} />
              {!o.contacted_at && (
                <div className="mt-2 flex justify-end">
                  <Button size="sm" variant="ghost" onClick={() => act("contacted", () => api.post<PD>(`/api/prospects/${p.id}/contacted`, { channel: "LinkedIn", outreach_id: o.id }), "Marked as sent")}>I sent this</Button>
                </div>)}
            </div>
          ))}
        </div>
      ))}

      {tab === "conversations" && (
        <div className="space-y-4">
          <Button variant="primary" icon={<MessageSquarePlus className="h-4 w-4" />} onClick={() => setModal("conv")}>Add conversation</Button>
          {(convs.data ?? []).length === 0 ? <EmptyState title="No conversations yet." body="Paste replies from LinkedIn or email to detect intent and qualification signals." /> :
            convs.data!.map((c) => (
              <Panel key={c.id} title={`${c.channel} · ${fmtDate(c.created_at)}`} action={<IntentBadge intent={c.intent} />}>
                <ol className="space-y-2">{c.messages.map((m) => (
                  <li key={m.id} className={`max-w-[85%] rounded-lg px-3 py-2 ${m.sender === "me" ? "ml-auto bg-pine text-white" : "bg-paper"}`}>
                    <span className="sr-only">{m.sender === "me" ? "You" : p.name}: </span>{m.body}</li>))}</ol>
                {c.analysis ? (
                  <dl className="mt-4 grid gap-3 border-t border-line pt-4 text-sm sm:grid-cols-2">
                    {([["Pain point", c.analysis.pain_point], ["Need", c.analysis.need], ["Budget signal", c.analysis.budget_signal], ["Timeline signal", c.analysis.timeline_signal],
                      ["Decision maker", c.analysis.decision_maker], ["Current solution", c.analysis.current_solution], ["Interest level", titleCase(c.analysis.interest_level)],
                      ["Recommended next action", c.analysis.recommended_next_action]] as const).map(([k, v]) => <div key={k}><dt className="font-medium">{k}</dt><dd className="text-ink-muted">{v}</dd></div>)}
                  </dl>
                ) : <div className="mt-4"><Button size="sm" onClick={async () => { try { await api.post(`/api/conversations/${c.id}/analyze`); convs.reload(); reload(); toast("Conversation analyzed"); } catch (e) { toast((e as Error).message, "error"); } }}>Analyze conversation</Button></div>}
              </Panel>
            ))}
        </div>
      )}

      {tab === "qualification" && <QualificationView key={p.updated_at} p={p} onSaved={setData} />}

      {tab === "details" && (
        <Panel title="Record" action={<Button size="sm" variant="danger" icon={<Trash2 className="h-4 w-4" />} onClick={async () => {
          if (!confirm(`Delete ${p.name} and all related analysis, messages and meetings?`)) return;
          await api.del(`/api/prospects/${p.id}`); toast("Prospect deleted"); nav("/prospects");
        }}>Delete</Button>}>
          <dl className="grid gap-x-8 gap-y-3 sm:grid-cols-2">
            {([["Email", p.email], ["Phone", p.phone], ["Industry", p.industry], ["Country", p.country], ["Company size", p.company_size], ["Source", p.source], ["Added", fmtDate(p.created_at)]] as const).map(([k, v]) => (
              <div key={k}><dt className="text-sm text-ink-muted">{k}</dt><dd>{v || "—"}</dd></div>))}
            <div><dt className="text-sm text-ink-muted">Website</dt><dd>{p.website ? <a className="inline-flex items-center gap-1 underline" href={p.website} target="_blank" rel="noopener noreferrer">{p.website}<ExternalLink className="h-3 w-3" /></a> : "—"}</dd></div>
            <div><dt className="text-sm text-ink-muted">LinkedIn</dt><dd>{p.linkedin_url ? <a className="inline-flex items-center gap-1 break-all underline" href={p.linkedin_url} target="_blank" rel="noopener noreferrer">Open profile<ExternalLink className="h-3 w-3" /></a> : "—"}</dd></div>
            <div className="sm:col-span-2"><dt className="text-sm text-ink-muted">Company description</dt><dd className="whitespace-pre-wrap">{p.company_description || "—"}</dd></div>
            <div className="sm:col-span-2"><dt className="text-sm text-ink-muted">Notes</dt><dd className="whitespace-pre-wrap">{p.notes || "—"}</dd></div>
          </dl>
        </Panel>
      )}

      {modal === "edit" && <ProspectFormModal open initial={p} onClose={() => setModal(null)} onSaved={(d) => { setData(d); setModal(null); }} />}
      <MeetingScheduler open={modal === "meeting"} prospect={p} onClose={() => setModal(null)} onBooked={() => nav("/meetings")} />
      {modal === "conv" && <ConversationFormModal open prospects={[p]} defaultProspectId={p.id} onClose={() => setModal(null)} onSaved={() => { setModal(null); convs.reload(); reload(); setTab("conversations"); }} />}
    </>
  );
}
