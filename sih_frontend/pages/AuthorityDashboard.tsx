import { KpiCard } from "../src/components/dashboard/KpiCard";
import { DistressTrendCard } from "../src/components/dashboard/DistressTrendCard";
import { RiskDistributionCard } from "../src/components/dashboard/RiskDistributionCard";
import { HighPriorityCasesTable } from "../src/components/dashboard/HighPriorityCasesTable";
import { CounsellorAvailabilityCard } from "../src/components/dashboard/CounsellorAvailabilityCard";
import { kpiStats } from "../data/mockData";

export default function AuthorityDashboard() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          Good Morning, District Welfare Officer
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Monitor victim wellbeing, counselling activity and intervention status.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {kpiStats.map((stat) => (
          <KpiCard key={stat.id} stat={stat} />
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <DistressTrendCard />
        <RiskDistributionCard />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <HighPriorityCasesTable />
        </div>
        <CounsellorAvailabilityCard />
      </div>
    </div>
  );
}
