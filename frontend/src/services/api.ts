/** Thin fetch wrapper. Session lives in an httpOnly cookie; no secrets ever touch the browser. */
export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

const BASE = import.meta.env.VITE_API_URL ?? "";

async function request<T>(method: string, path: string, body?: unknown, isForm = false): Promise<T> {
  const headers: Record<string, string> = { "X-Requested-With": "age" };
  if (body !== undefined && !isForm) headers["Content-Type"] = "application/json";
  let res: Response;
  try {
    res = await fetch(BASE + path, {
      method, headers, credentials: "include",
      body: body === undefined ? undefined : isForm ? (body as FormData) : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, "Can't reach the server. Check your connection and try again.");
  }
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  let data: unknown = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = null; }
  if (!res.ok) {
    const detail = (data as { detail?: unknown })?.detail;
    const msg = typeof detail === "string" ? detail : res.status === 401 ? "Please sign in." : "Request failed.";
    if (res.status === 401) window.dispatchEvent(new Event("age:unauthorized"));
    throw new ApiError(res.status, msg);
  }
  return data as T;
}

export const api = {
  get: <T>(p: string) => request<T>("GET", p),
  post: <T>(p: string, b?: unknown) => request<T>("POST", p, b ?? {}),
  put: <T>(p: string, b: unknown) => request<T>("PUT", p, b),
  del: <T>(p: string) => request<T>("DELETE", p),
  form: <T>(p: string, f: FormData) => request<T>("POST", p, f, true),
  url: (p: string) => BASE + p,
};
