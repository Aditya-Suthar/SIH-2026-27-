export type Analysis = {
  id: number; assessment_id: number | null; message_id: number | null;
  source_type: "assessment" | "message"; status: "completed" | "failed" | "pending";
  distress_score: number | null; risk_level: string | null; emotions: string[] | null;
  requires_attention: boolean | null; reason: string | null; created_at: string;
};
export type MonitoringCase = {
  case_id: string; assigned_counsellor: string; category: "URGENT" | "HIGH" | "MEDIUM" | "NORMAL" | "UNASSESSED";
  score: number | null; reasons: string[]; alerts: string[]; latest_analysis: Analysis | null;
  latest_attempt_status: string; latest_activity: string | null; needs_review: boolean; stale: boolean;
  review: { analysis_id: number; reviewer_id: number; reviewed_at: string } | null;
  trend: { state: string; days: number; change: number | null; slope_per_day: number | null; explanation: string };
};
export const priorityTone = { URGENT: "danger", HIGH: "orange", MEDIUM: "warning", NORMAL: "success", UNASSESSED: "default" } as const;
export const riskTone = (risk: string | null | undefined) => risk === "critical" ? "danger" : risk === "high" ? "orange" : risk === "medium" ? "warning" : risk === "low" ? "success" : "default";
export const words = (value: string) => value.replaceAll("_", " ");
export const dateTime = (value: string | null) => value ? new Date(value).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", year: "numeric" }) : "No activity yet";
