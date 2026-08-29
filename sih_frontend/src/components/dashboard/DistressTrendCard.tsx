import { useState } from "react";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";

import { Button } from "../ui/button";

import { cn } from "../../../lib/utils";

import { getTrendData } from "../../../data/mockData";

import type { TrendRange } from "../../../types";

const rangeOptions: { value: TrendRange; label: string }[] = [
  { value: "7d", label: "7 Days" },
  { value: "30d", label: "30 Days" },
  { value: "3m", label: "3 Months" },
];

export function DistressTrendCard() {
  const [range, setRange] = useState<TrendRange>("7d");
  const data = getTrendData(range);

  return (
    <Card className="col-span-1 lg:col-span-2">
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <div>
          <CardTitle>Distress &amp; Risk Trend</CardTitle>
          <p className="mt-1 text-xs text-muted-foreground">
            Aggregated distress score and flagged cases over time
          </p>
        </div>
        <div className="flex items-center gap-1 rounded-lg bg-secondary p-1">
          {rangeOptions.map((option) => (
            <Button
              key={option.value}
              size="sm"
              variant="ghost"
              onClick={() => setRange(option.value)}
              className={cn(
                "h-7 rounded-md px-2.5 text-xs text-muted-foreground hover:bg-card",
                range === option.value &&
                  "bg-card text-primary shadow-sm hover:bg-card"
              )}
            >
              {option.label}
            </Button>
          ))}
        </div>
      </CardHeader>
      <CardContent className="h-72 pt-2">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
            <defs>
              <linearGradient id="distressFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="hsl(217 72% 52%)" stopOpacity={0.28} />
                <stop offset="100%" stopColor="hsl(217 72% 52%)" stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(214 35% 89%)" vertical={false} />
            <XAxis
              dataKey="label"
              tickLine={false}
              axisLine={false}
              tick={{ fontSize: 12, fill: "hsl(215 18% 46%)" }}
            />
            <YAxis
              tickLine={false}
              axisLine={false}
              tick={{ fontSize: 12, fill: "hsl(215 18% 46%)" }}
              width={32}
            />
            <Tooltip
              contentStyle={{
                borderRadius: 10,
                border: "1px solid hsl(214 35% 89%)",
                boxShadow: "0 4px 16px -4px rgb(30 64 130 / 0.15)",
                fontSize: 12,
              }}
            />
            <Area
              type="monotone"
              dataKey="distressScore"
              name="Distress Score"
              stroke="hsl(217 72% 52%)"
              strokeWidth={2}
              fill="url(#distressFill)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
