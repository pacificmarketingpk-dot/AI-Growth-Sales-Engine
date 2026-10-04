import type { Breakdown } from "../types";
import { BREAKDOWN_PARTS, categoryOf } from "../utils/format";

const FILL: Record<string, string> = { HOT: "bg-hot", HIGH: "bg-high", MEDIUM: "bg-medium", LOW: "bg-low" };

/**
 * The signature element: one bar, six segments sized by each criterion's weight,
 * each segment filled by how much of that weight the prospect earned.
 */
export function ScoreBar({ breakdown, score, compact = false }: { breakdown: Breakdown | null; score: number | null; compact?: boolean }) {
  const cat = categoryOf(score);
  const fill = cat ? FILL[cat] : "bg-low";
  const desc = breakdown ? BREAKDOWN_PARTS.map((p) => `${p.label} ${breakdown[p.key]} of ${p.max}`).join(", ") : "Not analyzed";
  return (
    <div role="img" aria-label={`Lead score ${score ?? "not available"}. ${desc}`}>
      <div className={`flex w-full gap-[3px] ${compact ? "h-1.5" : "h-3"}`}>
        {BREAKDOWN_PARTS.map((p) => {
          const v = breakdown ? breakdown[p.key] : 0;
          return (
            <div key={p.key} className="relative overflow-hidden rounded-[2px] bg-line" style={{ flexGrow: p.max, flexBasis: 0 }}>
              <div className={`absolute inset-y-0 left-0 ${fill}`} style={{ width: `${(v / p.max) * 100}%` }} />
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function ScoreBreakdownTable({ breakdown }: { breakdown: Breakdown }) {
  return (
    <dl className="mt-4 grid grid-cols-1 gap-x-6 gap-y-2 sm:grid-cols-2">
      {BREAKDOWN_PARTS.map((p) => (
        <div key={p.key} className="flex items-center justify-between border-b border-line/70 py-1.5 text-sm">
          <dt className="text-ink-muted">{p.label}</dt>
          <dd className="tnum font-semibold">{breakdown[p.key]}<span className="font-normal text-ink-muted"> / {p.max}</span></dd>
        </div>
      ))}
    </dl>
  );
}
