import { createContext, ReactNode, useCallback, useContext, useEffect, useState } from "react";
import { api } from "../services/api";
import type { User } from "../types";

interface AuthCtx {
  user: User | null; ready: boolean; brand: string;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string) => Promise<void>;
  logout: () => Promise<void>; setBrand: (b: string) => void;
}
const Ctx = createContext<AuthCtx>(null as unknown as AuthCtx);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const [brand, setBrand] = useState("AI Growth Sales Engine");

  const loadBrand = useCallback(async () => {
    try { const s = await api.get<{ brand_name: string }>("/api/settings"); setBrand(s.brand_name || brand); }
    catch { /* keep default */ }
  }, [brand]);

  useEffect(() => {
    api.get<User>("/api/auth/me").then((u) => { setUser(u); loadBrand(); }).catch(() => setUser(null))
      .finally(() => setReady(true));
    const onUnauth = () => setUser(null);
    window.addEventListener("age:unauthorized", onUnauth);
    return () => window.removeEventListener("age:unauthorized", onUnauth);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect(() => { document.title = brand; }, [brand]);

  const value: AuthCtx = {
    user, ready, brand, setBrand,
    login: async (email, password) => { setUser(await api.post<User>("/api/auth/login", { email, password })); loadBrand(); },
    register: async (email, password, name) => { setUser(await api.post<User>("/api/auth/register", { email, password, name })); },
    logout: async () => { await api.post("/api/auth/logout"); setUser(null); },
  };
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}
export const useAuth = () => useContext(Ctx);
