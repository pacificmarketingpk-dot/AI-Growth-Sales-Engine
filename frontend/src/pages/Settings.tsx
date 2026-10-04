import { FormEvent, ReactNode, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useApi } from "../hooks/useApi";
import { useAuth } from "../hooks/useAuth";
import { api } from "../services/api";
import type { IntegrationItem, Settings as S } from "../types";
import { SheetsModal } from "../components/SheetsImport";
import { Button, CopyButton, ErrorState, Field, Notice, PageHeader, Panel, Spinner, Tabs, useToast } from "../components/ui";
import { fmtDateTime, titleCase } from "../utils/format";

type Tab = "profile" | "ai" | "google" | "sources" | "outreach" | "notifications" | "security" | "data";
interface Integrations {
  integrations: IntegrationItem[]; email_notifications_available: boolean;
  ai: { default_provider: string; providers: Record<string, { configured: boolean; default_model: string }> };
  prospect_sources: { key: string; label: string; configured: boolean }[];
}

function Status({ status }: { status: string }) {
  const ok = status === "CONNECTED";
  return <span className={`rounded px-2 py-0.5 text-xs font-semibold ${ok ? "bg-ok-soft text-ok" : status === "EXPIRED" ? "bg-signal-soft text-high" : "bg-low-soft text-ink"}`}>{ok ? "Connected" : status === "EXPIRED" ? "Expired, reconnect" : "Not connected"}</span>;
}

function Row({ title, note, right }: { title: string; note?: ReactNode; right: ReactNode }) {
  return (
    <div className="flex flex-col gap-3 py-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0"><p className="font-medium">{title}</p>{note && <div className="mt-0.5 text-sm text-ink-muted">{note}</div>}</div>
      <div className="flex shrink-0 flex-wrap items-center gap-2">{right}</div>
    </div>
  );
}

export default function Settings() {
  const [params, setParams] = useSearchParams();
  const [tab, setTab] = useState<Tab>((params.get("tab") as Tab) || "profile");
  const { data: s, error, loading, reload, setData } = useApi<S>("/api/settings");
  const integ = useApi<Integrations>("/api/integrations");
  const audit = useApi<{ id: number; action: string; entity_type: string; entity_id: number | null; created_at: string }[]>(tab === "data" ? "/api/audit?limit=100" : null);
  const [form, setForm] = useState<Partial<S>>({});
  const [busy, setBusy] = useState(false);
  const [sheets, setSheets] = useState<"import" | "export" | null>(null);
  const [pw, setPw] = useState({ current_password: "", new_password: "" });
  const [token, setToken] = useState<string | null>(null);
  const toast = useToast();
  const { setBrand } = useAuth();

  useEffect(() => { if (s) setForm(s); }, [s]);
  useEffect(() => {
    const c = params.get("connected"), e = params.get("google_error");
    if (c) toast(`${c === "google_calendar" ? "Google Calendar" : "Google Sheets"} connected`);
    if (e) toast(e === "access_denied" ? "Google access was not granted." : "Google connection failed. Please try again.", "error");
    if (c || e) setParams({ tab: "google" }, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (loading && !s) return <Spinner />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (!s) return null;

  const save = async (e?: FormEvent) => {
    e?.preventDefault(); setBusy(true);
    try { const n = await api.put<S>("/api/settings", form); setData(n); setBrand(n.brand_name); toast("Settings saved"); }
    catch (err) { toast((err as Error).message, "error"); } finally { setBusy(false); }
  };
  const set = (k: keyof S) => (e: { target: { value: string; type?: string; checked?: boolean } }) =>
    setForm({ ...form, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.type === "number" ? Number(e.target.value) : e.target.value });
  const input = (k: keyof S, label: string, hint?: string, type = "text") => (
    <Field label={label} hint={hint}>{(id) => <input id={id} type={type} className="input" value={String(form[k] ?? "")} onChange={set(k)} />}</Field>
  );
  const saveBar = <div className="mt-5"><Button variant="primary" type="submit" loading={busy}>Save changes</Button></div>;

  const connect = async (provider: string) => {
    try { const r = await api.post<{ auth_url: string }>(`/api/integrations/${provider}/connect`); window.location.href = r.auth_url; }
    catch (e) { toast((e as Error).message, "error"); }
  };
  const disconnect = async (provider: string) => {
    if (!confirm("Disconnect this integration? Stored tokens will be deleted.")) return;
    await api.del(`/api/integrations/${provider}`); integ.reload(); toast("Disconnected");
  };
  const g = (p: string) => integ.data?.integrations.find((i) => i.provider === p);
  const ai = integ.data?.ai;

  return (
    <>
      <PageHeader title="Settings" />
      <Tabs<Tab> value={tab} onChange={(t) => { setTab(t); setParams({ tab: t }, { replace: true }); }} tabs={[
        { id: "profile", label: "Profile" }, { id: "ai", label: "AI" }, { id: "google", label: "Google" }, { id: "sources", label: "Prospect sources" },
        { id: "outreach", label: "Outreach & meetings" }, { id: "notifications", label: "Notifications" }, { id: "security", label: "Security" }, { id: "data", label: "Data & audit" },
      ]} />

      <div className="max-w-3xl">
        {tab === "profile" && (
          <Panel title="Profile"><form onSubmit={save} className="grid gap-4 sm:grid-cols-2">
            {input("name", "Name")}{input("business", "Business", "Your company or practice name")}
            {input("role", "Role", "Used to frame AI analysis and messages")}{input("timezone", "Timezone", "IANA name, e.g. Asia/Karachi or America/New_York")}
            <div className="sm:col-span-2">{input("brand_name", "Application name", "Shown in the sidebar and browser tab")}</div>
            <div className="sm:col-span-2">{saveBar}</div>
          </form></Panel>
        )}

        {tab === "ai" && (
          <Panel title="AI provider"><form onSubmit={save} className="space-y-4">
            {ai && (
              <div className="divide-y divide-line rounded-md border border-line px-4">
                {Object.entries(ai.providers).map(([k, v]) => (
                  <Row key={k} title={k === "openai" ? "OpenAI" : "Anthropic (Claude)"} note={`Default model: ${v.default_model}`}
                    right={<span className={`rounded px-2 py-0.5 text-xs font-semibold ${v.configured ? "bg-ok-soft text-ok" : "bg-low-soft text-ink"}`}>{v.configured ? "API key configured" : "No API key"}</span>} />))}
              </div>
            )}
            <Notice>API keys live only in the server's environment variables (OPENAI_API_KEY, ANTHROPIC_API_KEY). They are never sent to the browser.</Notice>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Provider">{(id) => (
                <select id={id} className="input" value={form.ai_provider ?? ""} onChange={set("ai_provider")}>
                  <option value="">Server default ({ai?.default_provider ?? "…"})</option><option value="anthropic">Anthropic</option><option value="openai">OpenAI</option>
                </select>)}</Field>
              {input("ai_model", "Model", "Leave blank to use the provider's default model")}
            </div>
            {saveBar}
          </form></Panel>
        )}

        {tab === "google" && (
          <Panel title="Google">
            {g("google_calendar") && !g("google_calendar")!.available && (
              <Notice tone="warn"><p className="font-medium">Google OAuth isn't set up on the server.</p>
                <p className="mt-1">Create an OAuth client in Google Cloud Console, add <code>{"<BACKEND_URL>/api/integrations/google/callback"}</code> as a redirect URI, then set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env and restart. See README → Google OAuth setup.</p></Notice>
            )}
            <div className="divide-y divide-line">
              {(["google_calendar", "google_sheets"] as const).map((p) => {
                const i = g(p);
                if (!i) return null;
                const on = i.status === "CONNECTED";
                return (
                  <Row key={p} title={i.label} note={<><Status status={i.status} />{p === "google_sheets" && on && i.config.sheet && <span className="ml-2">Last used: {i.config.sheet}</span>}</>}
                    right={on ? (<>{p === "google_sheets" && <><Button size="sm" onClick={() => setSheets("import")}>Sync prospects</Button><Button size="sm" onClick={() => setSheets("export")}>Export results</Button></>}
                      <Button size="sm" variant="danger" onClick={() => disconnect(p)}>Disconnect</Button></>)
                      : <Button size="sm" variant="primary" disabled={!i.available} onClick={() => connect(p)}>{i.status === "EXPIRED" ? "Reconnect" : `Connect ${i.label}`}</Button>} />
                );
              })}
            </div>
            <p className="mt-2 text-sm text-ink-muted">You sign in on Google's own page. This app never sees your Google password, and tokens are stored encrypted.</p>
          </Panel>
        )}

        {tab === "sources" && (
          <Panel title="Prospect sources and future integrations">
            <p className="mb-2 text-ink-muted">Only official APIs and licensed providers are supported. Nothing here scrapes LinkedIn or automates your account.</p>
            <div className="divide-y divide-line">
              {(integ.data?.prospect_sources ?? []).map((src) => <Row key={src.key} title={src.label} right={<Status status={src.configured ? "CONNECTED" : "NOT_CONNECTED"} />} />)}
              {(integ.data?.integrations ?? []).filter((i) => !i.provider.startsWith("google")).map((i) => (
                <Row key={i.provider} title={i.label} note={<><Status status={i.status} /> <span className="ml-1">{i.note}</span></>}
                  right={<Button size="sm" onClick={() => connect(i.provider)}>Connect</Button>} />
              ))}
            </div>
            <p className="mt-2 text-sm text-ink-muted">Until a source is connected, add prospects by CSV, Google Sheets or manually.</p>
          </Panel>
        )}

        {tab === "outreach" && (
          <Panel title="Outreach and meetings"><form onSubmit={save} className="grid gap-4 sm:grid-cols-2">
            <Field label="Message tone">{(id) => (
              <select id={id} className="input" value={form.message_tone ?? ""} onChange={set("message_tone")}>
                {["professional and warm", "concise and direct", "friendly and casual", "formal"].map((t) => <option key={t} value={t}>{titleCase(t)}</option>)}
              </select>)}</Field>
            <div />
            {input("followup_1_days", "Days before follow-up 1", undefined, "number")}{input("followup_2_days", "Days before follow-up 2", undefined, "number")}
            {input("meeting_title", "Default meeting type")}{input("meeting_duration", "Default meeting length (minutes)", undefined, "number")}
            <div className="sm:col-span-2">{saveBar}</div>
          </form></Panel>
        )}

        {tab === "notifications" && (
          <Panel title="Email notifications"><form onSubmit={save} className="space-y-4">
            {!integ.data?.email_notifications_available && <Notice tone="warn">Email sending isn't configured on the server (SMTP_HOST, SMTP_FROM). Notifications will not be sent until it is.</Notice>}
            <label className="flex min-h-[44px] items-center gap-3"><input type="checkbox" className="h-5 w-5" checked={!!form.email_notifications} onChange={set("email_notifications")} />Email me when a lead becomes qualified</label>
            {input("notification_email", "Send notifications to", undefined, "email")}
            <p className="text-sm text-ink-muted">Notifications go only to you. The app never emails prospects automatically.</p>
            {saveBar}
          </form></Panel>
        )}

        {tab === "security" && (
          <div className="space-y-5">
            <Panel title="Password"><form className="grid gap-4 sm:grid-cols-2" onSubmit={async (e) => {
              e.preventDefault();
              try { await api.post("/api/auth/change-password", pw); setPw({ current_password: "", new_password: "" }); toast("Password changed. Other sessions were signed out."); }
              catch (err) { toast((err as Error).message, "error"); }
            }}>
              <Field label="Current password">{(id) => <input id={id} type="password" autoComplete="current-password" className="input" value={pw.current_password} onChange={(e) => setPw({ ...pw, current_password: e.target.value })} />}</Field>
              <Field label="New password" hint="At least 10 characters">{(id) => <input id={id} type="password" autoComplete="new-password" className="input" value={pw.new_password} onChange={(e) => setPw({ ...pw, new_password: e.target.value })} />}</Field>
              <div className="sm:col-span-2"><Button variant="primary" type="submit">Change password</Button></div>
            </form></Panel>
            <Panel title="Sessions"><Row title="Sign out everywhere" note="Ends every session and API token, except this one." right={
              <Button onClick={async () => { await api.post("/api/auth/revoke-sessions"); setToken(null); toast("All other sessions signed out"); }}>Sign out other sessions</Button>} /></Panel>
            <Panel title="API access">
              <p className="text-sm text-ink-muted">A bearer token for scripts calling this app's API. Treat it like a password. It stops working when you sign out other sessions.</p>
              {token ? <div className="mt-3 space-y-2"><code className="block break-all rounded bg-paper p-3 text-xs">{token}</code><CopyButton text={token} label="Copy token" /></div>
                : <div className="mt-3"><Button onClick={async () => setToken((await api.post<{ token: string }>("/api/auth/api-token")).token)}>Create API token</Button></div>}
            </Panel>
          </div>
        )}

        {tab === "data" && (
          <div className="space-y-5">
            <Panel title="Demo mode">
              <p className="text-ink-muted">Adds five clearly-labelled fake prospects (names start with DEMO) so you can explore. Demo records are tagged everywhere and excluded from analytics by default. AI analysis of demo prospects uses canned demo output and costs nothing.</p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Button onClick={async () => { const r = await api.post<{ created: number }>("/api/demo/seed"); toast(r.created ? "Demo data added" : "Demo data already exists"); }}>Add demo data</Button>
                <Button variant="danger" onClick={async () => { if (!confirm("Delete all demo records?")) return; const r = await api.del<{ deleted: number }>("/api/demo"); toast(`Deleted ${r.deleted} demo prospects`); }}>Remove demo data</Button>
              </div>
            </Panel>
            <Panel title="Export"><a href={api.url("/api/export/csv")}><Button>Download prospects CSV</Button></a></Panel>
            <Panel title="Audit log">
              {!audit.data ? <Spinner /> : (
                <div className="overflow-x-auto"><table className="w-full min-w-[480px] text-sm">
                  <thead className="text-left text-ink-muted"><tr><th className="py-2 font-medium">When</th><th className="py-2 font-medium">Action</th><th className="py-2 font-medium">Entity</th></tr></thead>
                  <tbody className="divide-y divide-line">{audit.data.map((r) => (
                    <tr key={r.id}><td className="tnum py-2 pr-4 text-ink-muted">{fmtDateTime(r.created_at)}</td><td className="py-2 pr-4">{r.action}</td><td className="py-2">{r.entity_type}{r.entity_id ? ` #${r.entity_id}` : ""}</td></tr>))}</tbody>
                </table></div>
              )}
            </Panel>
          </div>
        )}
      </div>
      <SheetsModal open={!!sheets} mode={sheets ?? "import"} onClose={() => setSheets(null)} />
    </>
  );
}
