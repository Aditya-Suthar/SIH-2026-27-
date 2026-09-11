import { Card, CardContent } from "../src/components/ui/card";
import { Construction } from "lucide-react";

export default function ComingSoon({ section }: { section: string }) {
  return (
    <Card>
      <CardContent className="flex flex-col items-center justify-center gap-3 py-16 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
          <Construction className="h-6 w-6" />
        </div>
        <div>
          <p className="text-base font-semibold text-foreground">{section}</p>
          <p className="mt-1 text-sm text-muted-foreground">
            This section is not built yet. Check back soon.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
