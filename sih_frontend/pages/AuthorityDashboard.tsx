import { useEffect, useState } from "react";

import { KpiCard } from "../src/components/dashboard/KpiCard";
import { DistressTrendCard } from "../src/components/dashboard/DistressTrendCard";
import { RiskDistributionCard } from "../src/components/dashboard/RiskDistributionCard";
import { HighPriorityCasesTable } from "../src/components/dashboard/HighPriorityCasesTable";
import { CounsellorAvailabilityCard } from "../src/components/dashboard/CounsellorAvailabilityCard";


type RiskLevel = "Low" | "Moderate" | "High" | "Critical";

type ApiCase = {
  caseId: string;
  riskLevel: RiskLevel;
  assignedCounsellor: string;
  lastAssessment: string;
  interventionStatus: string;
};          

export default function AuthorityDashboard() {
  const [cases, setCases] = useState<ApiCase[]>([]);

  useEffect(() => {
    const fetchCases = async () => {
      try {
        const token = localStorage.getItem("access_token");

        if (!token) return;

        const response = await fetch(
          "http://127.0.0.1:8000/api/cases",
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        if (!response.ok) {
          console.error("Failed to fetch cases:", response.status);
          return;
        }

        const data: ApiCase[] = await response.json();
        setCases(data);
      } catch (error) {
        console.error("Could not fetch cases:", error);
      }
    };

    fetchCases();
  }, []);

  const highRiskCases = cases.filter(
    (c) =>
      c.riskLevel === "High" ||
      c.riskLevel === "Critical"
  ).length;

  const kpiStats = [
    {
      id: "registered",
      label: "Registered Cases",
      value: String(cases.length),
      icon: "cases" as const,
    },
    {
      id: "high-risk",
      label: "High Risk Cases",
      value: String(highRiskCases),
      icon: "risk" as const,
      tone: "danger" as const,
      helperText: "Require close attention",
    },
  ];

  const riskCounts = {
  Low: cases.filter((c) => c.riskLevel === "Low").length,
  Moderate: cases.filter((c) => c.riskLevel === "Moderate").length,
  High: cases.filter((c) => c.riskLevel === "High").length,
  Critical: cases.filter((c) => c.riskLevel === "Critical").length,
};

const assignedCounsellors = cases
  .map((c) => c.assignedCounsellor)
  .filter((name) => name && name !== "Unassigned");

const uniqueCounsellors = [...new Set(assignedCounsellors)];

const counsellorAvailability = {
  available: uniqueCounsellors.length,
  inSession: 0,
  unavailable: 0,
};

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
        <RiskDistributionCard
      totalCases={cases.length}
      riskCounts={riskCounts}
    />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <HighPriorityCasesTable />
        </div>

        <CounsellorAvailabilityCard
  availability={counsellorAvailability}
/>
      </div>
    </div>
  );
}