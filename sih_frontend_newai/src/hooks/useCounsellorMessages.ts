import { useState } from "react";
import { createMockConversations } from "../../data/mockConversations";
import type { ChatMessage } from "../../types";

// API integration belongs here; the page need not know where messages are stored.
// This demo state is intentionally discarded when the page unmounts.
export function useCounsellorMessages() {
  const [data, setData] = useState(createMockConversations);
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);

  function selectConversation(caseId: string) {
    if (!data.conversations.some((conversation) => conversation.caseId === caseId)) return;
    setSelectedCaseId(caseId);
    setData((current) => ({
      ...current,
      conversations: current.conversations.map((conversation) =>
        conversation.caseId === caseId ? { ...conversation, unreadCount: 0 } : conversation,
      ),
    }));
  }

  function sendMessage(content: string) {
    const text = content.trim();
    if (!selectedCaseId || !text) return;
    const message: ChatMessage = {
      id: crypto.randomUUID(),
      caseId: selectedCaseId,
      sender: "counsellor",
      content: text,
      createdAt: new Date().toISOString(),
    };
    setData((current) => ({
      messages: [...current.messages, message],
      conversations: current.conversations.map((conversation) =>
        conversation.caseId === message.caseId
          ? { ...conversation, latestMessage: message }
          : conversation,
      ),
    }));
  }

  return {
    conversations: data.conversations,
    selectedConversation: data.conversations.find((item) => item.caseId === selectedCaseId) ?? null,
    messages: data.messages.filter((message) => message.caseId === selectedCaseId),
    selectConversation,
    sendMessage,
  };
}
