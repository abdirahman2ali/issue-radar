export interface ChoiceAnswer {
  choice: string;
  confidence: number;
  probabilities: Record<string, number>;
}

export interface ScoreAnswer {
  score: number;
  confidence: number;
  probabilities: Record<string, number>;
}

export interface NoulAnswer {
  noul: number;
}

export type FlagKey = "is_urgent" | "is_regression" | "has_repro" | "needs_info";

export interface Answers {
  category: ChoiceAnswer;
  area: ChoiceAnswer;
  severity: ScoreAnswer;
  is_urgent: NoulAnswer;
  is_regression: NoulAnswer;
  has_repro: NoulAnswer;
  needs_info: NoulAnswer;
}

export interface Issue {
  repo: string;
  number: number;
  title: string;
  url: string;
  author: string | null;
  state: "open" | "closed";
  labels: string[];
  comments: number;
  created_at: string;
  updated_at: string;
  excerpt: string;
  answers: Answers;
  model: string;
  classified_at: string;
}

export interface Triage {
  generated_at: string | null;
  watermark: string | null;
  model: string;
  issues: Issue[];
}

export const CATEGORIES: Record<string, string> = {
  bug: "Bug",
  feature_request: "Feature request",
  question: "Question",
  docs: "Docs",
  other: "Other",
};

export const AREAS: Record<string, string> = {
  cli_terminal: "CLI and terminal",
  ide_integration: "IDE integration",
  mcp_tools: "MCP and tools",
  permissions_security: "Permissions and security",
  performance: "Performance",
  auth_billing: "Auth and billing",
  other: "Other",
};

export const FLAGS: { key: FlagKey; label: string; hint: string }[] = [
  { key: "is_urgent", label: "Urgent", hint: "Conveys urgency or time sensitivity" },
  { key: "is_regression", label: "Regression", hint: "Used to work, broke after an update" },
  { key: "has_repro", label: "Has repro", hint: "Includes clear steps to reproduce" },
  { key: "needs_info", label: "Needs info", hint: "Maintainers would need to ask for more" },
];

export const SEVERITY_LABELS = ["Minor", "Moderate", "Major", "Blocking"] as const;

/** A yes/no answer counts as true at or above this probability. */
export const FLAG_THRESHOLD = 0.5;
