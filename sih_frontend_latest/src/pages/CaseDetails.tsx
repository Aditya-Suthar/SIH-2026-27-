import {API_BASE_URL} from "../lib/config";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";


import { CaseMonitoring } from "../components/monitoring/CaseMonitoring";
import { CaseChat } from "../components/monitoring/CaseChat";
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

export default function CaseDetails() {
  const { caseId } = useParams();
  const navigate = useNavigate();

  const [caseData, setCaseData] = useState<PriorityCase | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active=true;
    const controller=new AbortController();
    setLoading(true);setError("");
    const fetchCase = async () => {
      try {
        const token = localStorage.getItem("access_token");

        if (!token) {
          setError("No authentication token found");
          return;
        }

        if (!caseId) {
          setError("Invalid case ID");
          return;
        }

        const response = await fetch(
          `${API_BASE_URL}/api/cases/${caseId}`,
          {
            signal: controller.signal,
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        if (!response.ok) {
          throw new Error(`Failed to fetch case: ${response.status}`);
        }

        const data: PriorityCase = await response.json();

        if(active)setCaseData(data);
      } catch (err) {
        if(!active)return;
        setError("Could not load case details");
      } finally {
        if(active)setLoading(false);
      }
    };

    fetchCase();
    return()=>{active=false;controller.abort();};
  }, [caseId]);

  if (loading) {
    return (
      <p className="text-sm text-muted-foreground">
        Loading case details...
      </p>
    );
  }

  if (error || !caseData) {
    return (
      <div className="space-y-4">
        <p className="text-sm text-red-500">
          {error || "Case not found"}
        </p>

        <Button variant="outline" onClick={() => navigate("/cases")}>
          Back to Cases
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Case {caseData.caseId}
          </h1>

          <p className="mt-1 text-sm text-muted-foreground">
            Detailed information and monitoring status for this case.
          </p>
        </div>

        <Button variant="outline" onClick={() => navigate("/cases")}>
          Back
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Case Overview</CardTitle>
        </CardHeader>

        <CardContent>
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">

            <div>
              <p className="text-xs text-muted-foreground">
                Case ID
              </p>

              <p className="mt-1 font-medium">
                {caseData.caseId}
              </p>
            </div>

            <div>
              <p className="text-xs text-muted-foreground">
                Questionnaire Risk Level
              </p>

              <div className="mt-1">
                <Badge variant={riskBadgeVariant[caseData.riskLevel]}>
                  {caseData.riskLevel}
                </Badge>
              </div>
            </div>

            <div>
              <p className="text-xs text-muted-foreground">
                Assigned Counsellor
              </p>

              <p className="mt-1 font-medium">
                {caseData.assignedCounsellor}
              </p>
            </div>

            <div>
              <p className="text-xs text-muted-foreground">
                Last Assessment
              </p>

              <p className="mt-1 font-medium">
                {caseData.lastAssessment}
              </p>
            </div>

            <div>
              <p className="text-xs text-muted-foreground">
                Intervention Status
              </p>

              <p className="mt-1 font-medium">
                {caseData.interventionStatus}
              </p>
            </div>

            <div>
              <p className="text-xs text-muted-foreground">
                Location
              </p>

              <p className="mt-1 font-medium">
                {[caseData.district, caseData.state].filter(Boolean).join(", ") || "Not provided"}
              </p>
            </div>

          </div>
        </CardContent>
      </Card>
      <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1.25fr)_minmax(0,1fr)]">
        <CaseMonitoring key={`monitor-${caseData.caseId}`} caseId={caseData.caseId} />
        {(localStorage.getItem("role") === "counsellor" || localStorage.getItem("role") === "victim") && <CaseChat key={`chat-${caseData.caseId}`} caseId={caseData.caseId} />}
      </div>
    </div>
  );
}
