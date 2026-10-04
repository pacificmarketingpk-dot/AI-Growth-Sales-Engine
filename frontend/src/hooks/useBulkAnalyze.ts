import { useEffect, useRef, useState } from "react";
import { api } from "../services/api";

export interface Job { id: number; status: string; total: number; completed: number; failed: number; errors: { prospect_id: number; error: string }[] }

export function useBulkAnalyze(onFinished: () => void) {
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<number>();
  const done = useRef(onFinished); done.current = onFinished;

  const poll = (id: number) => {
    timer.current = window.setTimeout(async () => {
      try {
        const j = await api.get<Job>(`/api/analysis-jobs/${id}`);
        setJob(j);
        if (j.status === "done") done.current(); else poll(id);
      } catch (e) { setError((e as Error).message); }
    }, 1200);
  };
  useEffect(() => () => window.clearTimeout(timer.current), []);

  const start = async (ids: number[], force = false) => {
    setError(null);
    try {
      const r = await api.post<{ job_id: number; total: number }>("/api/prospects/bulk-analyze", { prospect_ids: ids, force });
      setJob({ id: r.job_id, status: "queued", total: r.total, completed: 0, failed: 0, errors: [] });
      poll(r.job_id);
    } catch (e) { setError((e as Error).message); }
  };
  return { job, error, start, clear: () => setJob(null) };
}
