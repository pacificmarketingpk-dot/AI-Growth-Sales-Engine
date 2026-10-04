import type { Job } from "../hooks/useBulkAnalyze";
import { Button } from "./ui";

export function BulkProgress({ job, onClose }: { job: Job; onClose: () => void }) {
  const processed = job.completed + job.failed;
  const running = job.status !== "done";
  return (
    <div className="mb-4 rounded-lg border border-line bg-white p-4" role="status" aria-live="polite">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="font-medium">{running ? `Analyzing ${Math.min(processed + 1, job.total)} / ${job.total}` : `Finished: ${job.completed} analyzed, ${job.failed} failed`}</p>
        {!running && <Button size="sm" onClick={onClose}>Dismiss</Button>}
      </div>
      <div className="mt-3 h-2 overflow-hidden rounded-sm bg-line">
        <div className="h-2 bg-pine-3 transition-[width]" style={{ width: `${(processed / job.total) * 100}%` }} />
      </div>
      {job.errors.length > 0 && (
        <ul className="mt-3 space-y-1 text-sm text-ink-muted">
          {job.errors.slice(0, 5).map((e) => <li key={e.prospect_id}>Prospect #{e.prospect_id}: {e.error}</li>)}
        </ul>
      )}
    </div>
  );
}
