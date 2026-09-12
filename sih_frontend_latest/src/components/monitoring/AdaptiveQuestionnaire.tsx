import { useCallback, useEffect, useMemo, useState } from "react";
import { API_BASE_URL } from "../../lib/config";
import { Button } from "../ui/button";

type Question = {
  id: string; text: string; domain: string; response_type: string;
  critical: boolean; reverse_scored: boolean; options: string[];
};
type Questionnaire = {
  questionnaire_id: string; questionnaire_version: string; age_group: string;
  age_group_name: string; questions: Question[]; notice: string;
};
type Result = {
  questionnaire_score: number; domain_scores: Record<string, number>;
  safety_flags: string[]; risk_level: string; triggered_followups: Question[];
  complete: boolean; ai_analysis?: { status: string };
};

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(API_BASE_URL + path, { ...options, headers: {
    "Content-Type": "application/json",
    Authorization: `Bearer ${localStorage.getItem("access_token") || ""}`,
    ...options.headers,
  }});
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(typeof body?.detail === "string" ? body.detail : "Could not load the questionnaire.");
  return body as T;
}

export function AdaptiveQuestionnaire({ note, disabled, onSaved }: {
  note: string; disabled: boolean;
  onSaved: (result: Result) => void;
}) {
  const [questionnaire, setQuestionnaire] = useState<Questionnaire | null>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [phase, setPhase] = useState<"initial" | "followup" | "complete">("initial");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<Result | null>(null);

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const data = await request<Questionnaire>("/api/victim/questionnaire");
      setQuestionnaire(data); setQuestions(data.questions); setAnswers({}); setPhase("initial");
    } catch (e) { setError(e instanceof Error ? e.message : "Could not load the questionnaire."); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void load(); }, [load]);

  const answered = useMemo(() => questions.filter(q => answers[q.id] !== undefined).length, [questions, answers]);
  async function submit() {
    if (!questionnaire || busy) return;
    const unansweredCore = phase === "initial" && questions.some(q => ["Q001","Q006","Q009","Q057","Q064","Q073"].includes(q.id) && answers[q.id] === undefined);
    if (unansweredCore) { setError("Please answer the six core wellbeing and safety questions."); return; }
    setBusy(true); setError("");
    try {
      const data = await request<Result>("/api/victim/questionnaire/submit", {
        method: "POST", body: JSON.stringify({ questionnaire_id: questionnaire.questionnaire_id,
          answers, note: phase === "initial" ? (note.trim() || null) : null }),
      });
      setResult(data); onSaved(data);
      if (!data.complete && data.triggered_followups.length) {
        setQuestions(data.triggered_followups); setAnswers({}); setPhase("followup");
      } else setPhase("complete");
    } catch (e) { setError(e instanceof Error ? e.message : "Could not save the questionnaire."); }
    finally { setBusy(false); }
  }

  async function answerQuestion(question: Question, value: number) {
    setAnswers(old => ({...old,[question.id]:value}));
    const concerning = question.critical && (question.reverse_scored ? value === 0 : value > 0);
    if (!concerning || !questionnaire) return;
    try {
      await request("/api/victim/questionnaire/safety-signal", {method:"POST", body:JSON.stringify({
        questionnaire_id:questionnaire.questionnaire_id, question_id:question.id, answer:value,
      })});
    } catch (e) {
      setError(e instanceof Error ? e.message : "The safety response could not be recorded. Please submit again.");
    }
  }

  if (loading) return <p role="status" className="text-sm text-muted-foreground">Preparing a short check-in for you…</p>;
  if (error && !questionnaire) return <div className="space-y-3"><p role="alert" className="text-sm text-danger">{error}</p><Button type="button" variant="outline" onClick={() => void load()}>Retry</Button></div>;
  if (phase === "complete" && result) return <div className="rounded-lg border border-success/30 bg-success/5 p-4"><p className="font-medium">Check-in saved</p><p className="mt-1 text-sm text-muted-foreground">Your responses were recorded for support monitoring. This is not a diagnosis.</p><Button type="button" className="mt-3" variant="outline" onClick={() => { setQuestionnaire(null); setResult(null); void load(); }}>Start another check-in</Button></div>;

  return <div className="space-y-5">
    <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
      <span>{phase === "followup" ? "A few important follow-ups" : `${questionnaire?.age_group_name} wording · version ${questionnaire?.questionnaire_version}`}</span>
      <span>{answered} of {questions.length} answered</span>
    </div>
    <div className="h-2 overflow-hidden rounded-full bg-secondary" aria-hidden="true"><div className="h-full bg-primary transition-all" style={{width:`${questions.length ? answered/questions.length*100 : 0}%`}} /></div>
    {questions.map((question, index) => <fieldset key={question.id} className="space-y-3 rounded-lg border p-4">
      <legend className="px-1 text-sm font-medium"><span className="mr-2 text-muted-foreground">{index+1}.</span>{question.text}{question.critical && <span className="sr-only"> Safety question</span>}</legend>
      <div className={`grid gap-2 ${question.options.length === 2 ? "grid-cols-2" : "grid-cols-2 sm:grid-cols-5"}`}>
        {question.options.map((option, value) => <Button key={option} type="button" size="sm" variant={answers[question.id] === value ? "default" : "outline"} disabled={busy || disabled} onClick={() => void answerQuestion(question,value)}>{option}</Button>)}
      </div>
      {!question.critical && <button type="button" className="text-xs text-muted-foreground underline" onClick={() => setAnswers(old => { const next={...old}; delete next[question.id]; return next; })}>Skip this optional question</button>}
    </fieldset>)}
    {error && <p role="alert" className="text-sm text-danger">{error}</p>}
    <Button type="button" className="w-full sm:w-auto" disabled={busy || disabled} onClick={() => void submit()}>{busy ? "Saving…" : phase === "followup" ? "Complete follow-ups" : "Submit Check-in"}</Button>
    <p className="text-xs text-muted-foreground">{questionnaire?.notice}</p>
  </div>;
}
