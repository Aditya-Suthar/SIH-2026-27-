import { Link } from "react-router-dom";
import { ArrowUpRight, ShieldCheck, RefreshCw } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { dateTime, priorityTone, riskTone, words } from "../../lib/monitoring";
import type { MonitoringCase } from "../../lib/monitoring";

export function PriorityQueue({ items, onRefresh, emptyMessage = "No cases are assigned to your account yet." }: { items: MonitoringCase[]; onRefresh: () => void; emptyMessage?: string }) {
  return <Card>
    <CardHeader className="gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div><CardTitle>Priority monitoring queue</CardTitle><p className="mt-1 text-sm text-muted-foreground">Review the signals, then decide the next step.</p></div>
      <Button variant="outline" size="sm" onClick={onRefresh}><RefreshCw className="h-4 w-4" /> Refresh</Button>
    </CardHeader>
    <CardContent className="space-y-3">
      {items.length === 0 && <p className="py-8 text-center text-sm text-muted-foreground">{emptyMessage}</p>}
      {items.map(item => <article key={item.case_id} className={`rounded-xl border p-4 sm:p-5 ${item.category === "URGENT" ? "border-danger/30 bg-danger/[0.025]" : "border-border"}`}>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2"><Link to={`/cases/${encodeURIComponent(item.case_id)}`} className="text-base font-semibold text-primary hover:underline">{item.case_id}</Link><Badge variant={priorityTone[item.category]}>{item.category === "UNASSESSED" ? "Not yet assessed" : item.category}</Badge>
          {item.needs_review ? <Badge variant="warning">Review recommended</Badge> : item.review ? <Badge variant="success"><ShieldCheck className="h-3 w-3" /> Reviewed</Badge> : null}</div>
          <Link className="inline-flex items-center gap-1 text-sm font-medium text-primary" to={`/cases/${encodeURIComponent(item.case_id)}`}>Open workspace <ArrowUpRight className="h-4 w-4" /></Link>
        </div>
        <div className="mt-4 grid gap-4 sm:grid-cols-3 lg:grid-cols-4">
          <div><p className="text-xs text-muted-foreground">Latest AI distress indicator</p><p className="mt-1 text-2xl font-semibold">{item.latest_analysis?.distress_score ?? "—"}<span className="text-sm font-normal text-muted-foreground">{item.latest_analysis ? " / 100" : " No successful analysis"}</span></p></div>
          <div><p className="text-xs text-muted-foreground">Risk / trend</p><div className="mt-1 flex flex-wrap gap-2"><Badge variant={riskTone(item.latest_analysis?.risk_level)}>{item.latest_analysis?.risk_level ?? "Unknown"}</Badge><span className="text-sm capitalize">{words(item.trend.state)}</span></div></div>
          <div><p className="text-xs text-muted-foreground">Recent emotions</p><p className="mt-1 text-sm capitalize">{item.latest_analysis?.emotions?.join(", ") || "None recorded"}</p></div>
          <div><p className="text-xs text-muted-foreground">Latest analysis activity</p><p className="mt-1 text-sm">{dateTime(item.latest_activity)}</p></div>
        </div>
        <div className="mt-4 border-t border-border/70 pt-3"><p className="text-xs font-semibold text-muted-foreground">WHY THIS PRIORITY</p><p className="mt-1 text-sm text-muted-foreground">{item.reasons.join(" ")}</p></div>
        {item.latest_attempt_status === "failed" && <p className="mt-2 text-xs text-warning">Latest analysis unavailable. Any score shown is from the last successful analysis.</p>}
        {item.latest_attempt_status === "pending" && <p className="mt-2 text-xs text-muted-foreground">Latest analysis is pending; its result is not included yet.</p>}
      </article>)}
    </CardContent>
  </Card>;
}
