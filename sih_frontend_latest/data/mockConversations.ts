import type { ChatMessage, Conversation } from "../types";

// Fixtures represent the signed-in counsellor's assigned cases only.
export function createMockConversations() {
  const at = (hours: number, minutes: number, daysAgo = 0) => {
    const date = new Date();
    date.setDate(date.getDate() - daysAgo);
    date.setHours(hours, minutes, 0, 0);
    return date.toISOString();
  };
  const messages: ChatMessage[] = [
    { id: "1042-1", caseId: "CASE-1042", sender: "victim", content: "Hello, I have been feeling anxious today.", createdAt: at(10, 38) },
    { id: "1042-2", caseId: "CASE-1042", sender: "counsellor", content: "I'm here with you. Would you like to tell me what has been making you feel anxious?", createdAt: at(10, 40) },
    { id: "1042-3", caseId: "CASE-1042", sender: "victim", content: "I have been feeling anxious today.", createdAt: at(10, 42) },
    { id: "1087-1", caseId: "CASE-1087", sender: "victim", content: "I need to talk to someone.", createdAt: at(9, 15) },
    { id: "1103-1", caseId: "CASE-1103", sender: "victim", content: "Thank you for yesterday's session.", createdAt: at(16, 20, 1) },
    { id: "1120-1", caseId: "CASE-1120", sender: "victim", content: "Can you please review my latest check-in?", createdAt: at(8, 50) },
  ];
  const cases: Omit<Conversation, "latestMessage">[] = [
    { caseId: "CASE-1042", riskLevel: "Moderate", distressScore: 54, unreadCount: 1 },
    { caseId: "CASE-1087", riskLevel: "High", distressScore: 76, unreadCount: 1 },
    { caseId: "CASE-1103", riskLevel: "Low", unreadCount: 0 },
    { caseId: "CASE-1120", riskLevel: "Critical", distressScore: 92, unreadCount: 1 },
  ];
  return {
    conversations: cases.map((item): Conversation => ({
      ...item,
      latestMessage: messages.filter((message) => message.caseId === item.caseId).at(-1) ?? null,
    })),
    messages,
  };
}
