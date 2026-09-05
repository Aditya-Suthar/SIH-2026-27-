import { useEffect, useMemo, useState } from "react";

import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";

import type { PriorityCase, RiskLevel } from "../../types";

const riskBadgeVariant: Record<
  RiskLevel,
  "danger" | "orange" | "warning" | "success"
> = {
  Critical: "danger",
  High: "orange",
  Moderate: "warning",
  Low: "success",
};

const riskFilterOptions: Array<"All" | RiskLevel> = [
  "All",
  "Critical",
  "High",
  "Moderate",
  "Low",
];

export default function Cases() {
  const [cases, setCases] = useState<PriorityCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [search, setSearch] = useState("");
  const [riskFilter, setRiskFilter] = useState<"All" | RiskLevel>("All");
  const [statusFilter, setStatusFilter] = useState("All");

  useEffect(() => {
    const fetchCases = async () => {
      try {
        const token = localStorage.getItem("access_token");

        if (!token) {
          setError("No authentication token found");
          setLoading(false);
          return;
        }

        const response = await fetch("http://127.0.0.1:8000/api/cases", {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (!response.ok) {
          throw new Error(`Failed to fetch cases: ${response.status}`);
        }

        const data: PriorityCase[] = await response.json();
        setCases(data);
      } catch (err) {
        console.error(err);
        setError("Could not load cases");
      } finally {
        setLoading(false);
      }
    };

    fetchCases();
  }, []);

  // Built from the real data returned by the API, rather than a hardcoded
  // list, so this never invents a status the backend doesn't actually send.
  const statusOptions = useMemo(() => {
    const unique = Array.from(
      new Set(cases.map((c) => c.interventionStatus).filter(Boolean))
    );
    return ["All", ...unique];
  }, [cases]);

  const filteredCases = useMemo(() => {
    const query = search.trim().toLowerCase();

    return cases.filter((c) => {
      const matchesSearch =
        query.length === 0 ||
        c.caseId.toLowerCase().includes(query) ||
        c.assignedCounsellor.toLowerCase().includes(query);

      const matchesRisk = riskFilter === "All" || c.riskLevel === riskFilter;

      const matchesStatus =
        statusFilter === "All" || c.interventionStatus === statusFilter;

      return matchesSearch && matchesRisk && matchesStatus;
    });
  }, [cases, search, riskFilter, statusFilter]);

  const hasActiveFilters =
    search.trim().length > 0 || riskFilter !== "All" || statusFilter !== "All";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          Cases
        </h1>

        <p className="mt-1 text-sm text-muted-foreground">
          Review and monitor all registered cases, filter by risk and
          intervention status, and track counselling progress.
        </p>
      </div>

      <Card>
        <CardHeader className="flex flex-col gap-4 pb-4">
          <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
            <div>
              <CardTitle>All Cases</CardTitle>
              <p className="mt-1 text-xs text-muted-foreground">
                {loading
                  ? "Loading cases..."
                  : `Showing ${filteredCases.length} of ${cases.length} total cases`}
              </p>
            </div>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by Case ID or Counsellor"
              className="w-full flex-1 rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring sm:max-w-xs"
            />

            <select
              value={riskFilter}
              onChange={(e) =>
                setRiskFilter(e.target.value as "All" | RiskLevel)
              }
              className="rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            >
              {riskFilterOptions.map((option) => (
                <option key={option} value={option}>
                  {option === "All" ? "All Risk Levels" : option}
                </option>
              ))}
            </select>

            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            >
              {statusOptions.map((option) => (
                <option key={option} value={option}>
                  {option === "All" ? "All Statuses" : option}
                </option>
              ))}
            </select>
          </div>
        </CardHeader>

        <CardContent className="pt-0">
          {loading && (
            <p className="py-4 text-sm text-muted-foreground">
              Loading cases...
            </p>
          )}

          {!loading && error && (
            <p className="py-4 text-sm text-red-500">{error}</p>
          )}

          {!loading && !error && (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[720px] border-collapse text-sm">
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
                  {filteredCases.map((c) => (
                    <tr
                      key={c.caseId}
                      className="border-b border-border last:border-0"
                    >
                      <td className="py-3 pr-4 font-medium text-foreground">
                        {c.caseId}
                      </td>

                      <td className="py-3 pr-4">
                        <Badge variant={riskBadgeVariant[c.riskLevel]}>
                          {c.riskLevel}
                        </Badge>
                      </td>

                      <td className="py-3 pr-4 text-muted-foreground">
                        {c.assignedCounsellor}
                      </td>

                      <td className="py-3 pr-4 text-muted-foreground">
                        {c.lastAssessment}
                      </td>

                      <td className="py-3 pr-4 text-muted-foreground">
                        {c.interventionStatus}
                      </td>

                      <td className="py-3 pr-0 text-right">
                        <Button
                          variant="outline"
                          size="sm"
                          title="Case detail view is not yet implemented"
                          onClick={() =>
                            console.log(
                              "View case:",
                              c.caseId,
                              "— wire this up once a case-detail endpoint exists"
                            )
                          }
                        >
                          View
                        </Button>
                      </td>
                    </tr>
                  ))}

                  {filteredCases.length === 0 && (
                    <tr>
                      <td
                        colSpan={6}
                        className="py-8 text-center text-muted-foreground"
                      >
                        {hasActiveFilters
                          ? "No cases match your search or filters."
                          : "No cases found."}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
