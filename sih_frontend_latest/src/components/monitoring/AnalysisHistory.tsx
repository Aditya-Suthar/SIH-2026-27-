import { useState } from "react";
import { useRemote } from "../../lib/api";
import { dateTime } from "../../lib/monitoring";
import type { Analysis } from "../../lib/monitoring";
import { Button } from "../ui/button";

export function AnalysisHistory({ caseId }: { caseId: string }) {
  const [offset, setOffset] = useState(0);
  const { data, error, loading } = useRemote<{ items: Analysis[]; has_more: boolean }>(
    `/api/cases/${encodeURIComponent(caseId)}/ai-analyses?limit=50&offset=${offset}`);
  return <div className="mt-4 space-y-3">
    <p className="text-sm font-semibold">Complete analysis history</p>
    {error && <p role="alert">{error}</p>}
    {loading && <p role="status">Loading history...</p>}
    {data?.items.map(row => <article key={row.id} className="rounded border p-3 text-sm">
      <p>{dateTime(row.created_at)} · {row.source_type === "message" ? "Victim message" : "Questionnaire note"} · {row.status === "failed" ? "Analysis failed" : row.status === "pending" ? "Analysis pending" : "Completed"}</p>
      {row.status === "completed" ? <><p>Text AI score: {row.distress_score} / 100 · Risk: {row.risk_level}</p><p>{row.emotions?.join(", ")}</p><p>{row.reason}</p></> : <p>{row.error_message || "Waiting for a saved AI result."}</p>}
    </article>)}
    {data && !data.items.length && <p>No text analysis has been requested.</p>}
    <div className="flex gap-2"><Button variant="outline" disabled={offset === 0 || loading} onClick={() => setOffset(value => Math.max(0, value - 50))}>Previous</Button><Button variant="outline" disabled={!data?.has_more || loading} onClick={() => setOffset(value => value + 50)}>Next</Button></div>
  </div>;
}
