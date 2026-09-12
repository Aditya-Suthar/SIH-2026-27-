import { useCallback, useEffect, useRef, useState } from "react";
import { Send, MessageCircle, Mic, RefreshCw, Square, LoaderCircle } from "lucide-react";
import { api } from "../../lib/api";
import { API_BASE_URL } from "../../lib/config";
import { dateTime } from "../../lib/monitoring";
import { Button } from "../ui/button";
import { Card, CardHeader, CardContent, CardTitle } from "../ui/card";

type Message = { id: number; sender_role: string; content: string; created_at: string; client_message_id: string };
type MessagePage = { items: Message[]; has_more: boolean };
type VoiceResult = { transcript: string; language: string | null; language_probability: number | null };

const recordingMimeTypes = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/ogg", "audio/mp4"];

export function CaseChat({ caseId }: { caseId: string }) {
  const role = localStorage.getItem("role");
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState(""); const [error, setError] = useState("");
  const [loading, setLoading] = useState(true); const [sending, setSending] = useState(false);
  const [hasMore, setHasMore] = useState(false); const [olderLoading, setOlderLoading] = useState(false);
  const [recording, setRecording] = useState(false); const [transcribing, setTranscribing] = useState(false);
  const initialized = useRef(false); const alive = useRef(true); const busy = useRef(false);
  const retry = useRef<{ content: string; id: string } | null>(null);
  const body = useRef<HTMLDivElement>(null);
  const recorder = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const transcriptionRequest = useRef<AbortController | null>(null);
  const path = `/api/cases/${encodeURIComponent(caseId)}/messages`;
  const merge = useCallback((rows: Message[]) => setMessages(previous => [...new Map([...previous, ...rows].map(x => [x.id, x])).values()].sort((a,b) => a.id-b.id)), []);
  const refresh = useCallback(async () => {
    if (busy.current) return; busy.current = true;
    try {
      const page = await api<MessagePage>(path);
      if (alive.current) { merge(page.items); if (!initialized.current) setHasMore(page.has_more); initialized.current = true; setError(""); }
    } catch(e) { if (alive.current) setError(e instanceof Error ? e.message : "Could not load messages."); }
    finally { busy.current = false; if (alive.current) setLoading(false); }
  }, [path, merge]);
  useEffect(() => {
    alive.current = true; void refresh();
    const timer = setInterval(() => { if (!document.hidden) void refresh(); }, 5000);
    return () => { alive.current = false; clearInterval(timer); };
  }, [refresh]);
  useEffect(() => () => {
    transcriptionRequest.current?.abort();
    if (recorder.current?.state !== "inactive") recorder.current?.stop();
    stream.current?.getTracks().forEach(track => track.stop());
    stream.current = null;
  }, []);
  const lastId = messages.at(-1)?.id;
  useEffect(() => { if (body.current) body.current.scrollTop = body.current.scrollHeight; }, [lastId]);
  async function older() {
    setOlderLoading(true);
    try { const page = await api<MessagePage>(`${path}?before_id=${messages[0].id}`); merge(page.items); setHasMore(page.has_more); }
    catch(e) { setError(e instanceof Error ? e.message : "Could not load earlier messages."); }
    finally { setOlderLoading(false); }
  }
  async function send() {
    const content = draft.trim(); if (!content || sending) return;
    if (!retry.current || retry.current.content !== content) retry.current = { content, id: crypto.randomUUID() };
    setSending(true); setError("");
    try {
      const result = await api<{message: Message}>(path, { method: "POST", body: JSON.stringify({ content, client_message_id: retry.current.id }) });
      if (alive.current) { merge([result.message]); setDraft(""); retry.current = null; }
    } catch(e) { if (alive.current) setError(e instanceof Error ? e.message : "Message not confirmed. Retry to check its saved status."); }
    finally { if (alive.current) setSending(false); }
  }
  function stopTracks() {
    stream.current?.getTracks().forEach(track => track.stop());
    stream.current = null;
  }
  async function transcribe(audio: Blob, mimeType: string) {
    if (!audio.size) {
      if (alive.current) { setError("No audio was recorded. Please try again."); setTranscribing(false); }
      return;
    }
    const token = localStorage.getItem("access_token");
    if (!token) {
      if (alive.current) { setError("Please sign in again."); setTranscribing(false); }
      return;
    }
    const controller = new AbortController(); transcriptionRequest.current = controller;
    try {
      const response = await fetch(`${API_BASE_URL}/api/victim/voice/transcribe`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": mimeType },
        body: audio,
        signal: controller.signal,
      });
      const payload = await response.json().catch(() => null) as VoiceResult | { detail?: string } | null;
      if (!response.ok) {
        const detail = typeof payload === "object" && payload && "detail" in payload && typeof payload.detail === "string" ? payload.detail : "";
        const message = response.status === 401 ? "Your session expired. Please sign in again."
          : response.status === 403 ? "Voice transcription is available only to victims."
          : response.status === 413 ? "The recording is too large. Please make a shorter recording."
          : response.status === 415 ? "This browser recorded an unsupported audio format."
          : detail || "Could not convert voice to text. Please try again.";
        throw new Error(message);
      }
      const transcript = typeof payload === "object" && payload && "transcript" in payload && typeof payload.transcript === "string" ? payload.transcript.trim() : "";
      if (!transcript) throw new Error("No speech could be detected. Please try recording again.");
      if (alive.current) {
        setDraft(current => {
          const separator = current && !/\s$/.test(current) ? " " : "";
          const available = 4000 - current.length;
          const addition = `${separator}${transcript}`.slice(0, Math.max(0, available));
          return current + addition;
        });
        setError("");
      }
    } catch (e) {
      if (alive.current && !(e instanceof DOMException && e.name === "AbortError")) setError(e instanceof Error ? e.message : "Could not convert voice to text. Please try again.");
    } finally {
      if (transcriptionRequest.current === controller) transcriptionRequest.current = null;
      if (alive.current) setTranscribing(false);
    }
  }
  async function startRecording() {
    if (recording || transcribing || recorder.current) return;
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      setError("Voice recording is not supported by this browser.");
      return;
    }
    const mimeType = recordingMimeTypes.find(type => MediaRecorder.isTypeSupported(type));
    if (!mimeType) {
      setError("This browser does not support a recording format accepted by voice transcription.");
      return;
    }
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (!alive.current) { mediaStream.getTracks().forEach(track => track.stop()); return; }
      const mediaRecorder = new MediaRecorder(mediaStream, { mimeType });
      const chunks: BlobPart[] = [];
      stream.current = mediaStream; recorder.current = mediaRecorder;
      mediaRecorder.ondataavailable = event => { if (event.data.size) chunks.push(event.data); };
      mediaRecorder.onstop = () => {
        recorder.current = null; stopTracks();
        if (!alive.current) return;
        setRecording(false); setTranscribing(true);
        void transcribe(new Blob(chunks, { type: mimeType }), mimeType);
      };
      mediaRecorder.onerror = () => { if (alive.current) setError("Recording failed. Please try again."); };
      setError(""); setRecording(true); mediaRecorder.start();
    } catch (e) {
      stopTracks(); recorder.current = null;
      if (alive.current) {
        const denied = e instanceof DOMException && (e.name === "NotAllowedError" || e.name === "SecurityError");
        setError(denied ? "Microphone access was denied. Allow it in your browser settings to record a message." : "Could not start microphone recording. Please try again.");
      }
    }
  }
  function stopRecording() {
    if (recorder.current?.state === "recording") recorder.current.stop();
  }
  return <Card>
    <CardHeader className="flex-row items-start justify-between gap-2"><div><CardTitle><MessageCircle className="mr-2 inline h-4 w-4 text-primary" />{role === "victim" ? "Talk to your counsellor" : "Case conversation"}</CardTitle><p className="mt-1 text-xs text-muted-foreground">{caseId} · Human conversation · Refreshes every 5 seconds</p></div><Button aria-label="Refresh messages" variant="ghost" size="icon" onClick={() => void refresh()}><RefreshCw className="h-4 w-4" /></Button></CardHeader>
    <CardContent>
      {error && <p role="alert" className="mb-3 rounded-lg bg-warning/10 p-3 text-sm text-warning">{error}</p>}
      <div ref={body} className="h-80 space-y-3 overflow-y-auto rounded-lg border border-border bg-secondary/30 p-3" aria-label="Conversation history">
        {hasMore && <Button variant="outline" size="sm" disabled={olderLoading} onClick={() => void older()}>{olderLoading ? "Loading..." : "Load earlier messages"}</Button>}
        {loading && <p className="p-4 text-sm text-muted-foreground">Loading conversation...</p>}
        {!loading && !messages.length && !error && <div className="flex h-full flex-col items-center justify-center gap-2 text-center text-sm text-muted-foreground"><MessageCircle className="h-7 w-7" /><p>No messages yet.</p><p>Start a conversation with your {role === "victim" ? "counsellor" : "assigned victim"}.</p></div>}
        {messages.map(message => <div key={message.id} className={`flex ${message.sender_role === role ? "justify-end" : "justify-start"}`}><div className="max-w-[88%] sm:max-w-[80%]"><p className="mb-1 text-xs text-muted-foreground">{message.sender_role === role ? "You" : message.sender_role === "victim" ? caseId : "Counsellor"}</p><p className={`whitespace-pre-wrap break-words rounded-xl px-3 py-2 text-sm [overflow-wrap:anywhere] ${message.sender_role === role ? "bg-primary text-primary-foreground" : "border border-border bg-card"}`}>{message.content}</p><time className="mt-1 block text-[11px] text-muted-foreground">{dateTime(message.created_at)}</time></div></div>)}
      </div>
      <form className="mt-3 flex items-end gap-2" onSubmit={e => { e.preventDefault(); void send(); }}>
        <textarea aria-label="Message" rows={2} maxLength={4000} disabled={sending || transcribing} value={draft} onChange={e => setDraft(e.target.value)} placeholder="Write a message..." className="min-w-0 flex-1 resize-y rounded-lg border border-border bg-background p-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
        {role === "victim" && <Button type="button" variant={recording ? "default" : "outline"} size="icon" aria-label={recording ? "Stop recording" : "Record a voice message"} title={recording ? "Stop recording" : "Record a voice message"} disabled={sending || transcribing} onClick={() => recording ? stopRecording() : void startRecording()}>{transcribing ? <LoaderCircle className="h-4 w-4 animate-spin" /> : recording ? <Square className="h-4 w-4" /> : <Mic className="h-4 w-4" />}</Button>}
        <Button type="submit" disabled={sending || recording || transcribing || !draft.trim()}><Send className="h-4 w-4" />{sending ? "Sending..." : "Send"}</Button>
      </form>
      {role === "victim" && <p role="status" className="mt-2 text-xs text-muted-foreground">{recording ? "Recording... Select stop recording when you are finished." : transcribing ? "Converting voice to text..." : ""}</p>}
      <p className="mt-2 text-xs text-muted-foreground">Victim messages may be analyzed by cloud AI to support counsellor review. Messages are saved even if analysis is unavailable.</p>
    </CardContent>
  </Card>;
}
