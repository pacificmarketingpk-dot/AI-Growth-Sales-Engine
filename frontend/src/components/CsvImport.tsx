import { useRef, useState } from "react";
import { FileUp } from "lucide-react";
import { api } from "../services/api";
import { Button, Modal, Notice } from "./ui";

interface Row { row: number; data: Record<string, string>; errors: string[]; duplicate: string | null; status: string }
interface Preview { rows: Row[]; summary: { ready: number; duplicate: number; invalid: number } }
interface Result { imported: number; duplicates: number; invalid: number; skipped: number }

/** Upload → validate → preview → detect duplicates → confirm → import */
export function CsvImportModal({ open, onClose, onDone }: { open: boolean; onClose: () => void; onDone: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [skip, setSkip] = useState<Set<number>>(new Set());
  const [result, setResult] = useState<Result | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const input = useRef<HTMLInputElement>(null);

  const reset = () => { setFile(null); setPreview(null); setResult(null); setSkip(new Set()); setError(null); };
  const close = () => { reset(); onClose(); };

  const send = async (dry: boolean, f = file) => {
    if (!f) return;
    const fd = new FormData();
    fd.append("file", f); fd.append("dry_run", String(dry)); fd.append("skip_rows", JSON.stringify([...skip]));
    setBusy(true); setError(null);
    try {
      if (dry) setPreview(await api.form<Preview>("/api/import/csv", fd));
      else { setResult(await api.form<Result>("/api/import/csv", fd)); onDone(); }
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };

  const toggle = (n: number) => setSkip((s) => { const x = new Set(s); x.has(n) ? x.delete(n) : x.add(n); return x; });
  const willImport = preview ? preview.rows.filter((r) => r.status === "ready" && !skip.has(r.row)).length : 0;

  return (
    <Modal open={open} onClose={close} title="Import prospects from CSV" wide
      footer={result ? <Button variant="primary" onClick={close}>Done</Button> : preview ? (
        <><Button onClick={reset}>Choose another file</Button>
          <Button variant="primary" loading={busy} disabled={!willImport} onClick={() => send(false)}>Import {willImport} prospects</Button></>
      ) : <Button onClick={close}>Cancel</Button>}>
      {result ? (
        <div>
          <p className="mb-4 font-display text-lg font-semibold">Import finished</p>
          <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {([["Imported", result.imported], ["Duplicates", result.duplicates], ["Invalid", result.invalid], ["Skipped", result.skipped]] as const).map(([k, v]) => (
              <div key={k} className="rounded-md border border-line p-3"><dt className="text-sm text-ink-muted">{k}</dt><dd className="tnum font-display text-2xl font-semibold">{v}</dd></div>
            ))}
          </dl>
        </div>
      ) : !preview ? (
        <div>
          <p className="mb-3 text-ink-muted">Columns we recognise: Name (required), LinkedIn URL, Company, Job Title, Industry, Country, Company Size, Website, Email, Notes. Up to 5 MB.</p>
          <button onClick={() => input.current?.click()} className="flex w-full flex-col items-center gap-2 rounded-lg border-2 border-dashed border-line px-4 py-10 hover:border-pine-3">
            <FileUp className="h-8 w-8 text-pine-3" aria-hidden />
            <span className="font-medium">{busy ? "Checking file…" : "Choose a CSV file"}</span>
          </button>
          <input ref={input} type="file" accept=".csv,text/csv" className="sr-only" aria-label="CSV file"
            onChange={(e) => { const f = e.target.files?.[0] ?? null; setFile(f); if (f) send(true, f); }} />
          {error && <p role="alert" className="mt-3 text-sm text-danger">{error}</p>}
        </div>
      ) : (
        <div>
          <div className="mb-3 flex flex-wrap gap-2 text-sm">
            <span className="rounded bg-ok-soft px-2 py-1 text-ok">{preview.summary.ready} ready</span>
            <span className="rounded bg-signal-soft px-2 py-1 text-high">{preview.summary.duplicate} duplicates</span>
            <span className="rounded bg-danger-soft px-2 py-1 text-danger">{preview.summary.invalid} invalid</span>
          </div>
          <Notice>Duplicates and invalid rows are never imported. Untick a ready row to skip it.</Notice>
          <div className="mt-3 max-h-[45vh] overflow-auto rounded-md border border-line">
            <table className="w-full min-w-[560px] text-sm">
              <thead className="sticky top-0 bg-paper text-left text-ink-muted"><tr>
                <th className="p-2">Import</th><th className="p-2">Row</th><th className="p-2">Name</th><th className="p-2">Company</th><th className="p-2">Result</th></tr></thead>
              <tbody>{preview.rows.map((r) => (
                <tr key={r.row} className="border-t border-line">
                  <td className="p-2"><input type="checkbox" className="h-5 w-5" aria-label={`Import row ${r.row}`} disabled={r.status !== "ready"}
                    checked={r.status === "ready" && !skip.has(r.row)} onChange={() => toggle(r.row)} /></td>
                  <td className="tnum p-2 text-ink-muted">{r.row}</td>
                  <td className="p-2">{r.data.name || "—"}</td><td className="p-2">{r.data.company || "—"}</td>
                  <td className="p-2">{r.status === "ready" ? <span className="text-ok">Ready</span>
                    : r.status === "duplicate" ? <span className="text-high">Duplicate ({r.duplicate?.replace("_", " ")})</span>
                    : <span className="text-danger">{r.errors.join("; ")}</span>}</td>
                </tr>))}</tbody>
            </table>
          </div>
          {error && <p role="alert" className="mt-3 text-sm text-danger">{error}</p>}
        </div>
      )}
    </Modal>
  );
}
