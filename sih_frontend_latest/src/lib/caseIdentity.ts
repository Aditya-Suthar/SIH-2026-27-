import type { PriorityCase, RiskLevel } from "../../types";

export const victimDisplayName = (name?: string | null) => name?.trim() || "Unnamed Victim";

export function matchesCaseSearch(item: { caseId: string; victimName?: string | null; assignedCounsellor?: string }, search: string) {
  const query = search.trim().toLocaleLowerCase();
  return [item.caseId, victimDisplayName(item.victimName), item.assignedCounsellor ?? ""]
    .some(value => value.toLocaleLowerCase().includes(query));
}

export function filterCases(items: PriorityCase[], search: string, risk: "All" | RiskLevel, status: string) {
  return items.filter(item => matchesCaseSearch(item, search)
    && (risk === "All" || item.riskLevel === risk)
    && (status === "All" || item.interventionStatus === status));
}
