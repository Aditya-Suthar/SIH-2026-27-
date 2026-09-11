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
  CheckCircle2,
  Lock,
  Mic,
  MessageCircle,
  MessageSquare,
  Phone,
  PhoneCall,
  Radio,
  ShieldAlert,
  ShieldCheck,
  Smartphone,
  Bot,
  Siren,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "../src/components/ui/card";
import { Badge } from "../src/components/ui/badge";
import { Button } from "../src/components/ui/button";
import { Input } from "../src/components/ui/input";
import { Avatar, AvatarFallback } from "../src/components/ui/avatar";
import { cn } from "../lib/utils";
type WellbeingMood = "Stable" | "Anxious" | "Distressed" | "Unsafe";
type RiskLevel = "Low" | "Moderate" | "High" | "Critical";
type SupportStatus = "Active" | "Available" | "Not Requested";
type VictimDashboardData = {
  caseId: string;
  riskLevel: RiskLevel;
  distressScore: number;
  assignedCounsellor: string;
  caseStage: string;
};


const caseStages = ["Complaint", "Investigation", "Trial", "Rehabilitation", "Compensation"] as const;

const moodOptions: { value: WellbeingMood; tone: string }[] = [
  { value: "Stable", tone: "border-success/40 text-success hover:bg-success/10" },
  { value: "Anxious", tone: "border-warning/40 text-warning hover:bg-warning/10" },
  { value: "Distressed", tone: "border-orange-500/40 text-orange-600 hover:bg-orange-500/10" },
  { value: "Unsafe", tone: "border-danger/40 text-danger hover:bg-danger/10" },
];

const riskBadgeVariant: Record<RiskLevel, "danger" | "orange" | "warning" | "success"> = {
  Critical: "danger",
  High: "orange",
  Moderate: "warning",
  Low: "success",
};


const trendData = [
  { label: "Week 1", wellbeing: 58 },
  { label: "Week 2", wellbeing: 52 },
  { label: "Week 3", wellbeing: 61 },
  { label: "Week 4", wellbeing: 55 },
  { label: "Week 5", wellbeing: 64 },
  { label: "Week 6", wellbeing: 67 },
];

const recentCheckIns = [
  { date: "Today, 9:12 AM", mood: "Stable" as WellbeingMood, channel: "App" },
  { date: "3 days ago", mood: "Anxious" as WellbeingMood, channel: "IVRS" },
  { date: "6 days ago", mood: "Stable" as WellbeingMood, channel: "Chatbot" },
  { date: "9 days ago", mood: "Distressed" as WellbeingMood, channel: "SMS" },
];

const moodDot: Record<WellbeingMood, string> = {
  Stable: "bg-success",
  Anxious: "bg-warning",
  Distressed: "bg-orange-500",
  Unsafe: "bg-danger",
};

const channels = [
  { label: "App", icon: Smartphone },
  { label: "SMS", icon: MessageSquare },
  { label: "IVRS", icon: PhoneCall },
  { label: "Chatbot", icon: Bot },
  { label: "Helpline", icon: Phone },
];

const supportStatuses: { label: string; status: SupportStatus }[] = [
  { label: "Counselling", status: "Active" },
  { label: "Medical Support", status: "Available" },
  { label: "Witness Protection", status: "Active" },
  { label: "Relocation Support", status: "Not Requested" },
  { label: "Financial Assistance", status: "Available" },
  { label: "Legal Aid", status: "Active" },
  { label: "Rehabilitation", status: "Available" },
];

const statusBadgeVariant: Record<SupportStatus, "success" | "primary" | "default"> = {
  Active: "success",
  Available: "primary",
  "Not Requested": "default",
};

export default function VictimDashboard() {
  const [showCounsellorChat, setShowCounsellorChat] = useState(false);
  const [chatMessage, setChatMessage] = useState(""); 
  const [chatMessages, setChatMessages] = useState<string[]>([]);  
  const [dashboardData, setDashboardData] =
  useState<VictimDashboardData | null>(null);

const currentStageIndex = dashboardData
  ? caseStages.indexOf(
      dashboardData.caseStage as typeof caseStages[number]
    )
  : 0;
  const [selectedMood, setSelectedMood] = useState<WellbeingMood | null>(null);
  const [note, setNote] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  
const [assessment, setAssessment] = useState({
  mood: 0,
  anxiety: 0,
  sleep: 0,
  hopelessness: 0,
  social_withdrawal: 0,
  self_harm_thoughts: 0,
});

const updateAssessment = (
  field: keyof typeof assessment,
  value: number
) => {
  setAssessment((prev) => ({
    ...prev,
    [field]: value,
  }));
};

const submitAssessment = async () => {
  try {
    const token = localStorage.getItem("access_token");

    if (!token) {
      alert("You are not logged in");
      return;
    }

    const response = await fetch(
      "http://127.0.0.1:8000/api/victim/assessment",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(assessment),
      }
    );

    if (!response.ok) {
      throw new Error(`Assessment failed: ${response.status}`);
    }

    const result = await response.json();
    setDashboardData((prev) =>
  prev
    ? {
        ...prev,
        distressScore: result.distressScore,
        riskLevel: result.riskLevel,
      }
    : prev
);

    alert(
      `Assessment submitted. Distress Score: ${result.distressScore}, Risk: ${result.riskLevel}`
    );
  } catch (error) {
    console.error(error);
    alert("Could not submit assessment");
  }
};


useEffect(() => {
  const fetchDashboard = async () => {
    try {
      const token = localStorage.getItem("access_token");

      if (!token) return;

      const response = await fetch(
        "http://127.0.0.1:8000/api/victim/dashboard",
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        console.error(
          "Failed to fetch victim dashboard:",
          response.status
        );
        return;
      }

      const data: VictimDashboardData =
        await response.json();

      setDashboardData(data);
    } catch (error) {
      console.error(
        "Could not fetch victim dashboard:",
        error
      );
    }
  };

  fetchDashboard();
}, []);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Hello, you're in a safe space
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Case ID <span className="font-medium text-foreground">{dashboardData?.caseId ?? "..."}</span> · Your details stay
            anonymised in every check-in
          </p>
        </div>
        <Badge variant="success" className="w-fit gap-1.5 px-3 py-1">
          <ShieldCheck className="h-3.5 w-3.5" />
          Identity Protected
        </Badge>
      </div>

      {/* Case stage tracker */}
      <Card>
        <CardHeader>
          <CardTitle>Your Case Journey</CardTitle>
          <p className="text-xs text-muted-foreground">Where your case currently stands</p>
        </CardHeader>
        <CardContent>
          <div className="flex items-center">
            {caseStages.map((stage, index) => {
              const isComplete = index < currentStageIndex;
              const isCurrent = index === currentStageIndex;
              return (
                <div key={stage} className="flex flex-1 items-center last:flex-none">
                  <div className="flex flex-col items-center gap-2 text-center">
                    <div
                      className={cn(
                        "flex h-8 w-8 items-center justify-center rounded-full border-2 text-xs font-semibold",
                        isComplete && "border-success bg-success text-success-foreground",
                        isCurrent && "border-primary bg-primary text-primary-foreground",
                        !isComplete && !isCurrent && "border-border bg-secondary text-muted-foreground"
                      )}
                    >
                      {isComplete ? <CheckCircle2 className="h-4 w-4" /> : index + 1}
                    </div>
                    <span
                      className={cn(
                        "w-20 text-xs font-medium",
                        isCurrent ? "text-foreground" : "text-muted-foreground"
                      )}
                    >
                      {stage}
                    </span>
                  </div>
                  {index < caseStages.length - 1 && (
                    <div
                      className={cn(
                        "mx-1 h-0.5 flex-1",
                        index < currentStageIndex ? "bg-success" : "bg-border"
                      )}
                    />
                  )}
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Status cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Card>
          <CardContent className="space-y-1.5 pt-5">
            <p className="text-xs font-medium text-muted-foreground">Dynamic Distress Score</p>
            <p className="text-2xl font-bold tracking-tight text-foreground">{dashboardData?.distressScore ?? 0} / 100</p>
            <p className="text-xs font-medium text-muted-foreground">Based on your recent check-ins</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="space-y-1.5 pt-5">
            <p className="text-xs font-medium text-muted-foreground">Current Risk Level</p>
            <div className="pt-0.5">
              <Badge
  variant={
    riskBadgeVariant[
      dashboardData?.riskLevel ?? "Low"
    ]
  }
>
  {dashboardData?.riskLevel ?? "Loading"}
</Badge>
            </div>
            <p className="text-xs font-medium text-muted-foreground">Reviewed by your counsellor</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="space-y-1.5 pt-5">
            <p className="text-xs font-medium text-muted-foreground">Next Scheduled Check-in</p>
            <p className="text-2xl font-bold tracking-tight text-foreground">Tomorrow</p>
            <p className="text-xs font-medium text-muted-foreground">6:00 PM via App</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-start justify-between gap-3 pt-5">
            <div className="space-y-1.5">
              <p className="text-xs font-medium text-muted-foreground">Assigned Counsellor</p>
              <p className="text-lg font-bold tracking-tight text-foreground">{dashboardData?.assignedCounsellor ?? "..."}</p>
              <p className="text-xs font-medium text-success">Available today</p>
            </div>
            <Avatar className="h-10 w-10">
              <AvatarFallback>MS</AvatarFallback>
            </Avatar>
          </CardContent>
        </Card>
      </div>

      {/* Trend + recent check-ins */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Your Well-being Over Time</CardTitle>
            <p className="text-xs text-muted-foreground">
              A gentle look at how you've been feeling in recent weeks
            </p>
          </CardHeader>
          <CardContent className="h-64 pt-2">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trendData} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                <defs>
                  <linearGradient id="wellbeingFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="hsl(152 55% 38%)" stopOpacity={0.28} />
                    <stop offset="100%" stopColor="hsl(152 55% 38%)" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(214 35% 89%)" vertical={false} />
                <XAxis
                  dataKey="label"
                  tickLine={false}
                  axisLine={false}
                  tick={{ fontSize: 12, fill: "hsl(215 18% 46%)" }}
                />
                <YAxis
                  tickLine={false}
                  axisLine={false}
                  tick={{ fontSize: 12, fill: "hsl(215 18% 46%)" }}
                  width={32}
                />
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
                  dataKey="wellbeing"
                  name="Well-being Signal"
                  stroke="hsl(152 55% 38%)"
                  strokeWidth={2}
                  fill="url(#wellbeingFill)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent Check-ins</CardTitle>
            <p className="text-xs text-muted-foreground">Your last few responses</p>
          </CardHeader>
          <CardContent className="space-y-3">
            {recentCheckIns.map((c, i) => (
              <div key={i} className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <span className={cn("h-2 w-2 rounded-full", moodDot[c.mood])} />
                  <div>
                    <p className="font-medium text-foreground">{c.mood}</p>
                    <p className="text-xs text-muted-foreground">{c.date}</p>
                  </div>
                </div>
                <span className="text-xs text-muted-foreground">{c.channel}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* Check-in card */}
      <Card>
        <CardHeader>
          <CardTitle>How are you feeling today?</CardTitle>
          <p className="text-xs text-muted-foreground">
            This is a private check-in. Answer only if you feel comfortable.
          </p>
        </CardHeader>

            <CardContent className="space-y-5">
              <div className="space-y-2">
                <p className="text-sm font-medium text-foreground">
                  How low or distressed has your mood felt today?
                </p>

                <div className="flex gap-2">
                  {[0, 1, 2, 3, 4].map((value) => (
                    <Button
                      key={value}
                      type="button"
                      variant={assessment.mood === value ? "default" : "outline"}
                      onClick={() => updateAssessment("mood", value)}
                    >
                      {value}
                    </Button>
                  ))}
                </div>

                <p className="text-xs text-muted-foreground">
                  0 = Not at all · 4 = Extremely
                </p>
              </div>
            <div className="space-y-2">
  <p className="text-sm font-medium text-foreground">
    How anxious or worried have you felt today?
  </p>

  <div className="flex gap-2">
    {[0, 1, 2, 3, 4].map((value) => (
      <Button
        key={value}
        type="button"
        variant={assessment.anxiety === value ? "default" : "outline"}
        onClick={() => updateAssessment("anxiety", value)}
      >
        {value}
      </Button>
    ))}
  </div>

  <p className="text-xs text-muted-foreground">
    0 = Not at all · 4 = Extremely
  </p>
</div>

<div className="space-y-2">
  <p className="text-sm font-medium text-foreground">
    How much has your sleep been disturbed recently?
  </p>

  <div className="flex gap-2">
    {[0, 1, 2, 3, 4].map((value) => (
      <Button
        key={value}
        type="button"
        variant={assessment.sleep === value ? "default" : "outline"}
        onClick={() => updateAssessment("sleep", value)}
      >
        {value}
      </Button>
    ))}
  </div>

  <p className="text-xs text-muted-foreground">
    0 = Not at all · 4 = Extremely
  </p>
</div>

<div className="space-y-2">
  <p className="text-sm font-medium text-foreground">
    How hopeless or discouraged have you felt recently?
  </p>

  <div className="flex gap-2">
    {[0, 1, 2, 3, 4].map((value) => (
      <Button
        key={value}
        type="button"
        variant={
          assessment.hopelessness === value ? "default" : "outline"
        }
        onClick={() => updateAssessment("hopelessness", value)}
      >
        {value}
      </Button>
    ))}
  </div>

  <p className="text-xs text-muted-foreground">
    0 = Not at all · 4 = Extremely
  </p>
</div>

<div className="space-y-2">
  <p className="text-sm font-medium text-foreground">
    How much have you avoided people or social interaction recently?
  </p>

  <div className="flex gap-2">
    {[0, 1, 2, 3, 4].map((value) => (
      <Button
        key={value}
        type="button"
        variant={
          assessment.social_withdrawal === value
            ? "default"
            : "outline"
        }
        onClick={() =>
          updateAssessment("social_withdrawal", value)
        }
      >
        {value}
      </Button>
    ))}
  </div>

  <p className="text-xs text-muted-foreground">
    0 = Not at all · 4 = Extremely
  </p>
</div>

<div className="space-y-2">
  <p className="text-sm font-medium text-foreground">
    Have you had thoughts of harming yourself recently?
  </p>

  <div className="flex gap-2">
    {[0, 1, 2, 3, 4].map((value) => (
      <Button
        key={value}
        type="button"
        variant={
          assessment.self_harm_thoughts === value
            ? "default"
            : "outline"
        }
        onClick={() =>
          updateAssessment("self_harm_thoughts", value)
        }
      >
        {value}
      </Button>
    ))}
  </div>

  <p className="text-xs text-muted-foreground">
    0 = Never · 1 = Rarely · 2 = Sometimes · 3 = Often · 4 = Very often
  </p>
</div>

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {moodOptions.map((mood) => (
              <button
                key={mood.value}
                onClick={() => setSelectedMood(mood.value)}
                className={cn(
                  "rounded-lg border bg-card px-3 py-3 text-sm font-medium transition-colors",
                  mood.tone,
                  selectedMood === mood.value && "ring-2 ring-ring"
                )}
              >
                {mood.value}
              </button>
            ))}
          </div>

          <div className="space-y-2">
            <label className="text-xs font-medium text-muted-foreground">
              Optional text check-in
            </label>
            <Input
              placeholder="Share anything you'd like your counsellor to know..."
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
          </div>

          <div className="flex items-center gap-4 rounded-lg border border-border bg-secondary/60 p-4">
            <button
              onClick={() => setIsRecording((v) => !v)}
              className={cn(
                "flex h-12 w-12 shrink-0 items-center justify-center rounded-full transition-colors",
                isRecording ? "bg-danger text-danger-foreground" : "bg-primary text-primary-foreground"
              )}
            >
              <Mic className="h-5 w-5" />
            </button>
            <div className="flex-1">
              <p className="text-sm font-medium text-foreground">Voice check-in</p>
              <p className="text-xs text-muted-foreground">
                {isRecording ? "Listening... tap again to stop" : "Tap to record how you're feeling"}
              </p>
            </div>
            <div className="flex items-end gap-0.5">
              {[6, 12, 8, 16, 10, 14, 7].map((h, i) => (
                <span
                  key={i}
                  className={cn(
                    "w-1 rounded-full",
                    isRecording ? "bg-primary" : "bg-border"
                  )}
                  style={{ height: h }}
                />
              ))}
            </div>
          </div>

          <Button
          className="w-full sm:w-auto"
          onClick={submitAssessment}
        >
          Submit Check-in
        </Button>
        </CardContent>
      </Card>

      {/* Channels + support status */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Ways You Can Reach Us</CardTitle>
            <p className="text-xs text-muted-foreground">Choose whatever feels easiest</p>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-3">
            {channels.map((c) => (
              <div
                key={c.label}
                className="flex items-center gap-2 rounded-lg border border-border px-3 py-2.5 text-sm"
              >
                <c.icon className="h-4 w-4 text-primary" />
                <span className="font-medium text-foreground">{c.label}</span>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Support &amp; Intervention Status</CardTitle>
            <p className="text-xs text-muted-foreground">What's in place for you right now</p>
          </CardHeader>
          <CardContent className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {supportStatuses.map((s) => (
              <div
                key={s.label}
                className="flex items-center justify-between rounded-lg border border-border px-3 py-2.5 text-sm"
              >
                <span className="font-medium text-foreground">{s.label}</span>
                <Badge variant={statusBadgeVariant[s.status]}>{s.status}</Badge>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* Quick actions */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Support Actions</CardTitle>
        </CardHeader>

        {showCounsellorChat && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Talk to your Counsellor</CardTitle>
                <p className="text-xs text-muted-foreground mt-1">
                  Assigned counsellor: {dashboardData?.assignedCounsellor ?? "Counsellor"}
                </p>
              </div>

              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowCounsellorChat(false)}
              >
                Close
              </Button>
            </div>
          </CardHeader>

          <CardContent className="space-y-4">
            <div className="rounded-lg border border-border bg-secondary/40 p-4 min-h-[150px] space-y-3">

              {/* Counsellor message */}
              <div className="flex justify-start">
                <div className="max-w-[75%] rounded-lg bg-card border border-border px-3 py-2">
                  <p className="text-sm">
                    Hello. I'm here to support you. How are you feeling today?
                  </p>
                </div>
              </div>

              {/* Victim messages */}
              {chatMessages.map((message, index) => (
                <div key={index} className="flex justify-end">
                  <div className="max-w-[75%] rounded-lg bg-primary text-primary-foreground px-3 py-2">
                    <p className="text-sm">
                      {message}
                    </p>
                  </div>
                </div>
              ))}

            </div>

            <div className="flex gap-2">
              <Input
                placeholder="Type your message..."
                value={chatMessage}
                onChange={(e) => setChatMessage(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    console.log(chatMessage);
                    setChatMessage("");
                  }
                }}
              />

              <Button
            onClick={() => {
              if (!chatMessage.trim()) return;

              setChatMessages((prev) => [...prev, chatMessage]);
              setChatMessage("");
            }}
          >
            Send
          </Button>
            </div>
          </CardContent>
        </Card>
      )}
        <CardContent className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <Button
            variant="outline"
            className="justify-start gap-2 h-auto py-3"
            onClick={() => setShowCounsellorChat(true)}
          >
            <MessageCircle className="h-4 w-4 text-primary" />
            Talk to Counsellor
          </Button>
          
          <Button variant="outline" className="justify-start gap-2 h-auto py-3">
            <Phone className="h-4 w-4 text-primary" />
            Request Call Back
          </Button>
          <Button variant="outline" className="justify-start gap-2 h-auto py-3 border-orange-500/40 text-orange-600 hover:bg-orange-500/10">
            <ShieldAlert className="h-4 w-4" />
            Report Threat / Intimidation
          </Button>
          <Button className="justify-start gap-2 h-auto py-3 bg-danger text-danger-foreground hover:bg-danger/90">
            <Siren className="h-4 w-4" />
            Need Immediate Support
          </Button>
        </CardContent>
      </Card>

      {/* Privacy & human review */}
      <Card className="border-dashed">
        <CardContent className="flex flex-col gap-2 pt-5 text-xs text-muted-foreground sm:flex-row sm:items-center sm:gap-6">
          <div className="flex items-center gap-2">
            <Lock className="h-3.5 w-3.5" />
            <span>Your responses are confidential and used only to support your case and well-being.</span>
          </div>
          <div className="flex items-center gap-2">
            <Radio className="h-3.5 w-3.5" />
            <span>Every flagged signal is reviewed by a trained professional before any action is taken.</span>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
