import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";

type CounsellorAvailabilityCardProps = {
  availability: {
    available: number;
    inSession: number;
    unavailable: number;
  };
};

export function CounsellorAvailabilityCard({
  availability,
}: CounsellorAvailabilityCardProps) {
  const rows = [
    {
      label: "Available",
      value: availability.available,
      dot: "bg-success",
    },
    {
      label: "In Session",
      value: availability.inSession,
      dot: "bg-primary",
    },
    {
      label: "Unavailable",
      value: availability.unavailable,
      dot: "bg-muted-foreground",
    },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Counsellor Availability</CardTitle>

        <p className="text-xs text-muted-foreground">
          Live status across all assigned counsellors
        </p>
      </CardHeader>

      <CardContent className="space-y-3">
        {rows.map((row) => (
          <div
            key={row.label}
            className="flex items-center justify-between text-sm"
          >
            <div className="flex items-center gap-2">
              <span className={`h-2 w-2 rounded-full ${row.dot}`} />
              <span className="text-foreground">{row.label}</span>
            </div>

            <span className="font-semibold text-foreground">
              {row.value}
            </span>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}