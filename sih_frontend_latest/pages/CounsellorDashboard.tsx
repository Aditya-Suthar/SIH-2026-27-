import {SessionList} from "../src/pages/Sessions";
import {SupportRequests} from "../src/pages/Operations";
import { Link } from "react-router-dom";
import { Briefcase, Activity, ShieldCheck, Clock3 } from "lucide-react";
import { Card, CardContent } from "../src/components/ui/card";
import { useRemote } from "../src/lib/api";
import type { MonitoringCase } from "../src/lib/monitoring";
import { PriorityQueue } from "../src/components/monitoring/PriorityQueue";
export default function CounsellorDashboard() {
  const { data, error, loading, refresh } = useRemote<{ items: MonitoringCase[] }>("/api/monitoring/cases");
  const cases = data?.items ?? [];
  return <div className="space-y-6">
    <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="mb-2 text-xs font-semibold uppercase tracking-widest text-primary">SAHAS · Counsellor workspace</p><h1 className="text-2xl font-bold tracking-tight">Care starts with attention</h1><p className="mt-1 text-sm text-muted-foreground">Your assigned cases, ordered by explainable distress indicators.</p></div><Link to="/counsellor/messages" className="rounded-lg border border-border bg-card px-4 py-2 text-sm font-medium text-primary">Open conversations</Link></div>
    <div className="grid gap-4 sm:grid-cols-3">{[
      { label: "Assigned cases", value: cases.length, icon: Briefcase },
      { label: "Review recommended", value: cases.filter(c => c.needs_review).length, icon: Activity },
      { label: "Rapidly worsening", value: cases.filter(c => c.trend.state === "rapidly_worsening").length, icon: Clock3 },
    ].map(stat => <Card key={stat.label}><CardContent className="flex items-center justify-between pt-5"><div><p className="text-xs text-muted-foreground">{stat.label}</p><p className="mt-2 text-3xl font-semibold">{loading || !data ? "—" : stat.value}</p></div><stat.icon className="h-6 w-6 text-primary/70" /></CardContent></Card>)}</div>
    <p className="flex items-start gap-2 text-xs text-muted-foreground"><ShieldCheck className="h-4 w-4 shrink-0 text-primary" />AI supports your judgement. Priority reflects recorded signals, not a diagnosis or a confirmed emergency.</p>
    {error && <p role="alert" className="rounded-lg bg-warning/10 p-3 text-sm text-warning">{error} {data ? "Showing last loaded data." : ""}</p>}
    {loading ? <Card><CardContent className="py-12 text-center text-sm text-muted-foreground">Loading your monitoring queue...</CardContent></Card> : <PriorityQueue items={cases} onRefresh={() => void refresh()} />}
      <SupportRequests/><SessionList/>
    </div>;
}
