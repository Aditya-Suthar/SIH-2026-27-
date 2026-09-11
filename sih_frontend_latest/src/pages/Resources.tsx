import { useMemo, useState } from "react";
import {
  Bookmark,
  BookmarkCheck,
  Brain,
  Clock3,
  FileHeart,
  Gavel,
  HeartPulse,
  Library,
  Search,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent } from "../components/ui/card";
import { Input } from "../components/ui/input";

type ResourceCategory = "Mental Health" | "Legal Support" | "Emergency Support" | "Self Help" | "Safety & Protection";

type SupportResource = {
  id: number;
  title: string;
  description: string;
  category: ResourceCategory;
  readTime: string;
  content: string[];
};

const resources: SupportResource[] = [
  { id: 1, title: "Understanding Anxiety After Trauma", description: "Recognise common anxiety responses and learn small ways to regain a sense of control.", category: "Mental Health", readTime: "5 min", content: ["Anxiety after a distressing experience can show up as racing thoughts, muscle tension, poor sleep or feeling constantly alert.", "Try to notice the response without judging it. Slow breathing, a predictable routine and talking with a trusted professional can help you feel more grounded.", "If distress feels severe or immediate safety is a concern, use the project's immediate-support pathway rather than relying on self-help alone."] },
  { id: 2, title: "Grounding Techniques", description: "Simple sensory techniques to help reconnect with the present moment when you feel overwhelmed.", category: "Mental Health", readTime: "4 min", content: ["Grounding is about gently bringing attention back to what is happening around you right now.", "Try naming five things you can see, four you can touch, three you can hear, two you can smell and one you can taste.", "You can also press both feet into the floor and slowly describe the room around you in neutral detail."] },
  { id: 3, title: "Managing Panic Symptoms", description: "A calm, practical guide for responding to a sudden wave of panic symptoms.", category: "Mental Health", readTime: "6 min", content: ["During panic, focus on making the next few minutes manageable rather than forcing the feeling to disappear instantly.", "Try a longer exhale than inhale, loosen tight clothing if safe, sit somewhere stable and remind yourself that intense sensations can pass.", "Seek professional support if episodes are frequent, worsening or difficult to manage alone."] },
  { id: 4, title: "5-Minute Breathing Exercise", description: "A short paced-breathing routine you can use before a meeting, session or difficult conversation.", category: "Self Help", readTime: "3 min", content: ["Sit in a supported position and relax your shoulders.", "Breathe in gently for four counts, pause briefly, then breathe out for six counts. Repeat without forcing the breath.", "If counting makes you uncomfortable, simply aim for a softer, slightly longer exhale."] },
  { id: 5, title: "Sleep and Recovery", description: "Create a gentler evening routine when stress is affecting rest and recovery.", category: "Self Help", readTime: "5 min", content: ["Keep wake and sleep times reasonably consistent where possible and reduce intense work immediately before bed.", "Write down tomorrow's essential tasks so your mind does not need to keep rehearsing them.", "If sleep problems persist for weeks or significantly affect daily functioning, consider discussing them with a qualified health professional."] },
  { id: 6, title: "Daily Emotional Check-in Guide", description: "A quick structure for noticing mood, stress and support needs without overthinking them.", category: "Self Help", readTime: "4 min", content: ["Ask yourself: what am I feeling, how intense is it, and what happened before it changed?", "Then identify one need for today, such as rest, practical help, a conversation or professional support.", "Use the answer as information, not as a score you need to perform well on."] },
  { id: 7, title: "Understanding Your Rights", description: "A plain-language checklist for preparing questions before speaking with legal support.", category: "Legal Support", readTime: "7 min", content: ["Write down what happened in chronological order while details are still clear to you.", "Keep copies of relevant documents and prepare questions about confidentiality, next steps and what evidence may be useful.", "This resource is general preparation material and is not a substitute for advice from a qualified legal professional."] },
  { id: 8, title: "How to Document an Incident", description: "Organise dates, events and supporting material in a clear and careful record.", category: "Legal Support", readTime: "6 min", content: ["Record the date, approximate time, place and a factual description of what occurred.", "Keep original files or documents where possible and avoid editing evidence simply to make it look cleaner.", "Store sensitive material securely and share it only with people or services you trust and are authorised to involve."] },
  { id: 9, title: "Preparing for Legal Assistance", description: "Know what to collect and what questions to ask before a legal-support meeting.", category: "Legal Support", readTime: "5 min", content: ["Bring a short timeline, relevant documents and a list of your main questions.", "Tell the professional if you have safety, privacy, accessibility or communication concerns before the discussion begins.", "Ask what the next step is, who will contact you, and what information you should keep confidential."] },
  { id: 10, title: "Creating a Personal Safety Plan", description: "Think through trusted contacts, safer places and practical steps before a stressful situation escalates.", category: "Safety & Protection", readTime: "7 min", content: ["Identify a few people or places you can contact if you begin to feel unsafe.", "Keep essential documents and important contact information accessible in a way that does not increase your risk.", "A personalised plan should account for your actual circumstances; involve a qualified support professional when possible."] },
  { id: 11, title: "Emergency Contact Planning", description: "Prepare a small, reliable contact plan for urgent situations without sharing unnecessary personal details.", category: "Safety & Protection", readTime: "4 min", content: ["Choose one or two trusted contacts who understand what kind of help you may need.", "Agree on a simple way to signal urgency and keep the plan easy to remember.", "Do not rely on this page for emergency numbers; use verified local emergency services and the project's support channels."] },
  { id: 12, title: "Immediate Support Information", description: "What to do inside SAHAS when you need quicker human support or feel at immediate risk.", category: "Emergency Support", readTime: "2 min", content: ["If you feel at immediate risk, use SAHAS's immediate-support or threat-reporting pathway as soon as it is available to you.", "Move to a safer place if you can do so without increasing risk and contact a trusted person or verified local emergency service.", "This resource intentionally does not display unverified helpline numbers."] },
];

const categories: Array<"All" | ResourceCategory> = ["All", "Mental Health", "Self Help", "Legal Support", "Safety & Protection", "Emergency Support"];

const categoryIcon = {
  "Mental Health": Brain,
  "Legal Support": Gavel,
  "Emergency Support": HeartPulse,
  "Self Help": Sparkles,
  "Safety & Protection": ShieldCheck,
};

export default function Resources() {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<(typeof categories)[number]>("All");
  const [selected, setSelected] = useState<SupportResource | null>(null);
  const [bookmarks, setBookmarks] = useState<number[]>([]);

  const filtered = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return resources.filter((resource) => {
      const matchesCategory = category === "All" || resource.category === category;
      const matchesQuery = !normalized || `${resource.title} ${resource.description} ${resource.category}`.toLowerCase().includes(normalized);
      return matchesCategory && matchesQuery;
    });
  }, [query, category]);

  function toggleBookmark(id: number) {
    setBookmarks((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id]);
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">Support library</p>
        <h1 className="mt-1 text-2xl font-bold tracking-tight text-foreground sm:text-3xl">Resources</h1>
        <p className="mt-2 max-w-2xl text-sm text-muted-foreground">Practical, calm guidance you can explore at your own pace. Use search or filter by the kind of support you need.</p>
      </div>

      <Card className="overflow-hidden">
        <CardContent className="p-5">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="relative w-full lg:max-w-md">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search guidance, safety, legal support..." className="pl-9" />
            </div>
            <div className="flex items-center gap-2 text-xs text-muted-foreground"><BookmarkCheck className="h-4 w-4 text-primary" /> {bookmarks.length} saved</div>
          </div>
          <div className="mt-4 flex gap-2 overflow-x-auto pb-1">
            {categories.map((item) => <Button key={item} size="sm" variant={category === item ? "default" : "outline"} onClick={() => setCategory(item)}>{item}</Button>)}
          </div>
        </CardContent>
      </Card>

      <div className="flex items-center justify-between"><p className="text-sm text-muted-foreground">Showing <span className="font-semibold text-foreground">{filtered.length}</span> resources</p>{(query || category !== "All") && <Button size="sm" variant="ghost" onClick={() => { setQuery(""); setCategory("All"); }}>Clear filters</Button>}</div>

      {filtered.length === 0 ? (
        <Card><CardContent className="flex flex-col items-center gap-3 py-14 text-center"><Library className="h-9 w-9 text-muted-foreground" /><div><p className="font-semibold">No matching resources</p><p className="mt-1 text-sm text-muted-foreground">Try a different search or category.</p></div><Button variant="outline" onClick={() => { setQuery(""); setCategory("All"); }}>Show all resources</Button></CardContent></Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {filtered.map((resource) => {
            const Icon = categoryIcon[resource.category];
            const saved = bookmarks.includes(resource.id);
            return (
              <Card key={resource.id} className="group flex h-full flex-col transition-all hover:-translate-y-0.5 hover:shadow-md">
                <CardContent className="flex h-full flex-col p-5">
                  <div className="flex items-start justify-between gap-3">
                    <div className="rounded-xl bg-primary/10 p-3 text-primary"><Icon className="h-5 w-5" /></div>
                    <Button size="icon" variant="ghost" onClick={() => toggleBookmark(resource.id)} aria-label={saved ? "Remove bookmark" : "Save resource"}>{saved ? <BookmarkCheck className="h-4 w-4 text-primary" /> : <Bookmark className="h-4 w-4" />}</Button>
                  </div>
                  <Badge variant="default" className="mt-4 w-fit">{resource.category}</Badge>
                  <h2 className="mt-3 text-base font-semibold leading-snug text-foreground">{resource.title}</h2>
                  <p className="mt-2 flex-1 text-sm leading-6 text-muted-foreground">{resource.description}</p>
                  <div className="mt-5 flex items-center justify-between border-t border-border pt-4"><span className="flex items-center gap-1.5 text-xs text-muted-foreground"><Clock3 className="h-3.5 w-3.5" /> {resource.readTime}</span><Button size="sm" variant="outline" onClick={() => setSelected(resource)}>View Resource</Button></div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      <Card className="border-primary/20 bg-primary/5"><CardContent className="flex gap-3 p-4"><FileHeart className="mt-0.5 h-5 w-5 shrink-0 text-primary" /><div><p className="text-sm font-medium">Resources support — they do not replace professional help.</p><p className="mt-1 text-xs leading-5 text-muted-foreground">For immediate safety concerns, use verified local emergency support and the appropriate SAHAS escalation pathway. No unverified helpline numbers are shown here.</p></div></CardContent></Card>

      {selected && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onMouseDown={(e) => e.target === e.currentTarget && setSelected(null)}>
          <Card className="max-h-[88vh] w-full max-w-2xl overflow-y-auto shadow-xl">
            <CardContent className="p-0">
              <div className="sticky top-0 flex items-start justify-between gap-3 border-b border-border bg-card p-5">
                <div><Badge variant="default">{selected.category}</Badge><h2 className="mt-3 text-xl font-bold">{selected.title}</h2><p className="mt-1 flex items-center gap-1.5 text-xs text-muted-foreground"><Clock3 className="h-3.5 w-3.5" /> {selected.readTime}</p></div>
                <Button size="icon" variant="ghost" onClick={() => setSelected(null)}><X className="h-4 w-4" /></Button>
              </div>
              <div className="space-y-4 p-5">
                <p className="text-sm font-medium leading-6 text-foreground">{selected.description}</p>
                {selected.content.map((paragraph, index) => <p key={index} className="text-sm leading-7 text-muted-foreground">{paragraph}</p>)}
                <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4"><p className="text-xs text-muted-foreground">Demo educational content • Review with a qualified professional where appropriate.</p><Button variant={bookmarks.includes(selected.id) ? "default" : "outline"} onClick={() => toggleBookmark(selected.id)}>{bookmarks.includes(selected.id) ? <BookmarkCheck className="h-4 w-4" /> : <Bookmark className="h-4 w-4" />}{bookmarks.includes(selected.id) ? "Saved" : "Save Resource"}</Button></div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
