import { useState } from "react";
import { Pencil, RefreshCw } from "lucide-react";
import { api } from "../services/api";
import type { Outreach } from "../types";
import { fmtDate, OUTREACH_LABELS } from "../utils/format";
import { Button, CopyButton, useToast } from "./ui";

export function MessageCard({ item, onChange, linkedinConnected = false }: { item: Outreach; onChange: (o: Outreach) => void; linkedinConnected?: boolean }) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(item.message);
  const [busy, setBusy] = useState<"save" | "regen" | null>(null);
  const toast = useToast();

  const save = async () => {
    setBusy("save");
    try { const o = await api.put<Outreach>(`/api/outreach/${item.id}`, { message: text }); onChange(o); setEditing(false); toast("Message saved"); }
    catch (e) { toast((e as Error).message, "error"); } finally { setBusy(null); }
  };
  const regen = async () => {
    if (item.edited && !confirm("Replace your edited version with a new AI draft?")) return;
    setBusy("regen");
    try { const o = await api.post<Outreach>(`/api/outreach/${item.id}/regenerate`); onChange(o); setText(o.message); toast("New draft ready"); }
    catch (e) { toast((e as Error).message, "error"); } finally { setBusy(null); }
  };

  return (
    <article className="rounded-lg border border-line bg-white">
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-4 py-2.5">
        <h3 className="font-sans text-sm font-semibold">{OUTREACH_LABELS[item.kind] ?? item.kind}</h3>
        <p className="text-xs text-ink-muted">
          {item.contacted_at ? `Sent via ${item.channel} on ${fmtDate(item.contacted_at)}` : item.edited ? "Edited by you" : "AI draft"}
          {item.follow_up_due && !item.contacted_at ? "" : item.follow_up_due ? ` · next follow-up ${fmtDate(item.follow_up_due)}` : ""}
        </p>
      </header>
      <div className="p-4">
        {editing ? (
          <>
            <label className="sr-only" htmlFor={`msg-${item.id}`}>Edit message</label>
            <textarea id={`msg-${item.id}`} className="input min-h-[140px]" value={text} onChange={(e) => setText(e.target.value)} />
            <p className="mt-1 text-xs text-ink-muted tnum">{text.length} characters{item.kind === "connection_message" && text.length > 300 ? " — LinkedIn connection notes are limited to 300" : ""}</p>
          </>
        ) : <p className="whitespace-pre-wrap leading-relaxed">{item.message}</p>}
      </div>
      <footer className="flex flex-wrap gap-2 border-t border-line px-4 py-3">
        {editing ? (
          <><Button size="sm" variant="primary" loading={busy === "save"} onClick={save}>Save message</Button>
            <Button size="sm" onClick={() => { setEditing(false); setText(item.message); }}>Cancel</Button></>
        ) : (
          <><CopyButton text={item.message} />
            <Button size="sm" icon={<Pencil className="h-4 w-4" />} onClick={() => setEditing(true)}>Edit</Button>
            <Button size="sm" icon={<RefreshCw className="h-4 w-4" />} loading={busy === "regen"} onClick={regen}>Regenerate</Button>
            {!linkedinConnected && <span className="self-center text-xs text-ink-muted">LinkedIn integration not connected. Copy and send it yourself.</span>}</>
        )}
      </footer>
    </article>
  );
}
