import {API_BASE_URL} from "../src/lib/config";
import {Link} from "react-router-dom";
import {api} from "../src/lib/api";
import {SupportRequests} from "../src/pages/Operations";
import {SessionList} from "../src/pages/Sessions";
import { useEffect, useRef, useState } from "react";
import {
  Lock,
  Mic,
  MessageCircle,
  Phone,
  Radio,
  ShieldAlert,
  ShieldCheck,
  Siren,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "../src/components/ui/card";
import { Badge } from "../src/components/ui/badge";
import { Button } from "../src/components/ui/button";
import { Input } from "../src/components/ui/input";
import { CaseChat } from "../src/components/monitoring/CaseChat";
import { VictimCheckIns } from "../src/components/monitoring/VictimCheckIns";
import { Avatar, AvatarFallback } from "../src/components/ui/avatar";
import { cn } from "../lib/utils";
type WellbeingMood = "Stable" | "Anxious" | "Distressed" | "Unsafe";
type RiskLevel = "Low" | "Moderate" | "High" | "Critical";
type VictimDashboardData = {
  caseId: string;
  riskLevel: RiskLevel;
  distressScore: number | null;
  assignedCounsellor: string;
  caseStage: string;
};



const moodOptions: { value: WellbeingMood; tone: string }[] = [
  { value: "Stable", tone: "border-success/40 text-success hover:bg-success/10" },
  { value: "Anxious", tone: "border-warning/40 text-warning hover:bg-warning/10" },
  { value: "Distressed", tone: "border-orange-500/40 text-orange-600 hover:bg-orange-500/10" },
  { value: "Unsafe", tone: "border-danger/40 text-danger hover:bg-danger/10" },
];

export default function VictimDashboard() {
  const [showCounsellorChat, setShowCounsellorChat] = useState(false);
  const [checkInRevision, setCheckInRevision] = useState(0);
  const [dashboardData, setDashboardData] =
  useState<VictimDashboardData | null>(null);

  const [selectedMood, setSelectedMood] = useState<WellbeingMood | null>(null);
  const [note, setNote] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [voiceNotice, setVoiceNotice] = useState("");
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const [dashboardError,setDashboardError]=useState("");
  const [requestNotice,setRequestNotice]=useState("");
  const [requestBusy,setRequestBusy]=useState(false);
  const [requestRevision,setRequestRevision]=useState(0);
  async function requestSupport(kind:string){setRequestBusy(true);try{await api("/api/support-requests",{method:"POST",body:JSON.stringify({kind})});setRequestNotice("Request saved for staff follow-up. This is not an emergency dispatch service.");setRequestRevision(v=>v+1);}catch(e){setRequestNotice((e as Error).message);}finally{setRequestBusy(false);}}
  
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

const transcribeRecording = async (audioBlob: Blob) => {
  setIsTranscribing(true);
  setVoiceNotice("Transcribing your recording locally...");
  try {
    const token = localStorage.getItem("access_token");
    if (!token) throw new Error("Please sign in again.");

    const response = await fetch(API_BASE_URL + "/api/victim/voice/transcribe", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": audioBlob.type || "audio/webm",
      },
      body: audioBlob,
    });

    const result = await response.json().catch(() => null);
    if (!response.ok) {
      const detail = typeof result?.detail === "string" ? result.detail : "Could not transcribe the recording.";
      throw new Error(detail);
    }

    const transcript = typeof result?.transcript === "string" ? result.transcript.trim() : "";
    if (!transcript) throw new Error("No speech could be detected. Please try again.");

    setNote(transcript);
    const language = typeof result?.language === "string" ? result.language.toUpperCase() : "speech";
    setVoiceNotice(`Transcribed ${language}. Review the text below, then submit your check-in.`);
  } catch (error) {
    setVoiceNotice(error instanceof Error ? error.message : "Could not transcribe the recording.");
  } finally {
    setIsTranscribing(false);
  }
};

const handleVoiceRecording = async () => {
  if (isTranscribing || isSubmitting) return;

  if (isRecording) {
    const recorder = mediaRecorderRef.current;
    if (recorder && recorder.state !== "inactive") recorder.stop();
    return;
  }

  try {
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      throw new Error("Voice recording is not supported in this browser.");
    }

    setVoiceNotice("Requesting microphone access...");
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
    });
    mediaStreamRef.current = stream;

    const preferredTypes = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/mp4"];
    const mimeType = preferredTypes.find((type) => MediaRecorder.isTypeSupported(type));
    const recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
    mediaRecorderRef.current = recorder;
    audioChunksRef.current = [];

    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) audioChunksRef.current.push(event.data);
    };

    recorder.onerror = () => {
      setVoiceNotice("Recording failed. Please try again.");
      setIsRecording(false);
      stream.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    };

    recorder.onstop = () => {
      setIsRecording(false);
      stream.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;

      const chunks = audioChunksRef.current;
      audioChunksRef.current = [];
      if (!chunks.length) {
        setVoiceNotice("No audio was captured. Please try again.");
        return;
      }
      const audioBlob = new Blob(chunks, { type: recorder.mimeType || "audio/webm" });
      void transcribeRecording(audioBlob);
    };

    recorder.start(1000);
    setIsRecording(true);
    setVoiceNotice("Recording... tap Stop when you are finished.");
  } catch (error) {
    mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
    mediaStreamRef.current = null;
    setIsRecording(false);
    setVoiceNotice(error instanceof Error ? error.message : "Could not access the microphone.");
  }
};

const submitAssessment = async () => {
  if (isSubmitting || isRecording || isTranscribing) return;
  setIsSubmitting(true);
  try {
    const token = localStorage.getItem("access_token");

    if (!token) {
      alert("You are not logged in");
      return;
    }

    const response = await fetch(
      API_BASE_URL + "/api/victim/assessment",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ ...assessment, note: note.trim() || null }),
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

    setNote("");
    setCheckInRevision(value => value + 1);
    const analysisNotice = result.ai_analysis?.status === "failed"
      ? " Your text was saved, but its AI analysis is unavailable."
      : result.ai_analysis?.status === "pending"
        ? " Your text was saved; its AI analysis is not complete."
        : "";
    alert(
      `Your check-in was saved.${analysisNotice}`
    );
  } catch (error) {
    console.error(error);
    alert("Could not submit assessment");
  } finally {
    setIsSubmitting(false);
  }
};


useEffect(() => () => {
  const recorder = mediaRecorderRef.current;
  if (recorder && recorder.state !== "inactive") {
    recorder.ondataavailable = null;
    recorder.onstop = null;
    recorder.onerror = null;
    recorder.stop();
  }
  mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
}, []);

useEffect(()=>{let active=true;async function load(){try{await api('/api/victim/case',{method:'POST'});const data=await api<VictimDashboardData>('/api/victim/dashboard');if(active)setDashboardData(data);}catch(e){if(active)setDashboardError((e as Error).message);}}void load();return()=>{active=false};},[]);
  if(!dashboardData)return <Card><CardContent className="pt-6"><p role="status">{dashboardError||'Loading your support case...'}</p>{dashboardError&&<Button onClick={()=>location.reload()}>Retry</Button>}</CardContent></Card>;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Hello, you're in a safe space
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Case ID <span className="font-medium text-foreground">{dashboardData?.caseId ?? "..."}</span> · Available to your authorized support team
          </p>
        </div>
        <Badge variant="success" className="w-fit gap-1.5 px-3 py-1">
          <ShieldCheck className="h-3.5 w-3.5" />
          Private support
        </Badge>
      </div>

      <Card><CardHeader><CardTitle>Your case status</CardTitle></CardHeader><CardContent><p>{dashboardData.caseStage}</p><p className="mt-2 text-xs text-muted-foreground">Updated by authorized staff.</p></CardContent></Card>
      {/* Support status; internal AI prioritization stays in professional views. */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Card>
          <CardContent className="space-y-1.5 pt-5">
            <p className="text-xs font-medium text-muted-foreground">Your appointments</p>
            <Link to="/sessions" className="text-lg font-semibold text-primary">Request or view an appointment →</Link>
            <p className="text-xs text-muted-foreground">Choose a time that works for you.</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-start justify-between gap-3 pt-5">
            <div className="space-y-1.5">
              <p className="text-xs font-medium text-muted-foreground">Assigned Counsellor</p>
              <p className="text-lg font-bold tracking-tight text-foreground">{dashboardData?.assignedCounsellor ?? "..."}</p>
              <p className="text-xs font-medium text-success">Contact through your case conversation</p>
            </div>
            <Avatar className="h-10 w-10">
              <AvatarFallback>CS</AvatarFallback>
            </Avatar>
          </CardContent>
        </Card>
      </div>

      <VictimCheckIns revision={checkInRevision} />

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
              maxLength={4000}
              disabled={isSubmitting || isRecording || isTranscribing}
              onChange={(e) => setNote(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              Optional text is analyzed by cloud AI to support counsellor review, not to provide a diagnosis.
            </p>
          </div>

          <div className="flex flex-col gap-3 rounded-lg border border-border bg-secondary/40 p-4 sm:flex-row sm:items-center">
            <Button
              type="button"
              variant="outline"
              className={cn("gap-2", isRecording && "border-danger bg-danger text-danger-foreground hover:bg-danger/90")}
              onClick={() => void handleVoiceRecording()}
              disabled={isTranscribing || isSubmitting}
            >
              <Mic className="h-4 w-4" />
              {isRecording ? "Stop recording" : isTranscribing ? "Transcribing..." : "Record voice"}
            </Button>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-foreground">Voice check-in</p>
              <p role="status" className="text-xs text-muted-foreground">
                {voiceNotice || "Record a message, review the transcript, then submit it with your check-in."}
              </p>
            </div>
          </div>
          <p className="text-xs text-muted-foreground">
            Audio is sent to the Sahas backend for local Whisper transcription, used only to produce the editable transcript, and not stored by the voice endpoint.
          </p>

          <Button
          className="w-full sm:w-auto"
          onClick={submitAssessment}
          disabled={isSubmitting || isRecording || isTranscribing}
        >
          {isSubmitting ? "Submitting..." : "Submit Check-in"}
        </Button>
        </CardContent>
      </Card>

      <SupportRequests key={requestRevision}/><SessionList/>

      {/* Quick actions */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Support Actions</CardTitle>
        </CardHeader>

        {showCounsellorChat && dashboardData?.caseId && <div className="px-5 pb-5"><CaseChat key={dashboardData.caseId} caseId={dashboardData.caseId} /><Button className="mt-2" variant="outline" onClick={() => setShowCounsellorChat(false)}>Close conversation</Button></div>}
        <CardContent className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <Button
            variant="outline"
            className="justify-start gap-2 h-auto py-3"
            onClick={() => setShowCounsellorChat(true)}
          >
            <MessageCircle className="h-4 w-4 text-primary" />
            Talk to Counsellor
          </Button>
          
          <Button disabled={requestBusy} onClick={()=>void requestSupport("Callback")} variant="outline" className="justify-start gap-2 h-auto py-3">
            <Phone className="h-4 w-4 text-primary" />
            Request Call Back
          </Button>
          <Button disabled={requestBusy} onClick={()=>void requestSupport("Threat report")} variant="outline" className="justify-start gap-2 h-auto py-3 border-orange-500/40 text-orange-600 hover:bg-orange-500/10">
            <ShieldAlert className="h-4 w-4" />
            Report Threat / Intimidation
          </Button>
          <Button disabled={requestBusy} onClick={()=>setRequestNotice("If you are in immediate danger, contact your local emergency services or a trusted person nearby. This app cannot dispatch emergency help. Use the support request button for staff follow-up.")} className="justify-start gap-2 h-auto py-3 bg-danger text-danger-foreground hover:bg-danger/90">
            <Siren className="h-4 w-4" />
            Need Immediate Support
          </Button>
        </CardContent>
      </Card>

      {requestNotice&&<p role="status" className="rounded-lg border p-4 text-sm">{requestNotice}</p>}
      {/* Privacy & human review */}
      <Card className="border-dashed">
        <CardContent className="flex flex-col gap-2 pt-5 text-xs text-muted-foreground sm:flex-row sm:items-center sm:gap-6">
          <div className="flex items-center gap-2">
            <Lock className="h-3.5 w-3.5" />
            <span>Your responses are available to authorized support staff; optional text may be processed by cloud AI.</span>
          </div>
          <div className="flex items-center gap-2">
            <Radio className="h-3.5 w-3.5" />
            <span>Counsellors review signals and decide appropriate follow-up.</span>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
