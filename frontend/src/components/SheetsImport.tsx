import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../services/api";
import type { IntegrationItem } from "../types";
import { Button, Field, Modal, Notice, Spinner, useToast } from "./ui";

export function SheetsModal({ open, onClose, onDone, mode = "import" }: { open: boolean; onClose: () => void; onDone?: () => void; mode?: "import" | "export" }) {
  const [status, setStatus] = useState<IntegrationItem | null>(null);
  const [files, setFiles] = useState<{ id: string; name: string }[]>([]);
  const [tabs, setTabs] = useState<string[]>([]);
  const [sel, setSel] = useState({ spreadsheet_id: "", sheet: "" });
  const [preview, setPreview] = useState<{ summary: Record<string, number> } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();

  useEffect(() => {
    if (!open) return;
    setError(null); setPreview(null);
    api.get<{ integrations: IntegrationItem[] }>("/api/integrations").then((d) => {
      const s = d.integrations.find((i) => i.provider === "google_sheets") ?? null;
      setStatus(s);
      if (s?.status === "CONNECTED") {
        setSel({ spreadsheet_id: s.config.spreadsheet_id ?? "", sheet: s.config.sheet ?? "" });
        api.get<{ id: string; name: string }[]>("/api/sheets/spreadsheets").then(setFiles).catch((e) => setError(e.message));
      }
    });
  }, [open]);
  useEffect(() => {
    if (!sel.spreadsheet_id || status?.status !== "CONNECTED") return;
    api.get<string[]>(`/api/sheets/${sel.spreadsheet_id}/tabs`).then(setTabs).catch((e) => setError(e.message));
  }, [sel.spreadsheet_id, status]);

  const run = async (dry: boolean) => {
    setBusy(true); setError(null);
    try {
      if (mode === "export") {
        const r = await api.post<{ updated_rows: number }>("/api/sheets/export", { ...sel, dry_run: false });
        toast(`Exported ${r.updated_rows} rows to Google Sheets`); onClose(); return;
      }
      const r = await api.post<{ summary?: Record<string, number>; imported?: number; duplicates?: number }>("/api/sheets/sync", { ...sel, dry_run: dry });
      if (dry) setPreview(r as { summary: Record<string, number> });
      else { toast(`Imported ${r.imported} prospects (${r.duplicates} duplicates skipped)`); onDone?.(); onClose(); }
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };

  const connected = status?.status === "CONNECTED";
  return (
    <Modal open={open} onClose={onClose} title={mode === "import" ? "Import from Google Sheets" : "Export results to Google Sheets"}
      footer={connected ? (<><Button onClick={onClose}>Cancel</Button>
        {mode === "import" && !preview && <Button variant="primary" loading={busy} disabled={!sel.sheet} onClick={() => run(true)}>Preview rows</Button>}
        {mode === "import" && preview && <Button variant="primary" loading={busy} onClick={() => run(false)}>Import {preview.summary.ready} prospects</Button>}
        {mode === "export" && <Button variant="primary" loading={busy} disabled={!sel.sheet} onClick={() => run(false)}>Export to sheet</Button>}</>) : <Button onClick={onClose}>Close</Button>}>
      {!status ? <Spinner /> : !connected ? (
        <Notice tone="warn">
          {status.available ? "Google Sheets is not connected. " : "Google OAuth isn't set up on the server yet. "}
          <Link className="font-medium underline" to="/settings?tab=google" onClick={onClose}>{status.available ? "Connect Google Sheets" : "See setup steps"}</Link>
        </Notice>
      ) : (
        <div className="space-y-4">
          <Field label="Spreadsheet">{(id) => (
            <select id={id} className="input" value={sel.spreadsheet_id} onChange={(e) => { setSel({ spreadsheet_id: e.target.value, sheet: "" }); setPreview(null); }}>
              <option value="">Choose a spreadsheet</option>{files.map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}
            </select>)}</Field>
          <Field label="Sheet" hint={mode === "export" ? "Export writes from cell A1 and overwrites what's there." : "First row must be headers. A Name column is required."}>{(id) => (
            <select id={id} className="input" value={sel.sheet} disabled={!tabs.length} onChange={(e) => { setSel({ ...sel, sheet: e.target.value }); setPreview(null); }}>
              <option value="">Choose a sheet</option>{tabs.map((t) => <option key={t}>{t}</option>)}
            </select>)}</Field>
          {preview && <p className="text-sm">{preview.summary.ready} ready, {preview.summary.duplicate} duplicates, {preview.summary.invalid} invalid. Only ready rows are imported.</p>}
        </div>
      )}
      {error && <p role="alert" className="mt-3 text-sm text-danger">{error}</p>}
    </Modal>
  );
}
