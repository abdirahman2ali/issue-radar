import { describe, expect, it } from "vitest";
import {
  DEFAULT_FILTERS,
  REPEAT_REPORTER_THRESHOLD,
  activeFilterCount,
  applyFilters,
  completeRange,
  dailyCounts,
  onlyCompleteDays,
  parseUrl,
  repeatReporters,
  sortIssues,
  toSearch,
  toggle,
  type Filters,
} from "./filters";
import type { Issue, Triage } from "./types";

function issue(n: number, over: Partial<Issue> = {}, urgent = 0.1, severity = 1): Issue {
  return {
    repo: "o/r",
    number: n,
    title: `Issue ${n}`,
    url: `https://github.com/o/r/issues/${n}`,
    author: "someone",
    state: "open",
    labels: [],
    comments: 0,
    created_at: "2026-10-15T10:00:00Z",
    updated_at: "2026-10-15T10:00:00Z",
    excerpt: "it breaks when I run it",
    model: "jev-1",
    classified_at: "2026-10-16T00:00:00Z",
    answers: {
      category: { choice: "bug", confidence: 1, probabilities: { bug: 1 } },
      area: { choice: "cli_terminal", confidence: 1, probabilities: { cli_terminal: 1 } },
      severity: { score: severity, confidence: 1, probabilities: { "1": 1 } },
      is_urgent: { noul: urgent },
      is_regression: { noul: 0.1 },
      has_repro: { noul: 0.1 },
      needs_info: { noul: 0.1 },
    },
    ...over,
  };
}

const f = (over: Partial<Filters>): Filters => ({ ...DEFAULT_FILTERS, ...over });

describe("url state", () => {
  it("round trips filters and the selected issue", () => {
    const filters = f({
      q: "crash",
      categories: ["bug"],
      areas: ["mcp_tools"],
      minSeverity: 2,
      flags: ["is_urgent"],
      day: "2026-10-15",
      state: "open",
      sort: "newest",
    });
    const parsed = parseUrl(toSearch(filters, 42));
    expect(parsed.filters).toEqual(filters);
    expect(parsed.issue).toBe(42);
  });

  it("drops unknown or malformed values", () => {
    const { filters, issue: sel } = parseUrl(
      "?cat=bug,nope&area=zzz&sev=9&flag=is_urgent,evil&day=yesterday&state=weird&sort=hack&issue=abc",
    );
    expect(filters.categories).toEqual(["bug"]);
    expect(filters.areas).toEqual([]);
    expect(filters.minSeverity).toBe(0);
    expect(filters.flags).toEqual(["is_urgent"]);
    expect(filters.day).toBeNull();
    expect(filters.state).toBe("all");
    expect(filters.sort).toBe("urgency");
    expect(sel).toBeNull();
  });

  it("serializes defaults to an empty query", () => {
    expect(toSearch(DEFAULT_FILTERS, null)).toBe("");
  });
});

describe("applyFilters", () => {
  const issues = [
    issue(1, { title: "Crash on start" }, 0.9, 3),
    issue(2, { state: "closed" }, 0.1, 0),
    issue(3, { created_at: "2026-10-14T10:00:00Z" }, 0.2, 2),
  ];

  it("filters by text, state, severity, flags and day", () => {
    expect(applyFilters(issues, f({ q: "crash" })).map((i) => i.number)).toEqual([1]);
    expect(applyFilters(issues, f({ state: "closed" })).map((i) => i.number)).toEqual([2]);
    expect(applyFilters(issues, f({ minSeverity: 2 })).map((i) => i.number)).toEqual([1, 3]);
    expect(applyFilters(issues, f({ flags: ["is_urgent"] })).map((i) => i.number)).toEqual([1]);
    expect(applyFilters(issues, f({ day: "2026-10-14" })).map((i) => i.number)).toEqual([3]);
  });

  it("skips one facet so its own counts stay selectable", () => {
    const filters = f({ day: "2026-10-14" });
    expect(applyFilters(issues, filters, "day")).toHaveLength(3);
  });
});

describe("sorting and helpers", () => {
  it("sorts by urgency then newest", () => {
    const list = [issue(1, {}, 0.2), issue(2, {}, 0.9), issue(3, {}, 0.9, 1)];
    expect(sortIssues(list, "urgency").map((i) => i.number)).toEqual([2, 3, 1]);
  });

  it("fills empty days in the daily series", () => {
    const list = [
      issue(1, { created_at: "2026-10-10T01:00:00Z" }),
      issue(2, { created_at: "2026-10-12T23:00:00Z" }),
    ];
    expect(dailyCounts(list).map((b) => [b.key, b.value])).toEqual([
      ["2026-10-10", 1],
      ["2026-10-11", 0],
      ["2026-10-12", 1],
    ]);
  });

  it("toggles list membership", () => {
    expect(toggle(["a"], "b")).toEqual(["a", "b"]);
    expect(toggle(["a", "b"], "a")).toEqual(["b"]);
  });
});

describe("complete days", () => {
  const at = (day: string, hour = 10) => `${day}T${String(hour).padStart(2, "0")}:00:00Z`;
  const issues = [
    issue(1, { created_at: at("2026-10-10") }), // oldest, partial
    issue(2, { created_at: at("2026-10-11") }),
    issue(3, { created_at: at("2026-10-17", 23) }),
    issue(4, { created_at: at("2026-10-18", 1) }), // today, still filling up
  ];
  const triage = (over: Partial<Triage> = {}): Triage => ({
    generated_at: "2026-10-18T06:17:00Z",
    watermark: null,
    model: "jev",
    issues,
    ...over,
  });

  it("keeps only the days the pipeline says are complete", () => {
    const t = triage({ complete_days: { from: "2026-10-11", through: "2026-10-17" } });
    expect(onlyCompleteDays(t).map((i) => i.number)).toEqual([2, 3]);
  });

  it("falls back to hiding the day the data was generated when the field is missing", () => {
    expect(completeRange(triage())).toEqual({ from: null, through: "2026-10-17" });
    expect(onlyCompleteDays(triage()).map((i) => i.number)).toEqual([1, 2, 3]);
  });

  it("shows everything when there is no timestamp and no range", () => {
    expect(onlyCompleteDays(triage({ generated_at: null })).map((i) => i.number)).toEqual([1, 2, 3, 4]);
  });

  it("makes the daily chart start and end on complete days", () => {
    const t = triage({ complete_days: { from: "2026-10-11", through: "2026-10-17" } });
    const bars = dailyCounts(onlyCompleteDays(t));
    expect(bars[0]?.key).toBe("2026-10-11");
    expect(bars[bars.length - 1]?.key).toBe("2026-10-17");
  });
});

describe("hide repeat reporters", () => {
  const T = REPEAT_REPORTER_THRESHOLD;
  const by = (author: string | null, count: number, start = 1000): Issue[] =>
    Array.from({ length: count }, (_, k) => issue(start + k, { author }));
  const hide = f({ hideRepeat: true });

  it("uses a threshold of 20", () => {
    expect(T).toBe(20);
  });

  it("is off by default and shows everything when off", () => {
    const issues = [...by("busy", T + 1), ...by("quiet", 2, 2000)];
    expect(DEFAULT_FILTERS.hideRepeat).toBe(false);
    expect(applyFilters(issues, DEFAULT_FILTERS)).toHaveLength(issues.length);
  });

  it("hides authors above and exactly at the threshold, keeps just below", () => {
    const issues = [
      ...by("over", T + 1, 1000),
      ...by("exact", T, 2000),
      ...by("below", T - 1, 3000),
    ];
    const kept = applyFilters(issues, hide);
    expect(kept).toHaveLength(T - 1);
    expect(kept.every((i) => i.author === "below")).toBe(true);
  });

  it("handles empty data", () => {
    expect(applyFilters([], hide)).toEqual([]);
    expect(repeatReporters([])).toEqual(new Set());
  });

  it("never hides or groups null, empty or blank authors", () => {
    const issues = [...by(null, T + 5, 1000), ...by("", T, 2000), ...by("  ", T, 3000)];
    expect(applyFilters(issues, hide)).toHaveLength(issues.length);
    expect(repeatReporters(issues).size).toBe(0);
  });

  it("counts __proto__ and constructor like any other name", () => {
    const issues = [
      ...by("__proto__", T, 1000),
      ...by("constructor", T, 2000),
      ...by("toString", T - 1, 3000),
      ...by("other", 1, 4000),
    ];
    expect(repeatReporters(issues)).toEqual(new Set(["__proto__", "constructor"]));
    const kept = applyFilters(issues, hide);
    expect(kept.map((i) => i.author)).toEqual([...Array(T - 1).fill("toString"), "other"]);
  });

  it("hidden count equals the number of issues removed", () => {
    const issues = [...by("busy", T, 1000), ...by("quiet", 3, 2000)];
    const removed = applyFilters(issues, f({ hideRepeat: false })).length - applyFilters(issues, hide).length;
    expect(removed).toBe(T);
  });

  it("counts authors on the full set, not the other-filtered subset", () => {
    const issues = [
      ...by("busy", T - 1, 1000),
      issue(2000, { author: "busy", state: "closed" }),
      ...by("quiet", 2, 3000),
    ];
    const kept = applyFilters(issues, f({ hideRepeat: true, state: "closed" }));
    expect(kept).toEqual([]);
    expect(applyFilters(issues, f({ hideRepeat: true, q: "Issue 30" })).every((i) => i.author === "quiet")).toBe(true);
  });

  it("round trips through the URL and counts as an active filter", () => {
    expect(toSearch(hide, null)).toBe("?repeat=hide");
    expect(parseUrl("?repeat=hide").filters.hideRepeat).toBe(true);
    expect(toSearch(DEFAULT_FILTERS, null)).toBe("");
    expect(activeFilterCount(hide)).toBe(1);
    expect(activeFilterCount(DEFAULT_FILTERS)).toBe(0);
  });

  it("treats any other repeat value as off, including prototype names", () => {
    for (const v of ["", "show", "true", "1", "HIDE", "__proto__", "constructor"]) {
      expect(parseUrl(`?repeat=${v}`).filters.hideRepeat).toBe(false);
    }
    expect(parseUrl("").filters.hideRepeat).toBe(false);
  });
});
