import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, MessageCircle, Search, Send, ShieldAlert } from "lucide-react";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { cn } from "../../lib/utils";
import type { RiskLevel } from "../../types";
import { useCounsellorMessages } from "../hooks/useCounsellorMessages";

const riskBadgeVariant = {
  Critical: "danger", High: "orange", Moderate: "warning", Low: "success",
} as const satisfies Record<RiskLevel, string>;

function formatTime(value: string, compact = false) {
  const date = new Date(value);
  const today = new Date();
  const yesterday = new Date();
  yesterday.setDate(today.getDate() - 1);
  if (date.toDateString() === today.toDateString()) {
    return date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  }
  if (compact && date.toDateString() === yesterday.toDateString()) return "Yesterday";
  return date.toLocaleString([], {
    month: "short", day: "numeric", year: "numeric",
    ...(compact ? {} : { hour: "numeric", minute: "2-digit" } as const),
  });
}

export default function CounsellorMessages() {
  const { conversations, selectedConversation, messages, selectConversation, sendMessage } = useCounsellorMessages();
  const [search, setSearch] = useState("");
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [showMobileChat, setShowMobileChat] = useState(false);
  const chatBody = useRef<HTMLDivElement>(null);
  const selectedId = selectedConversation?.caseId;
  const draft = selectedId ? drafts[selectedId] ?? "" : "";
  const unreadCount = conversations.reduce((total, item) => total + item.unreadCount, 0);
  const filtered = conversations.filter((item) => item.caseId.toLowerCase().includes(search.trim().toLowerCase()));

  useEffect(() => {
    if (chatBody.current) chatBody.current.scrollTop = chatBody.current.scrollHeight;
  }, [selectedId, messages.length, showMobileChat]);

  function send() {
    if (!selectedId || !draft.trim()) return;
    sendMessage(draft);
    setDrafts((current) => ({ ...current, [selectedId]: "" }));
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">Messages</h1>
        <p className="mt-1 text-sm text-muted-foreground">Conversations with your assigned cases.</p>
        <p className="mt-1 text-xs text-muted-foreground">Demo conversations · Messages reset when you leave this page.</p>
      </div>

      <Card className="grid h-[min(720px,75dvh)] min-h-[420px] overflow-hidden md:grid-cols-[280px_minmax(0,1fr)] xl:grid-cols-[320px_minmax(0,1fr)]">
        <section aria-label="Conversations" className={cn("min-h-0 flex-col border-border md:flex md:border-r", showMobileChat ? "hidden" : "flex")}>
          <div className="space-y-4 border-b border-border p-5">
            <div className="flex items-center justify-between gap-2">
              <h2 className="text-sm font-semibold">Conversations</h2>
              {unreadCount > 0 && <Badge variant="primary" aria-label={`${unreadCount} unread messages`}>{unreadCount} unread</Badge>}
            </div>
            <div className="relative">
              <Search aria-hidden="true" className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
              <Input aria-label="Search conversations" placeholder="Search conversations..." className="pl-9" value={search} onChange={(event) => setSearch(event.target.value)} />
            </div>
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto p-2">
            {filtered.length === 0 && <p className="p-5 text-sm text-muted-foreground">{conversations.length ? "No conversations match your search." : "No assigned conversations yet."}</p>}
            {filtered.map((conversation) => (
              <button key={conversation.caseId} type="button" aria-pressed={selectedId === conversation.caseId}
                onClick={() => { selectConversation(conversation.caseId); setShowMobileChat(true); }}
                className={cn("mb-1 w-full rounded-lg p-3 text-left transition-colors hover:bg-secondary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring", selectedId === conversation.caseId && "bg-primary/10 hover:bg-primary/10")}>
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-semibold">{conversation.caseId}</span>
                  <Badge variant={riskBadgeVariant[conversation.riskLevel]}>{conversation.riskLevel}</Badge>
                </div>
                <p className="mt-2 truncate text-sm text-muted-foreground">{conversation.latestMessage?.content ?? "No messages yet"}</p>
                <div className="mt-2 flex items-center justify-between gap-2">
                  <span className="text-xs text-muted-foreground">{conversation.latestMessage && formatTime(conversation.latestMessage.createdAt, true)}</span>
                  {conversation.unreadCount > 0 && <Badge variant="primary" aria-label={`${conversation.unreadCount} unread messages`}>{conversation.unreadCount}</Badge>}
                </div>
              </button>
            ))}
          </div>
        </section>

        <section aria-label="Chat" className={cn("min-h-0 min-w-0 flex-col md:flex", showMobileChat ? "flex" : "hidden")}>
          {!selectedConversation ? (
            <div className="flex flex-1 flex-col items-center justify-center gap-3 p-5 text-center">
              <MessageCircle aria-hidden="true" className="h-9 w-9 text-muted-foreground" />
              <h2 className="text-sm font-semibold">Select a conversation</h2>
              <p className="text-sm text-muted-foreground">Choose an assigned case to view messages.</p>
            </div>
          ) : (
            <>
              <div className="space-y-3 border-b border-border p-5">
                <div className="flex flex-wrap items-center gap-3">
                  <Button variant="ghost" size="icon" aria-label="Back to conversations" className="md:hidden" onClick={() => setShowMobileChat(false)}><ArrowLeft className="h-4 w-4" /></Button>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <h2 className="text-sm font-semibold">{selectedConversation.caseId}</h2>
                      <Badge variant={riskBadgeVariant[selectedConversation.riskLevel]}>{selectedConversation.riskLevel}</Badge>
                    </div>
                    {selectedConversation.distressScore != null && <p className="mt-1 text-xs text-muted-foreground">Current distress score: {selectedConversation.distressScore}/100</p>}
                  </div>
                  <Button asChild variant="outline" size="sm"><Link to={`/cases/${encodeURIComponent(selectedConversation.caseId)}`}>View Case</Link></Button>
                </div>
                {selectedConversation.riskLevel === "Critical" && (
                  <div role="alert" className="flex items-center gap-2 rounded-lg border border-danger/20 bg-danger/10 px-3 py-2 text-sm text-danger">
                    <ShieldAlert aria-hidden="true" className="h-4 w-4 shrink-0" />
                    Critical risk — immediate review recommended
                  </div>
                )}
              </div>
              <div ref={chatBody} role="log" aria-label={`Messages for ${selectedConversation.caseId}`} aria-live="polite" aria-relevant="additions" tabIndex={0} className="min-h-0 flex-1 space-y-4 overflow-y-auto p-5">
                {messages.length === 0 && <p className="text-sm text-muted-foreground">No messages yet. Start the conversation below.</p>}
                {messages.map((message) => (
                  <div key={message.id} className={cn("flex", message.sender === "counsellor" ? "justify-end" : "justify-start")}>
                    <div className="max-w-[85%] sm:max-w-[75%]">
                      <p className="mb-1 text-xs text-muted-foreground">{message.sender === "counsellor" ? "You" : selectedConversation.caseId}</p>
                      <p className={cn("whitespace-pre-wrap break-words rounded-xl px-4 py-3 text-sm [overflow-wrap:anywhere]", message.sender === "counsellor" ? "bg-primary text-primary-foreground" : "bg-secondary text-secondary-foreground")}>{message.content}</p>
                      <time dateTime={message.createdAt} className="mt-1 block text-xs text-muted-foreground">{formatTime(message.createdAt)}</time>
                    </div>
                  </div>
                ))}
              </div>
              <form className="flex items-end gap-3 border-t border-border p-4" onSubmit={(event) => { event.preventDefault(); send(); }}>
                <textarea rows={2} aria-label="Type a message" placeholder="Type a message..." value={draft}
                  onChange={(event) => setDrafts((current) => ({ ...current, [selectedConversation.caseId]: event.target.value }))}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
                      event.preventDefault();
                      send();
                    }
                  }}
                  className="min-w-0 flex-1 resize-none rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" />
                <Button type="submit" disabled={!draft.trim()}><Send aria-hidden="true" className="h-4 w-4" />Send</Button>
              </form>
            </>
          )}
        </section>
      </Card>
    </div>
  );
}
