import { useMemo, useState } from "react";
import type { FormEvent } from "react";
import {
  CalendarDays,
  CheckCircle2,
  Clock3,
  History,
  Plus,
  UserRound,
  Video,
  X,
} from "lucide-react";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";

type SessionStatus = "Upcoming" | "Completed" | "Cancelled" | "Rescheduled";

type SupportSession = {
  id: number;
  person: string;
  date: string;
  time: string;
  type: string;
  duration: string;
  status: SessionStatus;
  reason?: string;
};

const initialSessions: SupportSession[] = [
  {
    id: 1,
    person: "Dr. Meera Sharma",
    date: "12 Sep 2026",
    time: "4:30 PM",
    type: "Counselling Session",
    duration: "45 min",
    status: "Upcoming",
    reason: "Weekly emotional well-being check-in",
  },
  {
    id: 2,
    person: "Ananya Verma",
    date: "16 Sep 2026",
    time: "11:00 AM",
    type: "Follow-up",
    duration: "30 min",
    status: "Rescheduled",
    reason: "Follow-up after the previous support session",
  },
  {
    id: 3,
    person: "Dr. Meera Sharma",
    date: "04 Sep 2026",
    time: "3:00 PM",
    type: "Counselling Session",
    duration: "45 min",
    status: "Completed",
  },
  {
    id: 4,
    person: "Ananya Verma",
    date: "28 Aug 2026",
    time: "5:15 PM",
    type: "Case Review",
    duration: "30 min",
    status: "Completed",
  },
];

const statusClasses: Record<SessionStatus, string> = {
  Upcoming: "border-primary/20 bg-primary/10 text-primary",
  Completed: "border-success/20 bg-success/10 text-success",
  Cancelled: "border-danger/20 bg-danger/10 text-danger",
  Rescheduled: "border-warning/20 bg-warning/10 text-warning",
};

export default function Sessions() {
  const [sessions, setSessions] = useState(initialSessions);
  const [showSchedule, setShowSchedule] = useState(false);
  const [selectedSession, setSelectedSession] = useState<SupportSession | null>(null);
  const [sessionType, setSessionType] = useState("Counselling Session");
  const [preferredDate, setPreferredDate] = useState("");
  const [preferredTime, setPreferredTime] = useState("");
  const [reason, setReason] = useState("");
  const [formError, setFormError] = useState("");
  const [notice, setNotice] = useState("");
  const role = localStorage.getItem("role");

  const upcoming = useMemo(
    () => sessions.filter((session) => session.status === "Upcoming" || session.status === "Rescheduled"),
    [sessions]
  );
  const history = useMemo(
    () => sessions.filter((session) => session.status === "Completed" || session.status === "Cancelled"),
    [sessions]
  );

  function scheduleSession(event: FormEvent) {
    event.preventDefault();
    if (!preferredDate || !preferredTime) {
      setFormError("Choose both a preferred date and time.");
      return;
    }

    const date = new Date(`${preferredDate}T00:00:00`);
    const dateLabel = Number.isNaN(date.getTime())
      ? preferredDate
      : date.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });

    const [hoursText, minutesText] = preferredTime.split(":");
    const hours = Number(hoursText);
    const minutes = Number(minutesText);
    const suffix = hours >= 12 ? "PM" : "AM";
    const displayHours = hours % 12 || 12;
    const timeLabel = `${displayHours}:${String(minutes).padStart(2, "0")} ${suffix}`;

    setSessions((current) => [
      {
        id: Date.now(),
        person: role === "counsellor" ? "Victim assignment pending" : role === "authority" ? "Participant assignment pending" : "Counsellor assignment pending",
        date: dateLabel,
        time: timeLabel,
        type: sessionType,
        duration: sessionType === "Emergency Support" ? "30 min" : "45 min",
        status: "Upcoming",
        reason: reason.trim() || undefined,
      },
      ...current,
    ]);

    setPreferredDate("");
    setPreferredTime("");
    setReason("");
    setSessionType("Counselling Session");
    setFormError("");
    setShowSchedule(false);
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">Support planning</p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-foreground sm:text-3xl">Sessions</h1>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            Keep upcoming support appointments and recent session history in one calm, easy-to-scan place.
          </p>
        </div>
        <Button onClick={() => setShowSchedule(true)} className="sm:self-center">
          <Plus className="h-4 w-4" /> Schedule Session
        </Button>
      </div>

      {notice && (
        <div className="flex items-start justify-between gap-3 rounded-xl border border-primary/20 bg-primary/5 px-4 py-3 text-sm text-foreground">
          <p>{notice}</p>
          <button type="button" onClick={() => setNotice("")} className="text-muted-foreground hover:text-foreground" aria-label="Dismiss notice"><X className="h-4 w-4" /></button>
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardContent className="flex items-center gap-4 p-5">
            <div className="rounded-xl bg-primary/10 p-3 text-primary"><CalendarDays className="h-5 w-5" /></div>
            <div><p className="text-2xl font-bold">{upcoming.length}</p><p className="text-xs text-muted-foreground">Upcoming sessions</p></div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-4 p-5">
            <div className="rounded-xl bg-success/10 p-3 text-success"><CheckCircle2 className="h-5 w-5" /></div>
            <div><p className="text-2xl font-bold">{history.filter((s) => s.status === "Completed").length}</p><p className="text-xs text-muted-foreground">Completed recently</p></div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-4 p-5">
            <div className="rounded-xl bg-secondary p-3 text-secondary-foreground"><Clock3 className="h-5 w-5" /></div>
            <div><p className="text-2xl font-bold">45</p><p className="text-xs text-muted-foreground">Typical minutes</p></div>
          </CardContent>
        </Card>
      </div>

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <div><h2 className="text-lg font-semibold">Upcoming sessions</h2><p className="text-sm text-muted-foreground">Your next scheduled support touchpoints.</p></div>
        </div>

        {upcoming.length === 0 ? (
          <Card><CardContent className="flex flex-col items-center gap-3 py-12 text-center"><CalendarDays className="h-9 w-9 text-muted-foreground" /><div><p className="font-semibold">Nothing scheduled yet</p><p className="mt-1 text-sm text-muted-foreground">Schedule a session whenever you are ready.</p></div><Button onClick={() => setShowSchedule(true)} variant="outline">Schedule Session</Button></CardContent></Card>
        ) : (
          <div className="grid gap-4 xl:grid-cols-2">
            {upcoming.map((session) => (
              <Card key={session.id} className="overflow-hidden transition-shadow hover:shadow-md">
                <CardContent className="p-5">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex min-w-0 items-start gap-3">
                      <div className="rounded-xl bg-primary/10 p-2.5 text-primary"><UserRound className="h-5 w-5" /></div>
                      <div className="min-w-0"><p className="font-semibold text-foreground">{session.type}</p><p className="mt-0.5 truncate text-sm text-muted-foreground">{session.person}</p></div>
                    </div>
                    <Badge variant="outline" className={statusClasses[session.status]}>{session.status}</Badge>
                  </div>
                  <div className="mt-5 grid grid-cols-2 gap-3 rounded-xl bg-muted/60 p-4 text-sm">
                    <div><p className="text-xs text-muted-foreground">Date</p><p className="mt-1 font-medium">{session.date}</p></div>
                    <div><p className="text-xs text-muted-foreground">Time</p><p className="mt-1 font-medium">{session.time}</p></div>
                    <div><p className="text-xs text-muted-foreground">Duration</p><p className="mt-1 font-medium">{session.duration}</p></div>
                    <div><p className="text-xs text-muted-foreground">Format</p><p className="mt-1 font-medium">Secure video / call</p></div>
                  </div>
                  <div className="mt-4 flex flex-wrap gap-2">
                    <Button size="sm" onClick={() => setNotice("Demo mode: the secure join link will be issued when session backend/video integration is connected.")}><Video className="h-4 w-4" /> Join</Button>
                    <Button size="sm" variant="outline" onClick={() => setSelectedSession(session)}>View Details</Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </section>

      <Card>
        <CardHeader className="flex-row items-center gap-3">
          <div className="rounded-lg bg-secondary p-2 text-secondary-foreground"><History className="h-4 w-4" /></div>
          <div><CardTitle className="text-base">Session history</CardTitle><p className="mt-1 text-xs text-muted-foreground">A simple record of previous support sessions. Private notes are not shown here.</p></div>
        </CardHeader>
        <CardContent>
          <div className="divide-y divide-border">
            {history.map((session) => (
              <button key={session.id} type="button" onClick={() => setSelectedSession(session)} className="grid w-full gap-2 py-4 text-left transition-colors hover:bg-muted/40 sm:grid-cols-[1.3fr_1fr_1fr_auto] sm:items-center sm:px-2">
                <div><p className="text-sm font-medium">{session.type}</p><p className="text-xs text-muted-foreground">{session.person}</p></div>
                <p className="text-sm text-muted-foreground">{session.date}</p>
                <p className="text-sm text-muted-foreground">{session.duration}</p>
                <Badge variant="outline" className={statusClasses[session.status]}>{session.status}</Badge>
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      <div className="rounded-xl border border-dashed border-primary/30 bg-primary/5 px-4 py-3 text-xs text-muted-foreground">
        Demo mode: scheduling on this page is stored only in the current browser session. Backend persistence will be connected later.
      </div>

      {showSchedule && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onMouseDown={(e) => e.target === e.currentTarget && setShowSchedule(false)}>
          <Card className="w-full max-w-lg shadow-xl">
            <CardHeader className="flex-row items-center justify-between">
              <div><CardTitle className="text-lg">Schedule a session</CardTitle><p className="mt-1 text-xs text-muted-foreground">Share your preferred time. A counsellor can be assigned later.</p></div>
              <Button size="icon" variant="ghost" onClick={() => setShowSchedule(false)} aria-label="Close"><X className="h-4 w-4" /></Button>
            </CardHeader>
            <CardContent>
              <form onSubmit={scheduleSession} className="space-y-4">
                <label className="block text-sm font-medium">Session type
                  <select value={sessionType} onChange={(e) => setSessionType(e.target.value)} className="mt-1.5 flex h-10 w-full rounded-lg border border-border bg-card px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring">
                    <option>Counselling Session</option><option>Follow-up</option><option>Case Review</option><option>Emergency Support</option>
                  </select>
                </label>
                <div className="grid gap-4 sm:grid-cols-2">
                  <label className="block text-sm font-medium">Preferred date<Input className="mt-1.5" type="date" value={preferredDate} onChange={(e) => setPreferredDate(e.target.value)} /></label>
                  <label className="block text-sm font-medium">Preferred time<Input className="mt-1.5" type="time" value={preferredTime} onChange={(e) => setPreferredTime(e.target.value)} /></label>
                </div>
                <label className="block text-sm font-medium">Short reason <span className="font-normal text-muted-foreground">(optional)</span>
                  <textarea value={reason} onChange={(e) => setReason(e.target.value)} maxLength={240} rows={4} placeholder="Anything you want the support team to know before the session..." className="mt-1.5 w-full resize-none rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring" />
                </label>
                {formError && <p className="text-sm text-danger">{formError}</p>}
                <div className="flex justify-end gap-2 pt-1"><Button type="button" variant="outline" onClick={() => setShowSchedule(false)}>Cancel</Button><Button type="submit">Schedule Session</Button></div>
              </form>
            </CardContent>
          </Card>
        </div>
      )}

      {selectedSession && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onMouseDown={(e) => e.target === e.currentTarget && setSelectedSession(null)}>
          <Card className="w-full max-w-md shadow-xl">
            <CardHeader className="flex-row items-start justify-between"><div><CardTitle className="text-lg">{selectedSession.type}</CardTitle><p className="mt-1 text-xs text-muted-foreground">Session details</p></div><Button size="icon" variant="ghost" onClick={() => setSelectedSession(null)}><X className="h-4 w-4" /></Button></CardHeader>
            <CardContent className="space-y-4 text-sm">
              <div className="grid grid-cols-2 gap-3 rounded-xl bg-muted/60 p-4"><div><p className="text-xs text-muted-foreground">With</p><p className="mt-1 font-medium">{selectedSession.person}</p></div><div><p className="text-xs text-muted-foreground">Status</p><Badge variant="outline" className={`mt-1 ${statusClasses[selectedSession.status]}`}>{selectedSession.status}</Badge></div><div><p className="text-xs text-muted-foreground">Date</p><p className="mt-1 font-medium">{selectedSession.date}</p></div><div><p className="text-xs text-muted-foreground">Time</p><p className="mt-1 font-medium">{selectedSession.time}</p></div></div>
              {selectedSession.reason && <div><p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Reason</p><p className="mt-1.5 leading-6">{selectedSession.reason}</p></div>}
              <p className="text-xs text-muted-foreground">Sensitive counselling notes are intentionally not displayed in this overview.</p>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
