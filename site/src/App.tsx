import { useCallback, useEffect, useMemo, useState } from "react";
import { DailyChart, RowsChart } from "./components/Charts";
import { Controls } from "./components/Controls";
import { Drawer } from "./components/Drawer";
import { IssueList } from "./components/IssueList";
import { loadTriage, relativeTime, shortDay } from "./data";
import {
  DEFAULT_FILTERS,
  activeFilterCount,
  applyFilters,
  completeRange,
  countBy,
  dailyCounts,
  isFlagged,
  onlyCompleteDays,
  parseUrl,
  sortIssues,
  toSearch,
  toggle,
  type Filters,
} from "./filters";
import { AREAS, CATEGORIES, type Triage } from "./types";

const PAGE = 40;
type Theme = "system" | "light" | "dark";

function readTheme(): Theme {
  try {
    const t = localStorage.getItem("theme");
    return t === "light" || t === "dark" ? t : "system";
  } catch {
    return "system";
  }
}

function applyTheme(theme: Theme) {
  if (theme === "system") delete document.documentElement.dataset.theme;
  else document.documentElement.dataset.theme = theme;
  try {
    if (theme === "system") localStorage.removeItem("theme");
    else localStorage.setItem("theme", theme);
  } catch {
    /* storage can be blocked, the theme still applies for this visit */
  }
}

function Stat({ label, value, hint }: { label: string; value: number; hint: string }) {
  return (
    <div className="stat" title={hint}>
      <span className="stat-value">{value.toLocaleString()}</span>
      <span className="stat-label">{label}</span>
    </div>
  );
}

export function App() {
  const initial = useMemo(() => parseUrl(window.location.search), []);
  const [triage, setTriage] = useState<Triage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<Filters>(initial.filters);
  const [selected, setSelected] = useState<number | null>(initial.issue);
  const [visible, setVisible] = useState(PAGE);
  const [theme, setTheme] = useState<Theme>(readTheme);

  useEffect(() => {
    loadTriage().then(setTriage, (e: unknown) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  useEffect(() => applyTheme(theme), [theme]);

  useEffect(() => {
    const onPop = () => {
      const p = parseUrl(window.location.search);
      setFilters(p.filters);
      setSelected(p.issue);
    };
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  const change = useCallback((patch: Partial<Filters>) => {
    setFilters((prev) => {
      const next = { ...prev, ...patch };
      window.history.replaceState(null, "", toSearch(next, selected) || window.location.pathname);
      return next;
    });
    setVisible(PAGE);
  }, [selected]);

  const select = useCallback(
    (n: number | null) => {
      setSelected(n);
      const search = toSearch(filters, n) || window.location.pathname;
      if (n) window.history.pushState(null, "", search);
      else window.history.replaceState(null, "", search);
    },
    [filters],
  );

  const allIssues = useMemo(() => triage?.issues ?? [], [triage]);
  const issues = useMemo(() => (triage ? onlyCompleteDays(triage) : []), [triage]);
  const range = triage ? completeRange(triage) : null;
  const shown = useMemo(() => sortIssues(applyFilters(issues, filters), filters.sort), [issues, filters]);
  const categoryBars = useMemo(
    () => countBy(applyFilters(issues, filters, "categories"), (i) => i.answers.category.choice, CATEGORIES),
    [issues, filters],
  );
  const areaBars = useMemo(
    () => countBy(applyFilters(issues, filters, "areas"), (i) => i.answers.area.choice, AREAS),
    [issues, filters],
  );
  const dayBars = useMemo(() => dailyCounts(applyFilters(issues, filters, "day")), [issues, filters]);
  const active = activeFilterCount(filters);
  // Look in every issue, not just the complete days, so a shared link to a newer issue still opens.
  const selectedIssue = selected ? allIssues.find((i) => i.number === selected) : undefined;

  if (error) {
    return (
      <main className="page">
        <h1>Issue Radar</h1>
        <p className="error" role="alert">
          {error}
        </p>
      </main>
    );
  }
  if (!triage) {
    return (
      <main className="page">
        <h1>Issue Radar</h1>
        <p className="muted">Loading triage data…</p>
      </main>
    );
  }

  return (
    <main className="page">
      <header className="top">
        <div>
          <h1>Issue Radar</h1>
          <p className="muted">
            Every new <strong>anthropics/claude-code</strong> issue, classified by Jev. Refreshed daily
            {triage.generated_at ? `, last run ${relativeTime(triage.generated_at)}` : ""}.
          </p>
          {range?.from && range.through && (
            <p className="muted">
              UTC days: {shortDay(range.from)} to {shortDay(range.through)}. {shortDay(range.through)} is
              still filling up.
            </p>
          )}
        </div>
        <button
          type="button"
          className="theme"
          onClick={() => setTheme(theme === "dark" ? "light" : theme === "light" ? "system" : "dark")}
          title="Switch theme"
        >
          Theme: {theme}
        </button>
      </header>

      <section className="stats" aria-label="Summary of current filters">
        <Stat label="Issues" value={shown.length} hint="Issues matching the current filters" />
        <Stat
          label="Bugs"
          value={shown.filter((i) => i.answers.category.choice === "bug").length}
          hint="Classified as bug reports"
        />
        <Stat
          label="Urgent"
          value={shown.filter((i) => isFlagged(i, "is_urgent")).length}
          hint="Urgency probability of 50% or more"
        />
        <Stat
          label="Regressions"
          value={shown.filter((i) => isFlagged(i, "is_regression")).length}
          hint="Used to work, broke after an update"
        />
      </section>

      <section className="charts" aria-label="Charts">
        <DailyChart bars={dayBars} day={filters.day} onPick={(day) => change({ day })} />
        <RowsChart
          title="By category"
          subtitle="What kind of issue. Click to filter."
          bars={categoryBars}
          selected={filters.categories}
          onToggle={(k) => change({ categories: toggle(filters.categories, k) })}
        />
        <RowsChart
          title="By area"
          subtitle="Which part of the product. Click to filter."
          bars={areaBars}
          selected={filters.areas}
          onToggle={(k) => change({ areas: toggle(filters.areas, k) })}
        />
      </section>

      <Controls
        filters={filters}
        onChange={change}
        onReset={() => change({ ...DEFAULT_FILTERS, sort: filters.sort })}
        activeCount={active}
      />

      <p className="count" aria-live="polite">
        Showing {Math.min(visible, shown.length)} of {shown.length} issues
      </p>
      <IssueList
        issues={shown}
        visible={visible}
        selected={selected}
        onSelect={select}
        onMore={() => setVisible((v) => v + PAGE)}
      />

      {selectedIssue && <Drawer issue={selectedIssue} onClose={() => select(null)} />}

      <footer className="foot">
        Classified by Jev (<code>{triage.model}</code>) from TypeSafe AI. Probabilities are the model's, not
        a maintainer's judgment. Source on{" "}
        <a href="https://github.com/abdirahman2ali/issue-radar" rel="noopener noreferrer">
          GitHub
        </a>
        .
      </footer>
    </main>
  );
}
