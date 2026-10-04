import { ButtonHTMLAttributes, createContext, ReactNode, useCallback, useContext, useEffect, useId, useRef, useState } from "react";
import { AlertTriangle, Check, Copy, Loader2, X } from "lucide-react";
import type { Category } from "../types";
import { titleCase } from "../utils/format";

/* ---------- Button ---------- */
type Variant = "primary" | "secondary" | "ghost" | "danger" | "signal";
const VARIANTS: Record<Variant, string> = {
  primary: "bg-pine text-white hover:bg-pine-2 border border-pine",
  signal: "bg-signal text-pine hover:brightness-95 border border-signal font-semibold",
  secondary: "bg-white text-ink border border-line hover:border-pine-3 hover:bg-paper",
  ghost: "bg-transparent text-ink hover:bg-paper border border-transparent",
  danger: "bg-white text-danger border border-danger/40 hover:bg-danger-soft",
};
export function Button({ variant = "secondary", loading, icon, children, className = "", size = "md", ...rest }:
  ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; loading?: boolean; icon?: ReactNode; size?: "sm" | "md" }) {
  const sz = size === "sm" ? "min-h-[36px] px-3 text-sm" : "min-h-[44px] px-4 text-[15px]";
  return (
    <button {...rest} disabled={rest.disabled || loading}
      className={`inline-flex items-center justify-center gap-2 rounded-md font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${sz} ${VARIANTS[variant]} ${className}`}>
      {loading ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : icon}
      {children}
    </button>
  );
}

/* ---------- Badges: never colour-only, always text ---------- */
const CAT: Record<Category, { cls: string; mark: string }> = {
  HOT: { cls: "bg-hot-soft text-hot border-hot/30", mark: "▲▲" },
  HIGH: { cls: "bg-high-soft text-high border-high/30", mark: "▲" },
  MEDIUM: { cls: "bg-medium-soft text-medium border-medium/30", mark: "■" },
  LOW: { cls: "bg-low-soft text-low border-low/30", mark: "▽" },
};
export function CategoryBadge({ category, score }: { category: Category | null; score?: number | null }) {
  if (!category) return <span className="text-sm text-ink-muted">Not analyzed</span>;
  const c = CAT[category];
  return (
    <span className={`inline-flex items-center gap-1.5 rounded border px-2 py-0.5 text-xs font-semibold ${c.cls}`}>
      <span aria-hidden className="text-[9px]">{c.mark}</span>
      {score != null && <span className="tnum">{score}</span>}
      <span>{titleCase(category)}</span>
    </span>
  );
}

const STATUS_TONE: Record<string, string> = {
  NEW: "bg-low-soft text-ink", ANALYZING: "bg-signal-soft text-high", ANALYZED: "bg-medium-soft text-medium",
  REVIEW: "bg-medium-soft text-medium", APPROVED: "bg-medium-soft text-medium", CONTACTED: "bg-paper text-ink border-line",
  REPLIED: "bg-signal-soft text-high", QUALIFIED: "bg-ok-soft text-ok", PROPOSAL: "bg-ok-soft text-ok",
  WON: "bg-ok text-white", LOST: "bg-low-soft text-low line-through",
};
export function StatusBadge({ status }: { status: string }) {
  return <span className={`inline-flex rounded border border-transparent px-2 py-0.5 text-xs font-medium ${STATUS_TONE[status] ?? "bg-paper"}`}>{titleCase(status)}</span>;
}

const INTENT_TONE: Record<string, string> = {
  "QUALIFIED": "bg-ok-soft text-ok", "HIGH INTENT": "bg-hot-soft text-hot", "INTERESTED": "bg-signal-soft text-high",
  "NEEDS FOLLOW-UP": "bg-medium-soft text-medium", "NEUTRAL": "bg-low-soft text-ink",
  "NOT INTERESTED": "bg-low-soft text-low", "NOT RELEVANT": "bg-low-soft text-low",
};
export function IntentBadge({ intent }: { intent: string | null }) {
  if (!intent) return <span className="text-sm text-ink-muted">No intent yet</span>;
  return <span className={`inline-flex rounded px-2 py-0.5 text-xs font-semibold ${INTENT_TONE[intent] ?? "bg-paper"}`}>Intent: {titleCase(intent)}</span>;
}

export function DemoTag() {
  return <span className="rounded border border-dashed border-signal bg-signal-soft px-1.5 py-0.5 text-2xs font-semibold text-high">Demo data</span>;
}

/* ---------- Layout bits ---------- */
export function PageHeader({ title, description, actions }: { title: string; description?: string; actions?: ReactNode }) {
  return (
    <header className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div className="min-w-0">
        <h1 className="text-2xl font-semibold sm:text-[28px]">{title}</h1>
        {description && <p className="mt-1 max-w-2xl text-ink-muted">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </header>
  );
}

export function Panel({ title, action, children, className = "" }: { title?: string; action?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`panel ${className}`}>
      {(title || action) && (
        <div className="flex items-center justify-between gap-3 border-b border-line px-4 py-3 sm:px-5">
          {title && <h2 className="text-base font-semibold">{title}</h2>}
          {action}
        </div>
      )}
      <div className="p-4 sm:p-5">{children}</div>
    </section>
  );
}

export function EmptyState({ title, body, action, icon }: { title: string; body?: string; action?: ReactNode; icon?: ReactNode }) {
  return (
    <div className="flex flex-col items-center rounded-lg border border-dashed border-line bg-white px-6 py-12 text-center">
      {icon && <div className="mb-3 text-pine-3" aria-hidden>{icon}</div>}
      <p className="font-display text-lg font-semibold">{title}</p>
      {body && <p className="mt-1 max-w-md text-ink-muted">{body}</p>}
      {action && <div className="mt-5 flex flex-wrap justify-center gap-2">{action}</div>}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex items-start gap-3 rounded-lg border border-danger/30 bg-danger-soft p-4 text-danger">
      <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" aria-hidden />
      <div className="flex-1"><p className="font-medium">{message}</p></div>
      {onRetry && <Button size="sm" onClick={onRetry}>Try again</Button>}
    </div>
  );
}

export function Notice({ children, tone = "info" }: { children: ReactNode; tone?: "info" | "warn" }) {
  const cls = tone === "warn" ? "border-signal/40 bg-signal-soft text-ink" : "border-medium/30 bg-medium-soft text-ink";
  return <div className={`rounded-lg border p-3 text-sm ${cls}`}>{children}</div>;
}

export function Spinner({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-12 text-ink-muted" role="status">
      <Loader2 className="h-5 w-5 animate-spin" aria-hidden /> <span>{label}…</span>
    </div>
  );
}

/* ---------- Form field ---------- */
export function Field({ label, hint, children, error }: { label: string; hint?: string; error?: string; children: (id: string) => ReactNode }) {
  const id = useId();
  return (
    <div>
      <label htmlFor={id} className="label">{label}</label>
      {children(id)}
      {hint && !error && <p className="mt-1 text-xs text-ink-muted">{hint}</p>}
      {error && <p className="mt-1 text-xs text-danger">{error}</p>}
    </div>
  );
}

/* ---------- Modal (focus-trapped dialog; full-screen sheet on mobile) ---------- */
export function Modal({ open, onClose, title, children, footer, wide }: {
  open: boolean; onClose: () => void; title: string; children: ReactNode; footer?: ReactNode; wide?: boolean;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const titleId = useId();
  useEffect(() => {
    if (!open) return;
    const prev = document.activeElement as HTMLElement | null;
    const el = ref.current;
    el?.querySelector<HTMLElement>("input,textarea,select,button:not([data-close])")?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "Tab" && el) {
        const f = el.querySelectorAll<HTMLElement>("button,a[href],input,select,textarea,[tabindex]:not([tabindex='-1'])");
        if (!f.length) return;
        const first = f[0], last = f[f.length - 1];
        if (e.shiftKey && document.activeElement === first) { last.focus(); e.preventDefault(); }
        else if (!e.shiftKey && document.activeElement === last) { first.focus(); e.preventDefault(); }
      }
    };
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => { document.removeEventListener("keydown", onKey); document.body.style.overflow = ""; prev?.focus(); };
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-pine/40 sm:items-center sm:p-4" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div ref={ref} role="dialog" aria-modal="true" aria-labelledby={titleId}
        className={`flex max-h-[92vh] w-full flex-col rounded-t-xl bg-white shadow-xl sm:rounded-xl ${wide ? "sm:max-w-3xl" : "sm:max-w-lg"}`}
        style={{ paddingBottom: "env(safe-area-inset-bottom)" }}>
        <div className="flex items-center justify-between border-b border-line px-5 py-4">
          <h2 id={titleId} className="text-lg font-semibold">{title}</h2>
          <button data-close onClick={onClose} aria-label="Close" className="-mr-2 flex h-11 w-11 items-center justify-center rounded-md hover:bg-paper"><X className="h-5 w-5" /></button>
        </div>
        <div className="overflow-y-auto px-5 py-4">{children}</div>
        {footer && <div className="flex flex-col-reverse gap-2 border-t border-line px-5 py-3 sm:flex-row sm:justify-end">{footer}</div>}
      </div>
    </div>
  );
}

/* ---------- Tabs ---------- */
export function Tabs<T extends string>({ tabs, value, onChange }: { tabs: { id: T; label: string }[]; value: T; onChange: (t: T) => void }) {
  return (
    <div role="tablist" className="-mx-4 mb-5 flex gap-1 overflow-x-auto border-b border-line px-4 sm:mx-0 sm:px-0">
      {tabs.map((t) => (
        <button key={t.id} role="tab" aria-selected={value === t.id} onClick={() => onChange(t.id)}
          className={`min-h-[44px] whitespace-nowrap border-b-2 px-3 text-sm font-medium ${value === t.id ? "border-signal text-ink" : "border-transparent text-ink-muted hover:text-ink"}`}>
          {t.label}
        </button>
      ))}
    </div>
  );
}

/* ---------- Toasts ---------- */
type Toast = { id: number; text: string; tone: "ok" | "error" };
const ToastCtx = createContext<(text: string, tone?: "ok" | "error") => void>(() => {});
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const push = useCallback((text: string, tone: "ok" | "error" = "ok") => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, text, tone }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4500);
  }, []);
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div aria-live="polite" className="pointer-events-none fixed inset-x-0 bottom-4 z-[60] flex flex-col items-center gap-2 px-4" style={{ marginBottom: "env(safe-area-inset-bottom)" }}>
        {toasts.map((t) => (
          <div key={t.id} className={`pointer-events-auto rounded-md px-4 py-3 text-sm font-medium shadow-lg ${t.tone === "ok" ? "bg-pine text-white" : "bg-danger text-white"}`}>{t.text}</div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}
export const useToast = () => useContext(ToastCtx);

/* ---------- Copy ---------- */
export function CopyButton({ text, label = "Copy" }: { text: string; label?: string }) {
  const [done, setDone] = useState(false);
  const toast = useToast();
  const copy = async () => {
    try { await navigator.clipboard.writeText(text); }
    catch {
      const ta = document.createElement("textarea"); ta.value = text; document.body.appendChild(ta); ta.select();
      document.execCommand("copy"); ta.remove();
    }
    setDone(true); toast("Copied to clipboard"); setTimeout(() => setDone(false), 1800);
  };
  return <Button size="sm" onClick={copy} icon={done ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}>{done ? "Copied" : label}</Button>;
}
