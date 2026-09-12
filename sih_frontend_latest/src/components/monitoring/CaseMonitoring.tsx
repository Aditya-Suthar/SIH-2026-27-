import { useState } from "react";
import { AnalysisHistory } from "./AnalysisHistory";
import { LineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { Activity, CheckCheck } from "lucide-react";
import { useRemote, api } from "../../lib/api";
import { dateTime, displayedTimeZone, observationPoints, words, priorityTone, riskTone } from "../../lib/monitoring";
import type { MonitoringCase, Analysis } from "../../lib/monitoring";
import { Card, CardHeader, CardContent, CardTitle } from "../ui/card";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";

export function CaseMonitoring({ caseId, indicatorId }: { caseId: string; indicatorId?: string | null }) {
  const indicatorQuery = indicatorId ? `?indicator_id=${encodeURIComponent(indicatorId)}` : "";
  const { data, error, loading, refresh } = useRemote<MonitoringCase & { history: Analysis[]; history_limited: boolean }>(`/api/cases/${encodeURIComponent(caseId)}/monitoring${indicatorQuery}`);
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
  const points = observationPoints(data.history, data.questionnaire_history ?? []);
  const questionnaire = data.current_questionnaire;
  const attempt = data.latest_attempt;
  const omitted = data.history.filter(row => row.status !== "completed" || row.distress_score === null).length;
  return <div className="space-y-4">
    {error && <p role="alert" className="text-sm text-warning">{error} Showing the last loaded data.</p>}
    {data.selected_evidence && <Card>
      <CardHeader><div className="flex flex-wrap items-center justify-between gap-3"><CardTitle>Selected historical evidence</CardTitle><Badge variant={data.selected_evidence.severity === "URGENT" ? "danger" : "orange"}>{data.selected_evidence.severity}</Badge></div><p className="text-xs text-muted-foreground">Indicator #{data.selected_evidence.id} · {dateTime(data.selected_evidence.created_at)} · {displayedTimeZone()}</p></CardHeader>
      <CardContent className="space-y-3">
        <div className="grid gap-4 sm:grid-cols-3"><div><p className="text-xs text-muted-foreground">Evidence score</p><p className="mt-1 text-3xl font-semibold">{data.selected_evidence.score_snapshot ?? "—"}<span className="text-sm font-normal text-muted-foreground">{data.selected_evidence.score_snapshot !== null ? " / 100" : " Score unavailable"}</span></p></div><div><p className="text-xs text-muted-foreground">Severity</p><p className="mt-2 font-medium">{data.selected_evidence.severity}</p></div><div><p className="text-xs text-muted-foreground">Source</p><p className="mt-2 font-medium capitalize">{words(data.selected_evidence.source)}</p></div></div>
        <div className="rounded-lg bg-secondary/50 p-4"><p className="text-sm font-semibold">Triggering rule</p><p className="mt-2 text-sm">{data.selected_evidence.triggering_rule}</p></div>
        <p className="text-sm text-muted-foreground">{data.selected_evidence.assessment ? `Linked assessment #${data.selected_evidence.assessment.id}` : data.selected_evidence.analysis ? `Linked analysis #${data.selected_evidence.analysis.id}` : "No linked assessment or analysis."} · {data.selected_evidence.reviewed ? `Reviewed${data.selected_evidence.reviewed_at ? ` ${dateTime(data.selected_evidence.reviewed_at)}` : ""}` : "Awaiting review"}</p>
      </CardContent>
    </Card>}
    <Card>
      <CardHeader><div className="flex flex-wrap items-center justify-between gap-3"><CardTitle><Activity className="mr-2 inline h-4 w-4 text-primary" />Current case state</CardTitle><Badge variant={priorityTone[data.category]}>{data.category === "UNASSESSED" ? "Not yet assessed" : `${data.category} priority`}</Badge></div><p className="text-xs text-muted-foreground">As of {dateTime(data.current_state_at)} · {displayedTimeZone()}. Decision support for human review.</p></CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-3"><div><p className="text-xs text-muted-foreground">{data.current_source === "questionnaire" ? "Questionnaire score" : "Latest distress indicator"}</p><p className="mt-1 text-3xl font-semibold">{data.current_score ?? "—"}<span className="text-sm font-normal text-muted-foreground">{data.current_score !== null ? " / 100" : " Score unavailable"}</span></p></div><div><p className="text-xs text-muted-foreground">Risk indicator</p><Badge className="mt-2" variant={riskTone(data.current_risk)}>{data.current_risk ?? "Unassessed"}</Badge></div><div><p className="text-xs text-muted-foreground">Historical trend</p><p className="mt-2 text-base font-medium capitalize">{words(data.trend.state)}</p></div></div>
        <p className="text-sm text-muted-foreground">{data.current_source === "questionnaire" ? "Questionnaire score" : data.current_source === "text_ai" ? "Text AI score" : "No scored source available"}{data.current_source === "text_ai" && data.questionnaire_score != null ? ` · Questionnaire score: ${data.questionnaire_score} / 100` : ""}</p>
        {data.latest_attempt_status === "failed" && <p role="status" className="rounded-lg bg-warning/10 p-3 text-sm text-warning">{data.latest_attempt?.error_message || "Analysis failed. The source remains saved; no AI score was produced for this attempt."}</p>}
        {data.latest_attempt_status === "pending" && <p className="rounded-lg bg-secondary p-3 text-sm">Latest analysis pending. It has not contributed a score.</p>}
        {!!data.alerts.length && <div className="flex flex-wrap gap-2">{data.alerts.map(alert => <Badge variant="warning" key={alert}>{alert}</Badge>)}</div>}
        <div className="rounded-lg bg-secondary/50 p-4"><p className="text-sm font-semibold">Why this priority</p><ul className="mt-2 space-y-1 text-sm text-muted-foreground">{data.reasons.map(reason => <li key={reason}>• {reason}</li>)}</ul><p className="mt-3 text-xs text-muted-foreground">{data.trend.explanation}</p></div>
        <div><p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Latest AI observation</p><p className="mt-2 text-sm">{data.latest_analysis?.reason ?? "No successful text analysis yet. A saved check-in or eligible victim message will appear here after analysis."}</p><div className="mt-2 flex flex-wrap gap-2">{data.latest_analysis?.emotions?.map(emotion => <Badge key={emotion} variant="outline">{emotion}</Badge>)}</div></div>
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4"><p className="text-xs text-muted-foreground">{data.review ? `Reviewed ${dateTime(data.review.reviewed_at)} · counsellor #${data.review.reviewer_id}` : "Latest successful analysis has not been acknowledged by the assigned counsellor."}</p>
        {localStorage.getItem("role") === "counsellor" && <Button onClick={() => void review()} disabled={reviewing || !data.latest_analysis || !!data.review} variant={data.review ? "outline" : "default"}><CheckCheck className="h-4 w-4" />{reviewing ? "Saving..." : data.review ? "Reviewed" : "Mark as reviewed"}</Button>}</div>
        {reviewError && <p role="alert" className="text-sm text-warning">{reviewError}</p>}
      </CardContent>
    </Card>
    <Card><CardHeader><CardTitle>Current questionnaire evidence</CardTitle></CardHeader><CardContent className="space-y-2">
      <p>Questionnaire score: {questionnaire?.score != null ? `${questionnaire.score} / 100` : "Score unavailable"}</p>
      <p>Risk: {questionnaire?.risk ?? "Not assessed"}</p><p>{dateTime(questionnaire?.observed_at ?? null)} · {displayedTimeZone()}</p>
      {questionnaire?.safety_override && <p>Critical safety override triggered by the questionnaire response.</p>}
    </CardContent></Card>
    <Card><CardHeader><CardTitle>Latest text-AI observation</CardTitle></CardHeader><CardContent className="space-y-2">
      <p>{attempt?.status === "completed" ? "AI analysis completed" : attempt?.status === "pending" ? "AI analysis pending" : attempt?.status === "failed" ? "AI analysis temporarily unavailable" : "AI analysis not requested"}</p>
      {attempt?.status === "completed" && <><p>Text-AI score: {attempt.distress_score} / 100 · Risk: {attempt.risk_level}</p><p>{attempt.emotions?.join(", ")}</p><p>{attempt.reason}</p></>}
      {attempt && <p>{dateTime(attempt.finished_at || attempt.created_at)} · {displayedTimeZone()}</p>}
    </CardContent></Card>
    <Card><CardHeader><CardTitle>Distress history</CardTitle><p className="text-xs text-muted-foreground">Questionnaire and successful text-AI observations · displayed in your timezone</p></CardHeader><CardContent>
      {points.length ? <div className="h-64 w-full" aria-label="Distress history chart"><ResponsiveContainer width="100%" height="100%"><LineChart data={points} margin={{ left: -20, right: 16, bottom: 8, top: 10 }}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(214 35% 89%)" /><XAxis type="number" dataKey="time" domain={points.length === 1 ? [points[0].time - 3600000, points[0].time + 3600000] : ["dataMin", "dataMax"]} tickFormatter={value => new Date(value).toLocaleDateString([], { month:"short", day:"numeric" })} tick={{ fontSize:11 }} minTickGap={35} /><YAxis domain={[0,100]} tick={{ fontSize:11 }} /><Tooltip labelFormatter={label => dateTime(new Date(Number(label)).toISOString())}  /><Legend /><Line name="Questionnaire" type="linear" dataKey="questionnaire" connectNulls stroke="hsl(210 70% 45%)" dot={{r:4}} isAnimationActive={false} /><Line name="Text-AI" connectNulls type="linear" dataKey="text_ai" stroke="hsl(152 55% 38%)" strokeWidth={2} dot={{ r:4 }} activeDot={{ r:6 }} isAnimationActive={false} /></LineChart></ResponsiveContainer></div> : <div className="flex h-44 items-center justify-center rounded-lg border border-dashed text-center text-sm text-muted-foreground">No numerical observations to chart yet.</div>}
      <p className="mt-3 text-xs text-muted-foreground">{points.length === 1 ? "One observation is shown. More days are needed to calculate a trend. " : ""}{omitted ? `${omitted} pending/failed records excluded from the chart. ` : ""}{data.history_limited ? "Showing the latest 200 records; older records remain available through the history API." : "Scores are indicators, not a clinical assessment."}</p>
      {data.trend.state === "insufficient_data" && <p className="text-sm">Insufficient data for trend</p>}
      <AnalysisHistory key={caseId} caseId={caseId} />
    </CardContent></Card>
  </div>;
}
