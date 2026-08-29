import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";

import { counsellorAvailability } from "../../../data/mockData";

const rows = [
  { label: "Available", value: counsellorAvailability.available, dot: "bg-success" },
  { label: "In Session", value: counsellorAvailability.inSession, dot: "bg-primary" },
  { label: "Unavailable", value: counsellorAvailability.unavailable, dot: "bg-muted-foreground" },
];

export function CounsellorAvailabilityCard() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Counsellor Availability</CardTitle>
        <p className="text-xs text-muted-foreground">Live status across all assigned counsellors</p>
      </CardHeader>
      <CardContent className="space-y-3">
        {rows.map((row) => (
          <div key={row.label} className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-2">
              <span className={`h-2 w-2 rounded-full ${row.dot}`} />
              <span className="text-foreground">{row.label}</span>
            </div>
            <span className="font-semibold text-foreground">{row.value}</span>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
