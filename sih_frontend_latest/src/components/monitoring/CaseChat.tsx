import { useCallback, useEffect, useRef, useState } from "react";
import { Send, MessageCircle, RefreshCw } from "lucide-react";
import { api } from "../../lib/api";
import { dateTime } from "../../lib/monitoring";
import { Button } from "../ui/button";
import { Card, CardHeader, CardContent, CardTitle } from "../ui/card";

type Message = { id: number; sender_role: string; content: string; created_at: string; client_message_id: string };
type MessagePage = { items: Message[]; has_more: boolean };
export function CaseChat({ caseId }: { caseId: string }) {
  const role = localStorage.getItem("role");
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState(""); const [error, setError] = useState("");
  const [loading, setLoading] = useState(true); const [sending, setSending] = useState(false);
  const [hasMore, setHasMore] = useState(false); const [olderLoading, setOlderLoading] = useState(false);
  const initialized = useRef(false); const alive = useRef(true); const busy = useRef(false);
  const retry = useRef<{ content: string; id: string } | null>(null);
  const body = useRef<HTMLDivElement>(null);
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
        <textarea aria-label="Message" rows={2} maxLength={4000} disabled={sending} value={draft} onChange={e => setDraft(e.target.value)} placeholder="Write a message..." className="min-w-0 flex-1 resize-y rounded-lg border border-border bg-background p-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
        <Button type="submit" disabled={sending || !draft.trim()}><Send className="h-4 w-4" />{sending ? "Sending..." : "Send"}</Button>
      </form>
      <p className="mt-2 text-xs text-muted-foreground">Victim messages may be analyzed by cloud AI to support counsellor review. Messages are saved even if analysis is unavailable.</p>
    </CardContent>
  </Card>;
}
