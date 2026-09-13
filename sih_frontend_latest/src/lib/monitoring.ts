export type Analysis = {
  finished_at: string | null;
  id: number; assessment_id: number | null; message_id: number | null;
  source_type: "assessment" | "message"; status: "completed" | "failed" | "pending";
  distress_score: number | null; risk_level: string | null; emotions: string[] | null;
  requires_attention: boolean | null; reason: string | null; created_at: string;
  error_message?: string | null;
};
export type MonitoringCase = {
  victim_name: string;
  current_questionnaire?: QuestionnaireEvidence | null;
  questionnaire_history?: QuestionnaireEvidence[];
  case_id: string; assigned_counsellor: string; category: "URGENT" | "HIGH" | "MEDIUM" | "NORMAL" | "UNASSESSED";
  score: number | null; reasons: string[]; alerts: string[]; latest_analysis: Analysis | null;
  latest_attempt?: Analysis | null; questionnaire_score?: number | null;
  current_risk: "low" | "medium" | "high" | "critical" | null; current_score: number | null;
  current_source: "questionnaire" | "text_ai" | "legacy_case" | null; current_state_at: string | null;
  latest_attempt_status: string; latest_activity: string | null; needs_review: boolean; stale: boolean;
  review: { analysis_id: number; reviewer_id: number; reviewed_at: string } | null;
  trend: { state: string; days: number; change: number | null; slope_per_day: number | null; explanation: string };
  selected_evidence: SelectedEvidence | null;
};
export type QuestionnaireEvidence = { id: number; score: number | null; risk: string | null; observed_at: string | null; safety_override: boolean };
export type SelectedEvidence = {
  id: number; score_snapshot: number | null; severity: string; source: string;
  source_record_id: number | null; created_at: string; triggering_rule: string;
  safety_override: boolean; reviewed: boolean; reviewed_at: string | null;
  assessment: { id: number; distress_score: number | null; risk_level: string | null } | null;
  analysis: Analysis | null;
};
export const priorityTone = { URGENT: "danger", HIGH: "orange", MEDIUM: "warning", NORMAL: "success", UNASSESSED: "default" } as const;
export const riskTone = (risk: string | null | undefined) => risk === "critical" ? "danger" : risk === "high" ? "orange" : risk === "medium" ? "warning" : risk === "low" ? "success" : "default";
export const words = (value: string) => value.replaceAll("_", " ");
export const dateTime = (value: string | null) => value ? new Date(value).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", year: "numeric" }) : "No activity yet";
export const displayedTimeZone = () => Intl.DateTimeFormat().resolvedOptions().timeZone;
export function observationPoints(history: Analysis[], questionnaires: QuestionnaireEvidence[]) {
  return [
    ...history.filter(row => row.status === 'completed' && row.distress_score !== null).map(row => ({
      time: Date.parse(row.finished_at || row.created_at), text_ai: row.distress_score, questionnaire: null as number | null })),
    ...questionnaires.filter(row => row.score !== null && row.observed_at).map(row => ({
      time: Date.parse(row.observed_at!), questionnaire: row.score, text_ai: null as number | null })),
  ].filter(row => Number.isFinite(row.time)).sort((a,b) => a.time-b.time);
}
