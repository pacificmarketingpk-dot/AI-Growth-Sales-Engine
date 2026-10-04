import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { BarChart3, Brain, CalendarDays, Flame, Handshake, LayoutDashboard, LogOut, Menu, MessagesSquare, Send, Settings, Users, X } from "lucide-react";
import { useAuth } from "../hooks/useAuth";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/prospects", label: "Prospects", icon: Users },
  { to: "/analysis", label: "AI Analysis", icon: Brain },
  { to: "/hot-leads", label: "Hot Leads", icon: Flame },
  { to: "/conversations", label: "Conversations", icon: MessagesSquare },
  { to: "/outreach", label: "Outreach", icon: Send },
  { to: "/meetings", label: "Meetings", icon: Handshake },
  { to: "/calendar", label: "Calendar", icon: CalendarDays },
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
  { to: "/settings", label: "Settings", icon: Settings },
];

function Mark() {
  return (
    <svg viewBox="0 0 32 32" className="h-8 w-8 shrink-0" aria-hidden>
      <rect width="32" height="32" rx="7" fill="#16403F" />
      <path d="M8 22 L14 15 L18 18 L24 10" stroke="#D98E04" strokeWidth="3" fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function NavItems({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <ul className="space-y-0.5">
      {NAV.map(({ to, label, icon: Icon, end }) => (
        <li key={to}>
          <NavLink to={to} end={end} onClick={onNavigate}
            className={({ isActive }) => `flex min-h-[44px] items-center gap-3 rounded-md px-3 text-[15px] transition-colors ${isActive
              ? "bg-pine-2 font-medium text-white shadow-[inset_3px_0_0_#D98E04]" : "text-pine-text hover:bg-pine-2/60 hover:text-white"}`}>
            <Icon className="h-[18px] w-[18px]" aria-hidden />{label}
          </NavLink>
        </li>
      ))}
    </ul>
  );
}

export function AppLayout() {
  const { user, logout, brand } = useAuth();
  const [open, setOpen] = useState(false);
  const loc = useLocation();
  useEffect(() => setOpen(false), [loc.pathname]);
  useEffect(() => {
    if (!open) return;
    const k = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("keydown", k);
    return () => document.removeEventListener("keydown", k);
  }, [open]);

  const sidebar = (onNavigate?: () => void, drawer = false) => (
    <div className="flex h-full flex-col">
      <div className={`flex items-center gap-3 px-4 pb-6 pt-5 ${drawer ? "pr-14" : ""}`}><Mark /><span className="font-display text-[17px] font-semibold leading-tight text-white">{brand}</span></div>
      <nav aria-label="Main" className="flex-1 overflow-y-auto px-3"><NavItems onNavigate={onNavigate} /></nav>
      <div className="border-t border-pine-2 p-3">
        <p className="truncate px-3 text-sm text-white">{user?.name || user?.email}</p>
        <p className="truncate px-3 text-xs text-pine-dim">{user?.email}</p>
        <button onClick={logout} className="mt-2 flex min-h-[44px] w-full items-center gap-3 rounded-md px-3 text-pine-text hover:bg-pine-2/60 hover:text-white">
          <LogOut className="h-[18px] w-[18px]" aria-hidden /> Sign out
        </button>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen lg:pl-64">
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-2 focus:top-2 focus:z-[70] focus:rounded focus:bg-white focus:px-3 focus:py-2">Skip to content</a>
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 bg-pine lg:block">{sidebar()}</aside>

      {/* Mobile / tablet top bar */}
      <header className="sticky top-0 z-30 flex h-14 items-center gap-2 border-b border-pine-2 bg-pine px-2 lg:hidden" style={{ paddingTop: "env(safe-area-inset-top)" }}>
        <button onClick={() => setOpen(true)} aria-label="Open menu" aria-expanded={open} className="flex h-11 w-11 items-center justify-center rounded-md text-white hover:bg-pine-2"><Menu /></button>
        <Mark /><span className="truncate font-display font-semibold text-white">{brand}</span>
      </header>
      {open && (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true" aria-label="Menu">
          <div className="absolute inset-0 bg-black/40" onClick={() => setOpen(false)} />
          <div className="absolute inset-y-0 left-0 w-[82%] max-w-xs bg-pine shadow-xl" style={{ paddingTop: "env(safe-area-inset-top)" }}>
            <button onClick={() => setOpen(false)} aria-label="Close menu" className="absolute right-2 top-3 flex h-11 w-11 items-center justify-center rounded-md text-white hover:bg-pine-2"><X /></button>
            {sidebar(() => setOpen(false), true)}
          </div>
        </div>
      )}

      <main id="main" className="mx-auto max-w-[1280px] px-4 py-6 sm:px-6 lg:px-8 lg:py-8" style={{ paddingBottom: "calc(2rem + env(safe-area-inset-bottom))" }}>
        <Outlet />
      </main>
    </div>
  );
}
