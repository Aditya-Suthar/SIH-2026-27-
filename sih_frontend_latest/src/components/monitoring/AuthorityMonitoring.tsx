import { BarChart, Bar, CartesianGrid, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { useRemote } from "../../lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Button } from "../ui/button";
type Summary = { total_cases: number; risk_distribution: Record<string,number>; requiring_attention: number; unreviewed_urgent: number; analysis_unavailable: number };
export function AuthorityMonitoring() {
  const { data, error, loading, refresh } = useRemote<Summary>("/api/monitoring/summary");
  return <Card><CardHeader className="gap-3 sm:flex-row sm:justify-between"><div><CardTitle>AI monitoring overview</CardTitle><p className="mt-1 text-xs text-muted-foreground">Aggregate decision-support indicators · no conversation content</p></div><Button size="sm" variant="outline" onClick={() => void refresh()}>Refresh</Button></CardHeader><CardContent className="space-y-5">
    {error && <p role="alert" className="text-sm text-warning">{error}</p>}
    {loading ? <p className="text-sm text-muted-foreground">Loading monitoring summary...</p> : data && <><div className="grid grid-cols-2 gap-4 xl:grid-cols-4">{[
      ["Critical indicators", data.risk_distribution.critical], ["High indicators", data.risk_distribution.high],
      ["Require attention", data.requiring_attention], ["Unreviewed urgent", data.unreviewed_urgent],
    ].map(([label,value]) => <div key={label} className="rounded-lg border border-border p-4"><p className="text-xs text-muted-foreground">{label}</p><p className="mt-2 text-3xl font-semibold">{value}</p></div>)}</div>
    {data.total_cases ? <div className="h-56" aria-label="AI risk distribution chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={Object.entries(data.risk_distribution).map(([risk,count]) => ({ risk, count }))} margin={{left:-20,right:10}}><CartesianGrid vertical={false} strokeDasharray="3 3" /><XAxis dataKey="risk" tick={{fontSize:11}} /><YAxis allowDecimals={false} tick={{fontSize:11}} /><Tooltip /><Bar dataKey="count" name="Cases" fill="hsl(152 55% 38%)" radius={[4,4,0,0]} isAnimationActive={false} /></BarChart></ResponsiveContainer></div> : <p className="py-6 text-center text-sm text-muted-foreground">No cases available for monitoring.</p>}
    <p className="text-xs text-muted-foreground">{data.risk_distribution.unassessed} cases have no successful AI result. {data.analysis_unavailable} cases have a pending or failed latest attempt. Counts are indicators for review, not confirmed emergencies.</p></>}
  </CardContent></Card>;
}
