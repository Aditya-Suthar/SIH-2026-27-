import { useState } from "react";
import { LineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { Activity, CheckCheck } from "lucide-react";
import { useRemote, api } from "../../lib/api";
import { dateTime, words, priorityTone, riskTone } from "../../lib/monitoring";
import type { MonitoringCase, Analysis } from "../../lib/monitoring";
import { Card, CardHeader, CardContent, CardTitle } from "../ui/card";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";

export function CaseMonitoring({ caseId }: { caseId: string }) {
  const { data, error, loading, refresh } = useRemote<MonitoringCase & { history: Analysis[]; history_limited: boolean }>(`/api/cases/${encodeURIComponent(caseId)}/monitoring`);
  const [reviewing, setReviewing] = useState(false); const [reviewError, setReviewError] = useState("");
  async function review() {
    if (!data?.latest_analysis) return;
    setReviewing(true); setReviewError("");
    try { await api(`/api/cases/${encodeURIComponent(caseId)}/ai-review`, { method: "POST", body: JSON.stringify({ analysis_id: data.latest_analysis.id }) }); await refresh(); }
    catch(e) { setReviewError(e instanceof Error ? e.message : "Could not save review."); }
    finally { setReviewing(false); }
  }
  if (loading) return <Card><CardContent className="pt-6 text-sm">Loading AI monitoring...</CardContent></Card>;
  if (!data) return <Card><CardContent className="pt-6"><p role="alert" className="text-sm text-warning">{error || "Monitoring unavailable."}</p><Button variant="outline" onClick={() => void refresh()}>Retry</Button></CardContent></Card>;
  const points = data.history.filter(row => row.status === "completed" && row.distress_score !== null).map(row => ({ ...row, time: new Date(row.created_at).getTime() }));
  const omitted = data.history.length - points.length;
  return <div className="space-y-4">
    {error && <p role="alert" className="text-sm text-warning">{error} Showing the last loaded data.</p>}
    <Card>
      <CardHeader><div className="flex flex-wrap items-center justify-between gap-3"><CardTitle><Activity className="mr-2 inline h-4 w-4 text-primary" />AI monitoring</CardTitle><Badge variant={priorityTone[data.category]}>{data.category === "UNASSESSED" ? "Not yet assessed" : `${data.category} priority`}</Badge></div><p className="text-xs text-muted-foreground">Decision support for human review. These indicators are not a diagnosis.</p></CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-3"><div><p className="text-xs text-muted-foreground">Latest successful distress indicator</p><p className="mt-1 text-3xl font-semibold">{data.current_score ?? "—"}<span className="text-sm font-normal text-muted-foreground">{data.current_score !== null ? " / 100" : " Score unavailable"}</span></p></div><div><p className="text-xs text-muted-foreground">Risk indicator</p><Badge className="mt-2" variant={riskTone(data.current_risk)}>{data.current_risk ?? "Unassessed"}</Badge></div><div><p className="text-xs text-muted-foreground">Historical trend</p><p className="mt-2 text-base font-medium capitalize">{words(data.trend.state)}</p></div></div>
        {data.latest_attempt_status === "failed" && <p className="rounded-lg bg-warning/10 p-3 text-sm text-warning">Latest analysis unavailable. The original text remains saved; any score shown is an earlier successful result.</p>}
        {data.latest_attempt_status === "pending" && <p className="rounded-lg bg-secondary p-3 text-sm">Latest analysis pending. It has not contributed a score.</p>}
        {!!data.alerts.length && <div className="flex flex-wrap gap-2">{data.alerts.map(alert => <Badge variant="warning" key={alert}>{alert}</Badge>)}</div>}
        <div className="rounded-lg bg-secondary/50 p-4"><p className="text-sm font-semibold">Why this priority</p><ul className="mt-2 space-y-1 text-sm text-muted-foreground">{data.reasons.map(reason => <li key={reason}>• {reason}</li>)}</ul><p className="mt-3 text-xs text-muted-foreground">{data.trend.explanation}</p></div>
        <div><p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Latest AI observation</p><p className="mt-2 text-sm">{data.latest_analysis?.reason ?? "No successful text analysis yet. A saved check-in or eligible victim message will appear here after analysis."}</p><div className="mt-2 flex flex-wrap gap-2">{data.latest_analysis?.emotions?.map(emotion => <Badge key={emotion} variant="outline">{emotion}</Badge>)}</div></div>
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4"><p className="text-xs text-muted-foreground">{data.review ? `Reviewed ${dateTime(data.review.reviewed_at)} · counsellor #${data.review.reviewer_id}` : "Latest successful analysis has not been acknowledged by the assigned counsellor."}</p>
        {localStorage.getItem("role") === "counsellor" && <Button onClick={() => void review()} disabled={reviewing || !data.latest_analysis || !!data.review} variant={data.review ? "outline" : "default"}><CheckCheck className="h-4 w-4" />{reviewing ? "Saving..." : data.review ? "Reviewed" : "Mark as reviewed"}</Button>}</div>
        {reviewError && <p role="alert" className="text-sm text-warning">{reviewError}</p>}
      </CardContent>
    </Card>
    <Card><CardHeader><CardTitle>Distress history</CardTitle><p className="text-xs text-muted-foreground">Successful text analyses on their actual timestamps · check-ins and victim messages</p></CardHeader><CardContent>
      {points.length ? <div className="h-64 w-full" aria-label="Distress history chart"><ResponsiveContainer width="100%" height="100%"><LineChart data={points} margin={{ left: -20, right: 16, bottom: 8, top: 10 }}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(214 35% 89%)" /><XAxis type="number" dataKey="time" domain={points.length === 1 ? [points[0].time - 3600000, points[0].time + 3600000] : ["dataMin", "dataMax"]} tickFormatter={value => new Date(value).toLocaleDateString([], { month:"short", day:"numeric" })} tick={{ fontSize:11 }} minTickGap={35} /><YAxis domain={[0,100]} tick={{ fontSize:11 }} /><Tooltip labelFormatter={label => dateTime(new Date(Number(label)).toISOString())} formatter={value => [value, "Distress indicator"]} /><Line type="linear" dataKey="distress_score" stroke="hsl(152 55% 38%)" strokeWidth={2} dot={{ r:4 }} activeDot={{ r:6 }} isAnimationActive={false} /></LineChart></ResponsiveContainer></div> : <div className="flex h-44 items-center justify-center rounded-lg border border-dashed text-center text-sm text-muted-foreground">No successful AI history to chart yet.</div>}
      <p className="mt-3 text-xs text-muted-foreground">{points.length === 1 ? "One observation is shown. More days are needed to calculate a trend. " : ""}{omitted ? `${omitted} pending/failed records excluded from the chart. ` : ""}{data.history_limited ? "Showing the latest 200 records; older records remain available through the history API." : "Scores are indicators, not a clinical assessment."}</p>
      <div className="mt-4 max-h-56 overflow-auto"><table className="w-full min-w-[450px] text-left text-xs"><thead><tr className="border-b border-border"><th className="py-2">Time</th><th>Source</th><th>Status</th><th>Indicator</th></tr></thead><tbody>{[...data.history].reverse().slice(0,20).map(row => <tr key={row.id} className="border-b border-border/50"><td className="py-2">{dateTime(row.created_at)}</td><td>{row.source_type === "message" ? "Victim message" : "Check-in"}</td><td>{row.status}</td><td>{row.status === "completed" ? `${row.distress_score}/100` : "—"}</td></tr>)}</tbody></table></div>
    </CardContent></Card>
  </div>;
}
