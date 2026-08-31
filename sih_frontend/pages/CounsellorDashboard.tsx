import { useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  AlertOctagon,
  Briefcase,
  CalendarClock,
  ClipboardList,
  FileWarning,
  HeartHandshake,
  MessageSquareWarning,
  PhoneCall,
  ScaleIcon,
  ShieldAlert,
  Sparkles,
  TrendingDown,
  TrendingUp,
  UserCheck,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "../src/components/ui/card";
import { Badge } from "../src/components/ui/badge";
import { Button } from "../src/components/ui/button";
import { cn } from "../lib/utils";

type RiskLevel = "Low" | "Moderate" | "High" | "Critical";

type ApiCase = {
  caseId: string;
  riskLevel: RiskLevel;
  assignedCounsellor: string;
  lastAssessment: string;
  interventionStatus: string;
};
type Trend = "up" | "down" | "flat";
type EscalationStatus = "None" | "Requested" | "In Progress";

const riskBadgeVariant: Record<RiskLevel, "danger" | "orange" | "warning" | "success"> = {
  Critical: "danger",
  High: "orange",
  Moderate: "warning",
  Low: "success",
};

const escalationBadgeVariant: Record<EscalationStatus, "default" | "warning" | "danger"> = {
  None: "default",
  Requested: "warning",
  "In Progress": "danger",
};


const priorityQueue = [
  {
    caseId: "SAH-1042",
    distress: 78,
    risk: "Critical" as RiskLevel,
    trend: "up" as Trend,
    lastInteraction: "2 hours ago",
    nextSession: "Today, 4:30 PM",
    escalation: "In Progress" as EscalationStatus,
  },
  {
    caseId: "SAH-1037",
    distress: 61,
    risk: "High" as RiskLevel,
    trend: "up" as Trend,
    lastInteraction: "Yesterday",
    nextSession: "Tomorrow, 11:00 AM",
    escalation: "Requested" as EscalationStatus,
  },
  {
    caseId: "SAH-1028",
    distress: 44,
    risk: "Moderate" as RiskLevel,
    trend: "down" as Trend,
    lastInteraction: "2 days ago",
    nextSession: "Fri, 2:00 PM",
    escalation: "None" as EscalationStatus,
  },
  {
    caseId: "SAH-1019",
    distress: 28,
    risk: "Low" as RiskLevel,
    trend: "flat" as Trend,
    lastInteraction: "5 days ago",
    nextSession: "Next Mon",
    escalation: "None" as EscalationStatus,
  },
];

const trendIcon: Record<Trend, typeof TrendingUp> = {
  up: TrendingUp,
  down: TrendingDown,
  flat: TrendingUp,
};

const alerts = [
  { title: "Sudden distress increase", caseId: "SAH-1042", time: "12 min ago", icon: AlertOctagon, tone: "text-danger" },
  { title: "Threat/intimidation reported", caseId: "SAH-1037", time: "1 hr ago", icon: ShieldAlert, tone: "text-danger" },
  { title: "Repeated missed check-ins", caseId: "SAH-1028", time: "Today", icon: MessageSquareWarning, tone: "text-warning" },
  { title: "Severe negative sentiment", caseId: "SAH-1019", time: "Yesterday", icon: FileWarning, tone: "text-warning" },
];

const schedule = [
  { time: "10:00 AM", caseId: "SAH-1028", type: "Follow-up session", done: true },
  { time: "11:30 AM", caseId: "SAH-1055", type: "Initial assessment", done: true },
  { time: "2:00 PM", caseId: "SAH-1037", type: "Counselling session", done: false },
  { time: "4:30 PM", caseId: "SAH-1042", type: "Priority check-in", done: false },
];

const trendData = [
  { label: "Mon", distress: 52 },
  { label: "Tue", distress: 58 },
  { label: "Wed", distress: 61 },
  { label: "Thu", distress: 69 },
  { label: "Fri", distress: 74 },
  { label: "Sat", distress: 71 },
  { label: "Sun", distress: 78 },
];

const flagSignals = [
  "Distress score increased by 26 points over 7 days",
  "Negative sentiment increased in last 2 check-ins",
  "Missed two scheduled check-ins",
  "Threat-related response detected in text check-in",
];

export default function CounsellorDashboard() {
  const [selectedCase, setSelectedCase] = useState(priorityQueue[0].caseId);
  const [cases, setCases] = useState<ApiCase[]>([]);

  useEffect(() => {
    const fetchCases = async () => {
      try {
        const token = localStorage.getItem("access_token");

        if (!token) return;

        const response = await fetch(
          "http://127.0.0.1:8000/api/cases",
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        if (!response.ok) {
          console.error("Failed to fetch cases:", response.status);
          return;
        }

        const data: ApiCase[] = await response.json();
        setCases(data);
      } catch (error) {
        console.error("Could not fetch cases:", error);
      }
    };

    fetchCases();
  }, []);

  const highRiskCases = cases.filter(
    (c) => c.riskLevel === "High" || c.riskLevel === "Critical"
  ).length;

  const kpis = [
    {
      id: "assigned",
      label: "Assigned Cases",
      value: String(cases.length),
      icon: ClipboardList,
      tone: "neutral" as const,
    },
    {
      id: "high-risk",
      label: "High Risk Cases",
      value: String(highRiskCases),
      helper: "Require close attention",
      icon: AlertOctagon,
      tone: "danger" as const,
    },
    {
      id: "sessions",
      label: "Today's Sessions",
      value: "6",
      helper: "2 completed so far",
      icon: HeartHandshake,
      tone: "neutral" as const,
    },
    {
      id: "followups",
      label: "Pending Follow-ups",
      value: "9",
      helper: "Due this week",
      icon: CalendarClock,
      tone: "neutral" as const,
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          Good Morning, {localStorage.getItem("name")}
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Your assigned victims, priority alerts and today's schedule.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {kpis.map((kpi) => {
          const isDanger = kpi.tone === "danger";
          return (
            <Card key={kpi.id}>
              <CardContent className="flex items-start justify-between gap-3 pt-5">
                <div className="space-y-1.5">
                  <p className="text-xs font-medium text-muted-foreground">{kpi.label}</p>
                  <p className="text-2xl font-bold tracking-tight text-foreground">{kpi.value}</p>
                  {kpi.helper && (
                    <p className={cn("text-xs font-medium", isDanger ? "text-danger" : "text-muted-foreground")}>
                      {kpi.helper}
                    </p>
                  )}
                </div>
                <div
                  className={cn(
                    "flex h-10 w-10 shrink-0 items-center justify-center rounded-lg",
                    isDanger ? "bg-danger/10 text-danger" : "bg-primary/10 text-primary"
                  )}
                >
                  <kpi.icon className="h-5 w-5" />
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Trend + alerts */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader className="flex-row items-center justify-between space-y-0">
            <div>
              <CardTitle>Distress Trend — {selectedCase}</CardTitle>
              <p className="mt-1 text-xs text-muted-foreground">Longitudinal signal for the selected case</p>
            </div>
          </CardHeader>
          <CardContent className="h-64 pt-2">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trendData} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                <defs>
                  <linearGradient id="counsellorDistressFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="hsl(0 72% 51%)" stopOpacity={0.22} />
                    <stop offset="100%" stopColor="hsl(0 72% 51%)" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(214 35% 89%)" vertical={false} />
                <XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: "hsl(215 18% 46%)" }} />
                <YAxis tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: "hsl(215 18% 46%)" }} width={32} />
                <Tooltip
                  contentStyle={{
                    borderRadius: 10,
                    border: "1px solid hsl(214 35% 89%)",
                    boxShadow: "0 4px 16px -4px rgb(30 64 130 / 0.15)",
                    fontSize: 12,
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="distress"
                  name="Distress Score"
                  stroke="hsl(0 72% 51%)"
                  strokeWidth={2}
                  fill="url(#counsellorDistressFill)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent Alerts</CardTitle>
            <p className="text-xs text-muted-foreground">Signals needing your attention</p>
          </CardHeader>
          <CardContent className="space-y-3">
            {alerts.map((a, i) => (
              <div key={i} className="flex items-start gap-2.5 text-sm">
                <a.icon className={cn("mt-0.5 h-4 w-4 shrink-0", a.tone)} />
                <div className="flex-1">
                  <p className="font-medium text-foreground">{a.title}</p>
                  <p className="text-xs text-muted-foreground">
                    {a.caseId} · {a.time}
                  </p>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* Priority queue */}
      <Card>
        <CardHeader>
          <CardTitle>Priority Victim Queue</CardTitle>
          <p className="text-xs text-muted-foreground">Cases sorted by risk and recent activity</p>
        </CardHeader>
        <CardContent className="pt-0">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] border-collapse text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  <th className="py-2.5 pr-4">Case ID</th>
                  <th className="py-2.5 pr-4">Distress Score</th>
                  <th className="py-2.5 pr-4">Risk Level</th>
                  <th className="py-2.5 pr-4">Trend</th>
                  <th className="py-2.5 pr-4">Last Interaction</th>
                  <th className="py-2.5 pr-4">Next Session</th>
                  <th className="py-2.5 pr-4">Escalation</th>
                  <th className="py-2.5 pr-0 text-right">Action</th>
                </tr>
              </thead>
              <tbody>
                {priorityQueue.map((c) => {
                  const TrendIcon = trendIcon[c.trend];
                  return (
                    <tr key={c.caseId} className="border-b border-border last:border-0">
                      <td className="py-3 pr-4 font-medium text-foreground">{c.caseId}</td>
                      <td className="py-3 pr-4 text-muted-foreground">{c.distress} / 100</td>
                      <td className="py-3 pr-4">
                        <Badge variant={riskBadgeVariant[c.risk]}>{c.risk}</Badge>
                      </td>
                      <td className="py-3 pr-4">
                        <TrendIcon
                          className={cn(
                            "h-4 w-4",
                            c.trend === "up" ? "text-danger" : c.trend === "down" ? "text-success" : "text-muted-foreground"
                          )}
                        />
                      </td>
                      <td className="py-3 pr-4 text-muted-foreground">{c.lastInteraction}</td>
                      <td className="py-3 pr-4 text-muted-foreground">{c.nextSession}</td>
                      <td className="py-3 pr-4">
                        <Badge variant={escalationBadgeVariant[c.escalation]}>{c.escalation}</Badge>
                      </td>
                      <td className="py-3 pr-0 text-right">
                        <Button variant="outline" size="sm" onClick={() => setSelectedCase(c.caseId)}>
                          View
                        </Button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Schedule + workload */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Today's Schedule</CardTitle>
            <p className="text-xs text-muted-foreground">Your counselling sessions for today</p>
          </CardHeader>
          <CardContent className="space-y-3">
            {schedule.map((s, i) => (
              <div key={i} className="flex items-center justify-between rounded-lg border border-border px-3 py-2.5 text-sm">
                <div className="flex items-center gap-3">
                  <span className="w-16 shrink-0 font-medium text-foreground">{s.time}</span>
                  <div>
                    <p className="font-medium text-foreground">{s.caseId}</p>
                    <p className="text-xs text-muted-foreground">{s.type}</p>
                  </div>
                </div>
                <Badge variant={s.done ? "success" : "default"}>{s.done ? "Completed" : "Upcoming"}</Badge>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Workload &amp; Availability</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <div className="mb-1.5 flex items-center justify-between text-sm">
                <span className="font-medium text-foreground">Active Caseload</span>
                <span className="text-muted-foreground">24 / 30</span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-secondary">
                <div className="h-full rounded-full bg-primary" style={{ width: "80%" }} />
              </div>
            </div>
            <div className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-success" />
                <span className="text-foreground">Status</span>
              </div>
              <span className="font-semibold text-foreground">Available</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2">
                <Briefcase className="h-4 w-4 text-muted-foreground" />
                <span className="text-foreground">Sessions this week</span>
              </div>
              <span className="font-semibold text-foreground">18</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* AI-assisted summary + explainability */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader className="flex-row items-center gap-2 space-y-0">
            <Sparkles className="h-4 w-4 text-primary" />
            <CardTitle>AI-Assisted Case Summary — {selectedCase}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            <p>
              This case shows a rising distress indicator over the past week, with well-being signals
              trending downward across text and voice check-ins. Engagement through the app remains
              consistent, though tone in recent responses suggests heightened anxiety.
            </p>
            <p>
              This is an AI-assisted assessment intended to support, not replace, your professional
              judgement. Please review before taking action.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Why This Case Was Flagged</CardTitle>
            <p className="text-xs text-muted-foreground">Explainable AI · contributing signals</p>
          </CardHeader>
          <CardContent className="space-y-2.5">
            {flagSignals.map((s, i) => (
              <div key={i} className="flex items-start gap-2.5 rounded-lg border border-border px-3 py-2.5 text-sm">
                <UserCheck className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                <span className="text-foreground">{s}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Counsellor Actions — {selectedCase}</CardTitle>
          <p className="text-xs text-muted-foreground">
            Legal decisions remain with the assigned authority; use these to log care and route recommendations
          </p>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
          <Button variant="outline" className="justify-start gap-2 h-auto py-3">
            <HeartHandshake className="h-4 w-4 text-primary" />
            Start Session
          </Button>
          <Button variant="outline" className="justify-start gap-2 h-auto py-3">
            <ClipboardList className="h-4 w-4 text-primary" />
            Add Session Note
          </Button>
          <Button variant="outline" className="justify-start gap-2 h-auto py-3">
            <CalendarClock className="h-4 w-4 text-primary" />
            Schedule Follow-up
          </Button>
          <Button variant="outline" className="justify-start gap-2 h-auto py-3">
            <PhoneCall className="h-4 w-4 text-primary" />
            Request Medical Review
          </Button>
          <Button variant="outline" className="justify-start gap-2 h-auto py-3 border-orange-500/40 text-orange-600 hover:bg-orange-500/10">
            <ScaleIcon className="h-4 w-4" />
            Escalate to Authority
          </Button>
          <Button variant="outline" className="justify-start gap-2 h-auto py-3">
            <ShieldAlert className="h-4 w-4 text-primary" />
            Recommend Witness Protection
          </Button>
          <Button variant="outline" className="justify-start gap-2 h-auto py-3">
            <Briefcase className="h-4 w-4 text-primary" />
            Recommend Relocation Support
          </Button>
          <Button variant="outline" className="justify-start gap-2 h-auto py-3">
            <HeartHandshake className="h-4 w-4 text-primary" />
            Recommend Financial Assistance
          </Button>
          <Button variant="outline" className="justify-start gap-2 h-auto py-3">
            <ScaleIcon className="h-4 w-4 text-primary" />
            Recommend Legal Aid
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
