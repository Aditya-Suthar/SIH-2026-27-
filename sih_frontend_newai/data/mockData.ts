import type {
  CounsellorAvailability,
  KpiStat,
  NavSection,
  PriorityCase,
  RiskDistributionItem,
  TrendPoint,
  TrendRange,
}  from "../types";;

export const navSections: NavSection[] = [
  {
    title: "Overview",
    items: [{ label: "Dashboard", path: "/authority", icon: "LayoutDashboard" }],
  },
  {
    title: "Management",
    items: [
      { label: "Cases", path: "/cases", icon: "FolderKanban" },
      { label: "Alerts", path: "/alerts", icon: "AlertTriangle" },
      { label: "Counsellors", path: "/counsellors", icon: "Users" },
      { label: "Sessions", path: "/sessions", icon: "CalendarClock" },
      { label: "Analytics", path: "/analytics", icon: "BarChart3" },
      { label: "Reports", path: "/reports", icon: "FileText" },
    ],
  },
  {
    title: "System",
    items: [
      { label: "Resources", path: "/resources", icon: "Library" },
      { label: "Settings", path: "/settings", icon: "Settings" },
    ],
  },
];

export const kpiStats: KpiStat[] = [
  {
    id: "registered-cases",
    label: "Registered Cases",
    value: "1,284",
    change: "+8.2% this month",
    icon: "cases",
    tone: "neutral",
  },
  {
    id: "high-risk-cases",
    label: "High Risk Cases",
    value: "37",
    helperText: "Require attention",
    icon: "risk",
    tone: "danger",
  },
  {
    id: "counselling-sessions",
    label: "Counselling Sessions",
    value: "892",
    helperText: "Completed this month",
    icon: "sessions",
    tone: "neutral",
  },
  {
    id: "pending-interventions",
    label: "Pending Interventions",
    value: "54",
    helperText: "Awaiting action",
    icon: "interventions",
    tone: "neutral",
  },
];

const trendDataByRange: Record<TrendRange, TrendPoint[]> = {
  "7d": [
    { label: "Mon", distressScore: 42, riskFlags: 5 },
    { label: "Tue", distressScore: 46, riskFlags: 6 },
    { label: "Wed", distressScore: 39, riskFlags: 4 },
    { label: "Thu", distressScore: 51, riskFlags: 8 },
    { label: "Fri", distressScore: 48, riskFlags: 7 },
    { label: "Sat", distressScore: 35, riskFlags: 3 },
    { label: "Sun", distressScore: 33, riskFlags: 3 },
  ],
  "30d": [
    { label: "W1", distressScore: 44, riskFlags: 22 },
    { label: "W2", distressScore: 49, riskFlags: 27 },
    { label: "W3", distressScore: 41, riskFlags: 19 },
    { label: "W4", distressScore: 47, riskFlags: 24 },
  ],
  "3m": [
    { label: "Jun", distressScore: 39, riskFlags: 71 },
    { label: "Jul", distressScore: 45, riskFlags: 88 },
    { label: "Aug", distressScore: 43, riskFlags: 82 },
  ],
};

export function getTrendData(range: TrendRange): TrendPoint[] {
  return trendDataByRange[range];
}

export const riskDistribution: RiskDistributionItem[] = [
  { level: "Low", count: 742, percentage: 58 },
  { level: "Moderate", count: 389, percentage: 30 },
  { level: "High", count: 116, percentage: 9 },
  { level: "Critical", count: 37, percentage: 3 },
];

export const priorityCases: PriorityCase[] = [
  {
    caseId: "SAH-1042",
    district: "Kurukshetra",
    state: "Haryana",
    riskLevel: "Critical",
    assignedCounsellor: "Dr. Meera Sharma",
    lastAssessment: "Today",
    interventionStatus: "Immediate Action",
  },
  {
    caseId: "SAH-1037",
    district: "Rohtak",
    state: "Haryana",
    riskLevel: "High",
    assignedCounsellor: "Ananya Verma",
    lastAssessment: "Yesterday",
    interventionStatus: "Counselling Scheduled",
  },
  {
    caseId: "SAH-1028",
    district: "Panipat",
    state: "Haryana",
    riskLevel: "High",
    assignedCounsellor: "Rahul Singh",
    lastAssessment: "2 days ago",
    interventionStatus: "Follow-up Pending",
  },
  {
    caseId: "SAH-1019",
    district: "Ambala",
    state: "Haryana",
    riskLevel: "Moderate",
    assignedCounsellor: "Priya Nair",
    lastAssessment: "3 days ago",
    interventionStatus: "Monitoring",
  },
];

export const counsellorAvailability: CounsellorAvailability = {
  available: 18,
  inSession: 7,
  unavailable: 3,
};

export const counsellorNavSections: NavSection[] = [
  {
    title: "Overview",
    items: [
      { label: "Dashboard", path: "/counsellor", icon: "LayoutDashboard" },
    ],
  },
  {
    title: "Work",
    items: [
      { label: "Cases", path: "/cases", icon: "FolderKanban" },
    ],
  },
  {
    title: "Support",
    items: [
      { label: "Sessions", path: "/sessions", icon: "CalendarClock" },
      { label: "Messages", path: "/counsellor/messages", icon: "MessageCircle" },
      { label: "Resources", path: "/resources", icon: "Library" },
    ],
  },
];

export const victimNavSections: NavSection[] = [
  {
    title: "Overview",
    items: [
      { label: "Dashboard", path: "/victim", icon: "LayoutDashboard" },
    ],
  },
  {
    title: "Support",
    items: [
      { label: "Sessions", path: "/sessions", icon: "CalendarClock" },
      { label: "Resources", path: "/resources", icon: "Library" },
    ],
  },
];