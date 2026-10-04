import { FormEvent, useEffect, useState } from "react";
import { useAuth } from "../hooks/useAuth";
import { api } from "../services/api";
import { Button, Field } from "../components/ui";

export default function Login() {
  const { login, register } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [regOpen, setRegOpen] = useState(true);
  const [f, setF] = useState({ email: "", password: "", name: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.get<{ registration_open: boolean; has_users: boolean }>("/api/auth/config")
      .then((c) => { setRegOpen(c.registration_open); if (!c.has_users) setMode("register"); }).catch(() => {});
  }, []);

  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true); setError(null);
    try { mode === "login" ? await login(f.email, f.password) : await register(f.email, f.password, f.name); }
    catch (err) { setError((err as Error).message); } finally { setBusy(false); }
  };

  return (
    <div className="grid min-h-screen lg:grid-cols-[1.1fr_1fr]">
      <section className="hidden flex-col justify-between bg-pine p-12 text-pine-text lg:flex">
        <p className="font-display text-lg font-semibold text-white">AI Growth Sales Engine</p>
        <div className="max-w-md">
          <h1 className="font-display text-4xl font-semibold leading-tight text-white">Find the right business. Start the right conversation.</h1>
          <p className="mt-4 text-lg leading-relaxed">AI does the research, scoring and drafting. You build the relationship and run the consultation.</p>
          <div className="mt-10 space-y-2" aria-hidden>
            {[["Business fit", 85], ["Marketing opportunity", 92], ["Decision maker", 100], ["Digital opportunity", 66]].map(([l, v]) => (
              <div key={l as string} className="grid grid-cols-[170px_1fr] items-center gap-3 text-sm">
                <span>{l}</span><div className="h-2 rounded-sm bg-pine-2"><div className="h-2 rounded-sm bg-signal" style={{ width: `${v}%` }} /></div>
              </div>))}
          </div>
        </div>
        <p className="text-sm text-pine-dim">Human-in-the-loop. Nothing is sent without you.</p>
      </section>
      <section className="flex items-center justify-center px-5 py-12">
        <form onSubmit={submit} className="w-full max-w-sm space-y-4" noValidate>
          <div className="mb-2">
            <h2 className="text-2xl font-semibold">{mode === "login" ? "Sign in" : "Create your account"}</h2>
            <p className="mt-1 text-ink-muted">{mode === "login" ? "Welcome back." : "The first account becomes the workspace owner."}</p>
          </div>
          {mode === "register" && <Field label="Your name">{(id) => <input id={id} className="input" autoComplete="name" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} />}</Field>}
          <Field label="Email">{(id) => <input id={id} type="email" className="input" autoComplete="email" required value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} />}</Field>
          <Field label="Password" hint={mode === "register" ? "At least 10 characters." : undefined}>{(id) => <input id={id} type="password" className="input" autoComplete={mode === "login" ? "current-password" : "new-password"} required value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} />}</Field>
          {error && <p role="alert" className="text-sm text-danger">{error}</p>}
          <Button variant="primary" type="submit" loading={busy} className="w-full">{mode === "login" ? "Sign in" : "Create account"}</Button>
          {regOpen && (
            <p className="text-center text-sm text-ink-muted">
              {mode === "login" ? "New here? " : "Already have an account? "}
              <button type="button" className="font-medium text-ink underline" onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(null); }}>
                {mode === "login" ? "Create an account" : "Sign in"}
              </button>
            </p>
          )}
        </form>
      </section>
    </div>
  );
}
