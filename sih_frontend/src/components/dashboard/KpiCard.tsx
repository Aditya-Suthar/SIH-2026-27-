import { AlertOctagon, ClipboardList, HeartHandshake, ListChecks } from "lucide-react";

import { Card, CardContent } from "../ui/card";

import { cn } from "../../../lib/utils";

import type { KpiStat } from "../../../types";

const iconMap = {
  cases: ClipboardList,
  risk: AlertOctagon,
  sessions: HeartHandshake,
  interventions: ListChecks,
} as const;

export function KpiCard({ stat }: { stat: KpiStat }) {
  const Icon = iconMap[stat.icon];
  const isDanger = stat.tone === "danger";

  return (
    <Card>
      <CardContent className="flex items-start justify-between gap-3 pt-5">
        <div className="space-y-1.5">
          <p className="text-xs font-medium text-muted-foreground">{stat.label}</p>
          <p className="text-2xl font-bold tracking-tight text-foreground">{stat.value}</p>
          {stat.change && (
            <p className="text-xs font-medium text-success">{stat.change}</p>
          )}
          {stat.helperText && (
            <p
              className={cn(
                "text-xs font-medium",
                isDanger ? "text-danger" : "text-muted-foreground"
              )}
            >
              {stat.helperText}
            </p>
          )}
        </div>
        <div
          className={cn(
            "flex h-10 w-10 shrink-0 items-center justify-center rounded-lg",
            isDanger ? "bg-danger/10 text-danger" : "bg-primary/10 text-primary"
          )}
        >
          <Icon className="h-5 w-5" />
        </div>
      </CardContent>
    </Card>
  );
}
