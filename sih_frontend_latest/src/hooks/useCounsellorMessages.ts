import { useState } from "react";
import { useRemote } from "../lib/api";
import type { CaseResponse } from "../lib/cases";
// Same case-selection seam, now backed by authorized persisted cases.
export function useCounsellorMessages() {
  const { data, error, loading, refresh } = useRemote<CaseResponse[]>("/api/cases");
  const [selectedCaseId, selectConversation] = useState<string | null>(null);
  const conversations = data ?? [];
  return { conversations, selectedConversation: conversations.find(c => c.caseId === selectedCaseId) ?? null,
    selectConversation, loading, error, refresh };
}
