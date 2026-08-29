export type RiskLevel = "Low" | "Moderate" | "High" | "Critical";

export type InterventionStatus =
  | "Immediate Action"
  | "Counselling Scheduled"
  | "Follow-up Pending"
  | "Monitoring";

export interface KpiStat {
  id: string;
  label: string;
  value: string;
  change?: string;
  helperText?: string;
  icon: "cases" | "risk" | "sessions" | "interventions";
  tone?: "neutral" | "danger";
}

export interface TrendPoint {
  label: string;
  distressScore: number;
  riskFlags: number;
}

export interface RiskDistributionItem {
  level: RiskLevel;
  count: number;
  percentage: number;
}

export interface PriorityCase {
  caseId: string;
  riskLevel: RiskLevel;
  assignedCounsellor: string;
  lastAssessment: string;
  interventionStatus: InterventionStatus;
}

export interface CounsellorAvailability {
  available: number;
  inSession: number;
  unavailable: number;
}

export type TrendRange = "7d" | "30d" | "3m";

export interface NavItem {
  label: string;
  path: string;
  icon: string;
}

export interface NavSection {
  title: string;
  items: NavItem[];
}
