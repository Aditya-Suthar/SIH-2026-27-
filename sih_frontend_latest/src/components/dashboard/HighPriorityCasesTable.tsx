import { getCases } from "../../lib/cases";
import { CaseIdentity } from "../CaseIdentity";
import { useEffect, useState } from "react"

import { Card, CardContent, CardHeader, CardTitle } from "../ui/card"
import { Badge } from "../ui/badge"
import { Button } from "../ui/button"

import type { PriorityCase, RiskLevel } from "../../../types"

const riskBadgeVariant: Record<
  RiskLevel,
  "danger" | "orange" | "warning" | "success"
> = {
  Critical: "danger",
  High: "orange",
  Moderate: "warning",
  Low: "success",
}

export function HighPriorityCasesTable() {
  const [cases, setCases] = useState<PriorityCase[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  useEffect(() => {
    const fetchCases = async () => {
      try {
        const data = await getCases()

      setCases(data)
      } catch (err) {
        console.error(err)
        setError("Could not load cases")
      } finally {
        setLoading(false)
      }
    }

    fetchCases()
  }, [])

  return (
    <Card>
      <CardHeader>
        <CardTitle>High Priority Cases</CardTitle>

        <p className="text-xs text-muted-foreground">
          Cases flagged for elevated risk or pending intervention
        </p>
      </CardHeader>

      <CardContent className="pt-0">
        {loading && (
          <p className="py-4 text-sm text-muted-foreground">
            Loading cases...
          </p>
        )}

        {error && (
          <p className="py-4 text-sm text-red-500">
            {error}
          </p>
        )}

        {!loading && !error && (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] border-collapse text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  <th className="py-2.5 pr-4">Case</th>
                  <th className="py-2.5 pr-4">Risk Level</th>
                  <th className="py-2.5 pr-4">Assigned Counsellor</th>
                  <th className="py-2.5 pr-4">Last Assessment</th>
                  <th className="py-2.5 pr-4">Intervention Status</th>
                  <th className="py-2.5 pr-0 text-right">Action</th>
                </tr>
              </thead>

              <tbody>
                {cases.map((c) => (
                  <tr
                    key={c.caseId}
                    className="border-b border-border last:border-0"
                  >
                    <td className="py-3 pr-4 font-medium text-foreground">
                      <CaseIdentity caseId={c.caseId} victimName={c.victimName} />
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
                      <Button variant="outline" size="sm">
                        View
                      </Button>
                    </td>
                  </tr>
                ))}

                {cases.length === 0 && (
                  <tr>
                    <td
                      colSpan={6}
                      className="py-6 text-center text-muted-foreground"
                    >
                      No cases found
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  )
}