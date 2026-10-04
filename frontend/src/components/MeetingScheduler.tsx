import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../services/api";
import type { IntegrationItem, Meeting, Prospect, Settings } from "../types";
import { Button, Field, Modal, Notice, useToast } from "./ui";

function localInput(d: Date) {
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`;
}

export function MeetingScheduler({ open, onClose, prospect, onBooked }: {
  open: boolean; onClose: () => void; prospect: Pick<Prospect, "id" | "name" | "company" | "email"> | null; onBooked?: (m: Meeting) => void;
}) {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [calConnected, setCalConnected] = useState<boolean | null>(null);
  const [slots, setSlots] = useState<string[]>([]);
  const tomorrow = new Date(); tomorrow.setDate(tomorrow.getDate() + 1); tomorrow.setHours(10, 0, 0, 0);
  const [form, setForm] = useState({ meeting_type: "", start: localInput(tomorrow), duration: 30, notes: "", invite: false });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();

  useEffect(() => {
    if (!open) return;
    setError(null);
    api.get<Settings>("/api/settings").then((s) => { setSettings(s); setForm((f) => ({ ...f, meeting_type: s.meeting_title, duration: s.meeting_duration })); });
    api.get<{ integrations: IntegrationItem[] }>("/api/integrations").then((d) => {
      const c = d.integrations.find((i) => i.provider === "google_calendar")?.status === "CONNECTED";
      setCalConnected(c);
      if (c) api.get<{ free_slots: string[] }>("/api/calendar/events").then((e) => setSlots(e.free_slots.slice(0, 8))).catch(() => {});
    });
  }, [open]);

  const submit = async (e: FormEvent, sync: boolean) => {
    e.preventDefault();
    if (!prospect) return;
    setBusy(true); setError(null);
    try {
      const m = await api.post<Meeting>("/api/meetings", {
        prospect_id: prospect.id, meeting_type: form.meeting_type, start_at: new Date(form.start).toISOString(),
        duration_minutes: Number(form.duration), notes: form.notes || null, invite_prospect: form.invite, sync_to_google: sync,
      });
      toast(sync ? "Meeting booked in Google Calendar" : "Meeting saved");
      onBooked?.(m); onClose();
    } catch (err) { setError((err as Error).message); } finally { setBusy(false); }
  };

  return (
    <Modal open={open} onClose={onClose} title="Book consultation"
      footer={calConnected ? (
        <><Button onClick={onClose}>Cancel</Button><Button variant="primary" loading={busy} onClick={(e) => submit(e, true)}>Book in Google Calendar</Button></>
      ) : (
        <><Button onClick={onClose}>Cancel</Button><Button variant="primary" loading={busy} onClick={(e) => submit(e, false)}>Save meeting without calendar</Button></>
      )}>
      {prospect && (
        <form className="space-y-4" onSubmit={(e) => submit(e, !!calConnected)}>
          <div className="rounded-md bg-paper p-3 text-sm"><p className="font-semibold">{prospect.name}</p><p className="text-ink-muted">{prospect.company ?? "No company"}</p></div>
          {calConnected === false && (
            <Notice tone="warn">Google Calendar is not connected, so no calendar event will be created. <Link className="font-medium underline" to="/settings?tab=google">Connect Google Calendar</Link></Notice>
          )}
          <Field label="Meeting type">{(id) => <input id={id} className="input" value={form.meeting_type} onChange={(e) => setForm({ ...form, meeting_type: e.target.value })} />}</Field>
          {slots.length > 0 && (
            <div>
              <p className="label">Open times from your calendar</p>
              <div className="flex flex-wrap gap-2">{slots.map((s) => (
                <button type="button" key={s} onClick={() => setForm({ ...form, start: localInput(new Date(s)) })}
                  className={`min-h-[40px] rounded-md border px-3 text-sm ${localInput(new Date(s)) === form.start ? "border-pine bg-pine text-white" : "border-line hover:border-pine-3"}`}>
                  {new Date(s).toLocaleString(undefined, { weekday: "short", hour: "numeric", minute: "2-digit" })}
                </button>))}
              </div>
            </div>
          )}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-[1fr_140px]">
            <Field label="Date and time" hint={`Your timezone setting: ${settings?.timezone ?? "UTC"}`}>{(id) => <input id={id} type="datetime-local" className="input" value={form.start} onChange={(e) => setForm({ ...form, start: e.target.value })} />}</Field>
            <Field label="Minutes">{(id) => <input id={id} type="number" min={10} max={240} className="input" value={form.duration} onChange={(e) => setForm({ ...form, duration: Number(e.target.value) })} />}</Field>
          </div>
          <Field label="Notes">{(id) => <textarea id={id} className="input min-h-[80px]" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />}</Field>
          {calConnected && prospect.email && (
            <label className="flex min-h-[44px] items-center gap-3 text-sm">
              <input type="checkbox" className="h-5 w-5" checked={form.invite} onChange={(e) => setForm({ ...form, invite: e.target.checked })} />
              Add {prospect.email} as a guest (Google won't email them automatically)
            </label>
          )}
          {error && <p role="alert" className="text-sm text-danger">{error}</p>}
        </form>
      )}
    </Modal>
  );
}
