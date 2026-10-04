import { FormEvent, useState } from "react";
import { api } from "../services/api";
import type { Conversation, Prospect } from "../types";
import { Button, Field, Modal, useToast } from "./ui";

export function ConversationFormModal({ open, onClose, prospects, defaultProspectId, onSaved }: {
  open: boolean; onClose: () => void; prospects: Pick<Prospect, "id" | "name" | "company">[]; defaultProspectId?: number; onSaved: (c: Conversation) => void;
}) {
  const [pid, setPid] = useState<number | "">(defaultProspectId ?? "");
  const [channel, setChannel] = useState("LinkedIn");
  const [text, setText] = useState("");
  const [analyze, setAnalyze] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!pid || !text.trim()) { setError("Choose a prospect and paste the conversation."); return; }
    setBusy(true); setError(null);
    try {
      let c = await api.post<Conversation>("/api/conversations", { prospect_id: pid, channel, raw_text: text });
      if (analyze) {
        try { c = await api.post<Conversation>(`/api/conversations/${c.id}/analyze`); }
        catch (err) { toast(`Saved. ${(err as Error).message}`, "error"); }
      }
      toast("Conversation saved"); setText(""); onSaved(c);
    } catch (err) { setError((err as Error).message); } finally { setBusy(false); }
  };

  return (
    <Modal open={open} onClose={onClose} title="Add conversation" wide
      footer={<><Button onClick={onClose}>Cancel</Button><Button variant="primary" type="submit" form="conv-form" loading={busy}>{analyze ? "Save and analyze" : "Save conversation"}</Button></>}>
      <form id="conv-form" onSubmit={submit} className="space-y-4">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Field label="Prospect">{(id) => (
            <select id={id} className="input" value={pid} onChange={(e) => setPid(Number(e.target.value) || "")}>
              <option value="">Choose a prospect</option>
              {prospects.map((p) => <option key={p.id} value={p.id}>{p.name}{p.company ? ` — ${p.company}` : ""}</option>)}
            </select>)}</Field>
          <Field label="Channel">{(id) => (
            <select id={id} className="input" value={channel} onChange={(e) => setChannel(e.target.value)}>
              <option>LinkedIn</option><option>Email</option><option>Other</option>
            </select>)}</Field>
        </div>
        <Field label="Conversation" hint="One message per line, starting with who said it. Example — Me: Thanks for connecting.  Sam: We're struggling with Meta leads.">
          {(id) => <textarea id={id} className="input min-h-[200px] font-sans" value={text} onChange={(e) => setText(e.target.value)}
            placeholder={"Me: Thanks for connecting, Sam.\nSam: We're currently struggling to generate qualified leads through Meta."} />}
        </Field>
        <label className="flex min-h-[44px] items-center gap-3 text-sm">
          <input type="checkbox" className="h-5 w-5" checked={analyze} onChange={(e) => setAnalyze(e.target.checked)} /> Analyze with AI after saving
        </label>
        {error && <p role="alert" className="text-sm text-danger">{error}</p>}
      </form>
    </Modal>
  );
}
