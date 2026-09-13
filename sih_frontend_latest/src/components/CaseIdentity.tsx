import { victimDisplayName } from "../lib/caseIdentity";

export function CaseIdentity({ caseId, victimName }: { caseId: string; victimName?: string | null }) {
  return <span className="inline-flex min-w-0 flex-col text-left">
    <span className="break-words font-medium text-foreground">{victimDisplayName(victimName)}</span>
    <span className="text-xs font-normal text-muted-foreground">{caseId}</span>
  </span>;
}
