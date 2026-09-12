import { useEffect } from "react";
import { useRemote } from "../../lib/api";
import { dateTime } from "../../lib/monitoring";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Badge } from "../ui/badge";
export function VictimCheckIns({ revision }: { revision: number }) {
  const { data, loading, error, refresh } = useRemote<{items: Array<{id: number; created_at: string; text_included: boolean; analysis_status: string}>}>("/api/victim/check-ins");
  useEffect(() => { if (revision) void refresh(); }, [revision, refresh]);
  return <Card><CardHeader><CardTitle>Your saved check-ins</CardTitle><p className="text-xs text-muted-foreground">Share at your own pace. Your counsellor can use your updates to support you.</p></CardHeader><CardContent className="space-y-3">
    {loading && <p className="text-sm text-muted-foreground">Loading your check-ins...</p>}
    {error && <p role="alert" className="text-sm text-warning">{error}</p>}
    {!loading && !error && !data?.items.length && <p className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">No check-ins saved yet. You can start with the form below.</p>}
    {data?.items.map(row => <div key={row.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border p-3 text-sm"><div><p className="font-medium">Check-in saved</p><p className="text-xs text-muted-foreground">{dateTime(row.created_at)} · {row.text_included ? "With optional text" : "Questionnaire"}</p></div><Badge variant={row.analysis_status === "failed" ? "warning" : "default"}>{row.analysis_status === "failed" ? "AI analysis temporarily unavailable" : row.analysis_status === "pending" ? "AI analysis pending" : row.analysis_status === "completed" ? "AI analysis completed" : "AI analysis not requested"}</Badge></div>)}
  </CardContent></Card>;
}
