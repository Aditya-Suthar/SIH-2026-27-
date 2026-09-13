import type { PriorityCase } from "../../types";
import { api } from "./api";

export type CaseResponse = PriorityCase & { victimName: string };
export const getCases = (signal?: AbortSignal) => api<CaseResponse[]>("/api/cases", { signal });
export const getCase = (caseId: string, signal?: AbortSignal) =>
  api<CaseResponse>(`/api/cases/${encodeURIComponent(caseId)}`, { signal });
