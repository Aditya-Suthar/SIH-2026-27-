import { useState } from "react";
import { Link } from "react-router-dom";
import { MessageCircle } from "lucide-react";
import { useCounsellorMessages } from "../hooks/useCounsellorMessages";
import { CaseChat } from "../components/monitoring/CaseChat";
import { Card, CardContent } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
export default function CounsellorMessages() {
  const { conversations, selectedConversation, selectConversation, loading, error, refresh } = useCounsellorMessages();
  const [search, setSearch] = useState("");
  return <div className="space-y-5"><div><h1 className="text-2xl font-bold">Messages</h1><p className="mt-1 text-sm text-muted-foreground">Conversations with your assigned cases. Messages persist across sessions.</p></div>
    {error && <p role="alert" className="text-sm text-warning">{error} <Button variant="outline" onClick={() => void refresh()}>Retry</Button></p>}
    <div className="grid items-start gap-4 lg:grid-cols-[280px_minmax(0,1fr)]">
      <Card><CardContent className="space-y-2 pt-5"><Input aria-label="Search conversations" placeholder="Search case ID..." value={search} onChange={e => setSearch(e.target.value)} />
      {loading && <p className="p-3 text-sm">Loading conversations...</p>}
      {!loading && !conversations.length && <p className="p-3 text-sm text-muted-foreground">No assigned conversations yet.</p>}
      {conversations.filter(c => c.caseId.toLowerCase().includes(search.toLowerCase())).map(c => <button key={c.caseId} onClick={() => selectConversation(c.caseId)} className={`w-full rounded-lg border p-3 text-left text-sm ${selectedConversation?.caseId === c.caseId ? "border-primary bg-primary/5 text-primary" : "border-border"}`}><MessageCircle className="mr-2 inline h-4 w-4" />{c.caseId}</button>)}</CardContent></Card>
      {selectedConversation ? <div className="space-y-3"><Link className="text-sm text-primary hover:underline" to={`/cases/${encodeURIComponent(selectedConversation.caseId)}`}>Open case monitoring workspace →</Link><CaseChat key={selectedConversation.caseId} caseId={selectedConversation.caseId} /></div> : <Card><CardContent className="flex h-80 items-center justify-center text-sm text-muted-foreground">Select an assigned case to start.</CardContent></Card>}
    </div>
  </div>;
}
