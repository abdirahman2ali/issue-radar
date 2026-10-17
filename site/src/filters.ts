import { AREAS, CATEGORIES, FLAGS, FLAG_THRESHOLD, type FlagKey, type Issue } from "./types";

export type SortKey = "urgency" | "severity" | "newest" | "comments";
export type StateFilter = "all" | "open" | "closed";
export type Facet = "categories" | "areas" | "day";

export interface Filters {
  q: string;
  categories: string[];
  areas: string[];
  minSeverity: number;
  flags: FlagKey[];
  day: string | null;
  state: StateFilter;
  sort: SortKey;
}

export const SORTS: { key: SortKey; label: string }[] = [
  { key: "urgency", label: "Most urgent" },
  { key: "severity", label: "Most severe" },
  { key: "newest", label: "Newest" },
  { key: "comments", label: "Most comments" },
];

export const DEFAULT_FILTERS: Filters = {
  q: "",
  categories: [],
  areas: [],
  minSeverity: 0,
  flags: [],
  day: null,
  state: "all",
  sort: "urgency",
};

const FLAG_KEYS = FLAGS.map((f) => f.key);
const SORT_KEYS = SORTS.map((s) => s.key);

function list(value: string | null): string[] {
  return value ? value.split(",").filter(Boolean) : [];
}

export function parseUrl(search: string): { filters: Filters; issue: number | null } {
  const p = new URLSearchParams(search);
  const sort = p.get("sort");
  const state = p.get("state");
  const sev = Number(p.get("sev"));
  const day = p.get("day");
  const issue = Number(p.get("issue"));
  return {
    filters: {
      q: p.get("q") ?? "",
      categories: list(p.get("cat")).filter((c) => c in CATEGORIES),
      areas: list(p.get("area")).filter((a) => a in AREAS),
      minSeverity: Number.isInteger(sev) && sev >= 1 && sev <= 3 ? sev : 0,
      flags: list(p.get("flag")).filter((f): f is FlagKey => FLAG_KEYS.includes(f as FlagKey)),
      day: day && /^\d{4}-\d{2}-\d{2}$/.test(day) ? day : null,
      state: state === "open" || state === "closed" ? state : "all",
      sort: SORT_KEYS.includes(sort as SortKey) ? (sort as SortKey) : DEFAULT_FILTERS.sort,
    },
    issue: Number.isInteger(issue) && issue > 0 ? issue : null,
  };
}

export function toSearch(filters: Filters, issue: number | null): string {
  const p = new URLSearchParams();
  if (filters.q) p.set("q", filters.q);
  if (filters.categories.length) p.set("cat", filters.categories.join(","));
  if (filters.areas.length) p.set("area", filters.areas.join(","));
  if (filters.minSeverity) p.set("sev", String(filters.minSeverity));
  if (filters.flags.length) p.set("flag", filters.flags.join(","));
  if (filters.day) p.set("day", filters.day);
  if (filters.state !== "all") p.set("state", filters.state);
  if (filters.sort !== DEFAULT_FILTERS.sort) p.set("sort", filters.sort);
  if (issue) p.set("issue", String(issue));
  const s = p.toString();
  return s ? `?${s}` : "";
}

export function dayOf(issue: Issue): string {
  return issue.created_at.slice(0, 10);
}

export function isFlagged(issue: Issue, flag: FlagKey): boolean {
  return issue.answers[flag].noul >= FLAG_THRESHOLD;
}

/** Apply every filter except the one for `skip`, so a facet's own counts stay selectable. */
export function applyFilters(issues: Issue[], f: Filters, skip?: Facet): Issue[] {
  const q = f.q.trim().toLowerCase();
  return issues.filter((i) => {
    if (q && !`${i.title} ${i.excerpt} #${i.number} ${i.author ?? ""}`.toLowerCase().includes(q)) {
      return false;
    }
    if (f.state !== "all" && i.state !== f.state) return false;
    if (skip !== "categories" && f.categories.length && !f.categories.includes(i.answers.category.choice)) {
      return false;
    }
    if (skip !== "areas" && f.areas.length && !f.areas.includes(i.answers.area.choice)) return false;
    if (skip !== "day" && f.day && dayOf(i) !== f.day) return false;
    if (f.minSeverity && i.answers.severity.score < f.minSeverity - 0.5) return false;
    return f.flags.every((flag) => isFlagged(i, flag));
  });
}

export function sortIssues(issues: Issue[], sort: SortKey): Issue[] {
  const byNewest = (a: Issue, b: Issue) => b.created_at.localeCompare(a.created_at);
  const keyed: Record<SortKey, (a: Issue, b: Issue) => number> = {
    urgency: (a, b) => b.answers.is_urgent.noul - a.answers.is_urgent.noul || byNewest(a, b),
    severity: (a, b) => b.answers.severity.score - a.answers.severity.score || byNewest(a, b),
    newest: byNewest,
    comments: (a, b) => b.comments - a.comments || byNewest(a, b),
  };
  return [...issues].sort(keyed[sort]);
}

export interface Bar {
  key: string;
  label: string;
  value: number;
}

export function countBy(issues: Issue[], pick: (i: Issue) => string, labels: Record<string, string>): Bar[] {
  const counts = new Map<string, number>();
  for (const i of issues) counts.set(pick(i), (counts.get(pick(i)) ?? 0) + 1);
  return Object.entries(labels)
    .map(([key, label]) => ({ key, label, value: counts.get(key) ?? 0 }))
    .sort((a, b) => b.value - a.value);
}

/** One bar per calendar day (UTC) between the first and last day, zeros included. */
export function dailyCounts(issues: Issue[]): Bar[] {
  if (!issues.length) return [];
  const counts = new Map<string, number>();
  for (const i of issues) counts.set(dayOf(i), (counts.get(dayOf(i)) ?? 0) + 1);
  const days = [...counts.keys()].sort();
  const first = days[0];
  const last = days[days.length - 1];
  if (!first || !last) return [];
  const out: Bar[] = [];
  for (let t = Date.parse(`${first}T00:00:00Z`); t <= Date.parse(`${last}T00:00:00Z`); t += 86_400_000) {
    const key = new Date(t).toISOString().slice(0, 10);
    out.push({ key, label: key, value: counts.get(key) ?? 0 });
  }
  return out;
}

export function toggle<T>(items: T[], item: T): T[] {
  return items.includes(item) ? items.filter((x) => x !== item) : [...items, item];
}

export function activeFilterCount(f: Filters): number {
  return (
    (f.q.trim() ? 1 : 0) +
    f.categories.length +
    f.areas.length +
    (f.minSeverity ? 1 : 0) +
    f.flags.length +
    (f.day ? 1 : 0) +
    (f.state !== "all" ? 1 : 0)
  );
}
