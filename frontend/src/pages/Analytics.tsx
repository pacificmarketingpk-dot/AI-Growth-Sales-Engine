import { useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useApi } from "../hooks/useApi";
import { EmptyState, ErrorState, PageHeader, Panel, Spinner } from "../components/ui";
import { titleCase } from "../utils/format";

interface A {
  counts: Record<string, number>; average_score: number | null; rates: Record<string, number>;
  funnel: { stage: string; value: number }[]; weekly: { week: string; added: number; analyzed: number }[];
  score_distribution: { category: string; count: number }[]; intents: { intent: string; count: number }[];
}
const CAT_COLORS: Record<string, string> = { HOT: "#B93A0E", HIGH: "#9A6408", MEDIUM: "#2B6A88", LOW: "#5E6B68" };
const RATES = [
  ["contact_rate", "Contact rate", "Contacted ÷ prospects"], ["response_rate", "Response rate", "Responses ÷ contacts"],
  ["qualification_rate", "Qualification rate", "Qualified ÷ responses"], ["meeting_rate", "Meeting rate", "Meetings ÷ qualified"],
  ["proposal_rate", "Proposal rate", "Proposals ÷ meetings"], ["win_rate", "Win rate", "Won ÷ proposals"],
] as const;
const axis = { fontSize: 12, fill: "#56665F" };

export default function Analytics() {
  const [days, setDays] = useState(90);
  const [demo, setDemo] = useState(false);
  const { data, error, loading, reload } = useApi<A>(`/api/analytics?days=${days}&include_demo=${demo}`);

  return (
    <>
      <PageHeader title="Analytics" description="How well each stage of your pipeline converts."
        actions={<>
          <label className="flex min-h-[44px] items-center gap-2 rounded-md border border-line bg-white px-3 text-sm"><input type="checkbox" className="h-4 w-4" checked={demo} onChange={(e) => setDemo(e.target.checked)} />Include demo data</label>
          <select className="input w-auto" aria-label="Period" value={days} onChange={(e) => setDays(Number(e.target.value))}>
            <option value={30}>Last 30 days</option><option value={90}>Last 90 days</option><option value={180}>Last 6 months</option><option value={365}>Last year</option>
          </select></>} />
      {loading && !data ? <Spinner /> : error ? <ErrorState message={error} onRetry={reload} /> : !data ? null : data.counts.prospects_added === 0 ? (
        <EmptyState title="No data for this period." body="Analytics fill in as you add, analyze and contact prospects." />
      ) : (
        <div className="space-y-5">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-6">
            {RATES.map(([k, label, formula]) => (
              <div key={k} className="panel p-4"><p className="text-sm text-ink-muted">{label}</p><p className="tnum font-display text-[28px] font-semibold">{data.rates[k]}%</p><p className="text-xs text-ink-muted">{formula}</p></div>
            ))}
          </div>
          <div className="grid grid-cols-1 gap-5 lg:grid-cols-2 [&>*]:min-w-0">
            <Panel title="Funnel">
              <div className="h-72"><ResponsiveContainer><BarChart data={data.funnel} layout="vertical" margin={{ left: 8, right: 16 }}>
                <CartesianGrid horizontal={false} stroke="#DCE3E0" /><XAxis type="number" tick={axis} allowDecimals={false} /><YAxis type="category" dataKey="stage" tick={axis} width={80} />
                <Tooltip /><Bar dataKey="value" name="Prospects" fill="#245654" radius={[0, 3, 3, 0]} />
              </BarChart></ResponsiveContainer></div>
            </Panel>
            <Panel title="Prospects added and analyzed per week">
              <div className="h-72"><ResponsiveContainer><LineChart data={data.weekly} margin={{ right: 16 }}>
                <CartesianGrid stroke="#DCE3E0" vertical={false} /><XAxis dataKey="week" tick={axis} tickFormatter={(w) => new Date(w).toLocaleDateString(undefined, { month: "short", day: "numeric" })} />
                <YAxis tick={axis} allowDecimals={false} width={32} /><Tooltip />
                <Line type="monotone" dataKey="added" name="Added" stroke="#245654" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="analyzed" name="Analyzed" stroke="#D98E04" strokeWidth={2} strokeDasharray="5 3" dot={false} />
              </LineChart></ResponsiveContainer></div>
              <p className="mt-2 text-xs text-ink-muted">Solid: added · Dashed: analyzed</p>
            </Panel>
            <Panel title={`Lead score distribution${data.average_score != null ? ` · average ${data.average_score}` : ""}`}>
              <div className="h-60"><ResponsiveContainer><BarChart data={data.score_distribution}>
                <CartesianGrid stroke="#DCE3E0" vertical={false} /><XAxis dataKey="category" tick={axis} tickFormatter={titleCase} /><YAxis tick={axis} allowDecimals={false} width={32} /><Tooltip />
                <Bar dataKey="count" name="Prospects" radius={[3, 3, 0, 0]}>{data.score_distribution.map((d) => <Cell key={d.category} fill={CAT_COLORS[d.category]} />)}</Bar>
              </BarChart></ResponsiveContainer></div>
            </Panel>
            <Panel title="Conversation intent">
              {data.intents.length === 0 ? <p className="text-ink-muted">No analyzed conversations in this period.</p> : (
                <ul className="space-y-2">{data.intents.map((i) => {
                  const max = Math.max(...data.intents.map((x) => x.count));
                  return (<li key={i.intent} className="grid grid-cols-[140px_1fr_32px] items-center gap-3 text-sm"><span>{titleCase(i.intent)}</span>
                    <div className="h-2.5 rounded-sm bg-line"><div className="h-2.5 rounded-sm bg-pine-3" style={{ width: `${(i.count / max) * 100}%` }} /></div><span className="tnum text-right">{i.count}</span></li>);
                })}</ul>)}
            </Panel>
          </div>
        </div>
      )}
    </>
  );
}
