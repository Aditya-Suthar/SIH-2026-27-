import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";

import { Badge } from "../ui/badge";

import { Button } from "../ui/button";

import { priorityCases } from "../../../data/mockData";

import type { RiskLevel } from "../../../types";
const riskBadgeVariant: Record<RiskLevel, "danger" | "orange" | "warning" | "success"> = {
  Critical: "danger",
  High: "orange",
  Moderate: "warning",
  Low: "success",
};

export function HighPriorityCasesTable() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>High Priority Cases</CardTitle>
        <p className="text-xs text-muted-foreground">
          Cases flagged for elevated risk or pending intervention
        </p>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] border-collapse text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                <th className="py-2.5 pr-4">Case ID</th>
                <th className="py-2.5 pr-4">Risk Level</th>
                <th className="py-2.5 pr-4">Assigned Counsellor</th>
                <th className="py-2.5 pr-4">Last Assessment</th>
                <th className="py-2.5 pr-4">Intervention Status</th>
                <th className="py-2.5 pr-0 text-right">Action</th>
              </tr>
            </thead>
            <tbody>
              {priorityCases.map((c) => (
                <tr key={c.caseId} className="border-b border-border last:border-0">
                  <td className="py-3 pr-4 font-medium text-foreground">{c.caseId}</td>
                  <td className="py-3 pr-4">
                    <Badge variant={riskBadgeVariant[c.riskLevel]}>{c.riskLevel}</Badge>
                  </td>
                  <td className="py-3 pr-4 text-muted-foreground">{c.assignedCounsellor}</td>
                  <td className="py-3 pr-4 text-muted-foreground">{c.lastAssessment}</td>
                  <td className="py-3 pr-4 text-muted-foreground">{c.interventionStatus}</td>
                  <td className="py-3 pr-0 text-right">
                    <Button variant="outline" size="sm">
                      View
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
