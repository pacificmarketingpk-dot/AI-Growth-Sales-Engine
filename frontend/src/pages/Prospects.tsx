import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Brain, Download, FileSpreadsheet, Search, Sparkles, Upload, UserPlus } from "lucide-react";
import { useApi } from "../hooks/useApi";
import { useBulkAnalyze } from "../hooks/useBulkAnalyze";
import { api } from "../services/api";
import { STATUSES, type Prospect } from "../types";
import { BulkProgress } from "../components/BulkProgress";
import { CsvImportModal } from "../components/CsvImport";
import { ProspectFormModal } from "../components/ProspectForm";
import { SheetsModal } from "../components/SheetsImport";
import { ScoreBar } from "../components/ScoreBar";
import { Button, CategoryBadge, DemoTag, EmptyState, ErrorState, Field, Notice, PageHeader, Spinner, StatusBadge } from "../components/ui";
import { fmtDate, titleCase } from "../utils/format";

function Discovery({ onImport, onSheets }: { onImport: () => void; onSheets: () => void }) {
  const [open, setOpen] = useState(false);
  const [c, setC] = useState({ country: "", industry: "", company_size: "", job_titles: "", business_type: "", keywords: "", min_score: 75, limit: 50 });
  const [res, setRes] = useState<{ connected: boolean; message?: string; results: unknown[] } | null>(null);
  const [busy, setBusy] = useState(false);
  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true);
    try { setRes(await api.post("/api/discovery/search", { ...c, job_titles: c.job_titles.split(",").map((s) => s.trim()).filter(Boolean) })); }
    finally { setBusy(false); }
  };
  const inp = (k: keyof typeof c, label: string, ph = "", type = "text") => (
    <Field label={label}>{(id) => <input id={id} type={type} className="input" placeholder={ph} value={c[k]} onChange={(e) => setC({ ...c, [k]: type === "number" ? Number(e.target.value) : e.target.value })} />}</Field>
  );
  return (
    <section className="panel mb-5">
      <button onClick={() => setOpen(!open)} aria-expanded={open} className="flex min-h-[52px] w-full items-center justify-between gap-3 px-4 text-left sm:px-5">
        <span className="flex items-center gap-2 font-display font-semibold"><Sparkles className="h-4 w-4 text-signal" aria-hidden />Prospect discovery</span>
        <span className="text-sm text-ink-muted">{open ? "Hide" : "Define your ideal prospect"}</span>
      </button>
      {open && (
        <form onSubmit={submit} className="border-t border-line p-4 sm:p-5">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {inp("country", "Country", "USA")}{inp("industry", "Industry", "SaaS")}{inp("company_size", "Company size", "10–200")}
            {inp("job_titles", "Job titles", "Founder, CEO, CMO")}{inp("business_type", "Business type", "B2B")}{inp("keywords", "Keywords", "demo, trial")}
            {inp("min_score", "Lead score minimum", "", "number")}{inp("limit", "Number of prospects", "", "number")}
          </div>
          <div className="mt-4"><Button type="submit" variant="primary" loading={busy} icon={<Search className="h-4 w-4" />}>Find prospects</Button></div>
          {res && !res.connected && (
            <div className="mt-4 rounded-lg border border-signal/40 bg-signal-soft p-4">
              <p className="font-semibold">No prospecting source connected.</p>
              <p className="mt-1 text-sm text-ink-muted">Discovery only searches licensed, permitted data providers. Nothing was searched and no prospects were created.</p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Link to="/settings?tab=sources"><Button size="sm">Connect data source</Button></Link>
                <Button size="sm" onClick={onImport}>Import CSV</Button>
                <Button size="sm" onClick={onSheets}>Import Google Sheet</Button>
              </div>
            </div>
          )}
        </form>
      )}
    </section>
  );
}

export default function Prospects() {
  const [params, setParams] = useSearchParams();
  const nav = useNavigate();
  const [q, setQ] = useState("");
  const [status, setStatus] = useState(params.get("status") ?? "");
  const [minScore, setMinScore] = useState("");
  const [sort, setSort] = useState("created_at");
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [modal, setModal] = useState<"add" | "csv" | "sheets" | null>(params.get("import") ? "csv" : params.get("add") ? "add" : null);
  const qs = new URLSearchParams({ sort, order: sort === "name" || sort === "company" ? "asc" : "desc", limit: "200" });
  if (q) qs.set("q", q); if (status) qs.set("status", status); if (minScore) qs.set("min_score", minScore);
  const { data, error, loading, reload } = useApi<{ items: Prospect[]; total: number }>(`/api/prospects?${qs}`);
  const bulk = useBulkAnalyze(() => { reload(); setSelected(new Set()); });

  useEffect(() => { if (params.get("import") || params.get("add")) setParams({}, { replace: true }); }, [params, setParams]);

  const items = data?.items ?? [];
  const toggle = (id: number) => setSelected((s) => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n; });
  const allSel = items.length > 0 && items.every((p) => selected.has(p.id));
  const analyzeSelected = () => {
    const ids = [...selected];
    const already = items.filter((p) => selected.has(p.id) && p.lead_score != null).length;
    let force = false;
    if (already) {
      force = confirm(`${already} of ${ids.length} already have an analysis. Re-analyze them too? This uses AI credits.\n\nOK = re-analyze all, Cancel = only analyze new ones.`);
    }
    bulk.start(ids, force);
  };

  return (
    <>
      <PageHeader title="Prospects" description="Everyone you're researching or talking to."
        actions={<>
          <Button variant="primary" icon={<UserPlus className="h-4 w-4" />} onClick={() => setModal("add")}>Add prospect</Button>
          <Button icon={<Upload className="h-4 w-4" />} onClick={() => setModal("csv")}>Import CSV</Button>
          <Button icon={<FileSpreadsheet className="h-4 w-4" />} onClick={() => setModal("sheets")}>Google Sheet</Button>
          <a href={api.url("/api/export/csv")}><Button icon={<Download className="h-4 w-4" />}>Export</Button></a>
        </>} />
      <Discovery onImport={() => setModal("csv")} onSheets={() => setModal("sheets")} />

      <div className="mb-4 grid grid-cols-2 gap-2 sm:grid-cols-[1fr_180px_140px_170px]">
        <div className="relative col-span-2 sm:col-span-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-muted" aria-hidden />
          <input className="input pl-9" placeholder="Search name, company, email" aria-label="Search prospects" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
        <select className="input" aria-label="Filter by status" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All statuses</option>{STATUSES.map((s) => <option key={s} value={s}>{titleCase(s)}</option>)}
        </select>
        <select className="input" aria-label="Minimum score" value={minScore} onChange={(e) => setMinScore(e.target.value)}>
          <option value="">Any score</option><option value="90">Hot (90+)</option><option value="75">High (75+)</option><option value="60">Medium (60+)</option>
        </select>
        <select className="input col-span-2 sm:col-span-1" aria-label="Sort" value={sort} onChange={(e) => setSort(e.target.value)}>
          <option value="created_at">Newest first</option><option value="lead_score">Highest score</option><option value="updated_at">Recently updated</option><option value="name">Name A–Z</option><option value="company">Company A–Z</option>
        </select>
      </div>

      {bulk.job && <BulkProgress job={bulk.job} onClose={bulk.clear} />}
      {bulk.error && <div className="mb-4"><ErrorState message={bulk.error} /></div>}
      {selected.size > 0 && !bulk.job && (
        <div className="sticky top-16 z-20 mb-4 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-pine bg-pine px-4 py-2 text-white lg:top-4">
          <span className="text-sm">{selected.size} selected</span>
          <div className="flex gap-2">
            <Button size="sm" variant="ghost" className="text-white hover:bg-pine-2" onClick={() => setSelected(new Set())}>Clear</Button>
            <Button size="sm" variant="signal" icon={<Brain className="h-4 w-4" />} onClick={analyzeSelected}>Analyze selected</Button>
          </div>
        </div>
      )}

      {loading && !data ? <Spinner /> : error ? <ErrorState message={error} onRetry={reload} /> : items.length === 0 ? (
        q || status || minScore ? <EmptyState title="No prospects match these filters." action={<Button onClick={() => { setQ(""); setStatus(""); setMinScore(""); }}>Clear filters</Button>} /> :
        <EmptyState title="No prospects yet." body="Import your first prospect list to begin."
          action={<><Button variant="primary" onClick={() => setModal("csv")}>Import CSV</Button><Button onClick={() => setModal("add")}>Add prospect</Button></>} />
      ) : (
        <>
          <p className="mb-2 text-sm text-ink-muted tnum">{data!.total} prospects</p>
          {/* Desktop/tablet table */}
          <div className="panel hidden overflow-x-auto md:block">
            <table className="w-full text-sm">
              <thead className="border-b border-line bg-paper text-left text-ink-muted">
                <tr>
                  <th className="w-10 p-3"><input type="checkbox" className="h-4 w-4" aria-label="Select all" checked={allSel} onChange={() => setSelected(allSel ? new Set() : new Set(items.map((p) => p.id)))} /></th>
                  <th className="p-3 font-medium">Prospect</th><th className="p-3 font-medium">Company</th>
                  <th className="p-3 font-medium">Lead score</th><th className="p-3 font-medium">Status</th><th className="hidden p-3 font-medium xl:table-cell">Added</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {items.map((p) => (
                  <tr key={p.id} className="cursor-pointer hover:bg-paper/70" onClick={() => nav(`/prospects/${p.id}`)}>
                    <td className="p-3" onClick={(e) => e.stopPropagation()}><input type="checkbox" className="h-4 w-4" aria-label={`Select ${p.name}`} checked={selected.has(p.id)} onChange={() => toggle(p.id)} /></td>
                    <td className="p-3"><Link to={`/prospects/${p.id}`} onClick={(e) => e.stopPropagation()} className="font-medium hover:underline">{p.name}</Link>
                      <div className="text-ink-muted">{p.job_title ?? "—"}</div>{p.is_demo && <DemoTag />}</td>
                    <td className="p-3">{p.company ?? "—"}<div className="text-ink-muted">{[p.industry, p.country].filter(Boolean).join(", ")}</div></td>
                    <td className="w-48 p-3"><div className="mb-1.5"><CategoryBadge category={p.category} score={p.lead_score} /></div>{p.lead_score != null && <ScoreBar breakdown={p.score_breakdown} score={p.lead_score} compact />}</td>
                    <td className="p-3"><StatusBadge status={p.status} />{p.takeover_required && <div className="mt-1 text-xs font-semibold text-hot">Takeover needed</div>}</td>
                    <td className="tnum hidden p-3 text-ink-muted xl:table-cell">{fmtDate(p.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {/* Mobile cards */}
          <ul className="space-y-3 md:hidden">
            {items.map((p) => (
              <li key={p.id} className="panel flex gap-3 p-4">
                <input type="checkbox" className="mt-1 h-5 w-5 shrink-0" aria-label={`Select ${p.name}`} checked={selected.has(p.id)} onChange={() => toggle(p.id)} />
                <Link to={`/prospects/${p.id}`} className="min-w-0 flex-1">
                  <div className="flex items-start justify-between gap-2"><p className="truncate font-semibold">{p.name}</p><StatusBadge status={p.status} /></div>
                  <p className="truncate text-sm text-ink-muted">{[p.job_title, p.company].filter(Boolean).join(" at ") || "—"}</p>
                  <div className="mt-2 flex items-center gap-2"><CategoryBadge category={p.category} score={p.lead_score} />{p.is_demo && <DemoTag />}</div>
                  {p.takeover_required && <p className="mt-1 text-xs font-semibold text-hot">Takeover needed</p>}
                </Link>
              </li>
            ))}
          </ul>
        </>
      )}

      {modal === "add" && <ProspectFormModal open onClose={() => setModal(null)} onSaved={(p) => { setModal(null); nav(`/prospects/${p.id}`); }} />}
      <CsvImportModal open={modal === "csv"} onClose={() => setModal(null)} onDone={reload} />
      <SheetsModal open={modal === "sheets"} onClose={() => setModal(null)} onDone={reload} />
      {items.length > 0 && items.some((p) => p.is_demo) && <div className="mt-4"><Notice>Rows tagged “Demo data” are fake and excluded from analytics by default.</Notice></div>}
    </>
  );
}
