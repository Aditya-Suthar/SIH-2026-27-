import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";

import type { RiskLevel } from "../../../types";

import { cn } from "../../../lib/utils";

const barColor: Record<RiskLevel, string> = {
  Low: "bg-success",
  Moderate: "bg-warning",
  High: "bg-orange-500",
  Critical: "bg-danger",
};

type RiskDistributionCardProps = {
  totalCases: number;

  riskCounts: {
    Low: number;
    Moderate: number;
    High: number;
    Critical: number;
  };
};

export function RiskDistributionCard({
  totalCases,
  riskCounts,
}: RiskDistributionCardProps) {

  const riskDistribution = (
    ["Low", "Moderate", "High", "Critical"] as RiskLevel[]
  ).map((level) => ({
    level,
    count: riskCounts[level],

    percentage:
      totalCases === 0
        ? 0
        : Math.round((riskCounts[level] / totalCases) * 100),
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Risk Distribution</CardTitle>

        <p className="text-xs text-muted-foreground">
          Share of registered cases by risk level
        </p>
      </CardHeader>

      <CardContent className="space-y-4">
        {riskDistribution.map((item) => (
          <div key={item.level}>

            <div className="mb-1.5 flex items-center justify-between text-sm">
              <span className="font-medium text-foreground">
                {item.level} Risk
              </span>

              <span className="text-muted-foreground">
                {item.count} · {item.percentage}%
              </span>
            </div>

            <div className="h-2 w-full overflow-hidden rounded-full bg-secondary">
              <div
                className={cn(
                  "h-full rounded-full",
                  barColor[item.level]
                )}
                style={{
                  width: `${item.percentage}%`,
                }}
              />
            </div>

          </div>
        ))}
      </CardContent>
    </Card>
  );
}