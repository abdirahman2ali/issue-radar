import { useEffect, useRef } from "react";
import { relativeTime, safeUrl } from "../data";
import { AREAS, CATEGORIES, FLAGS, FLAG_THRESHOLD, SEVERITY_LABELS, type Issue } from "../types";
import { Severity } from "./IssueList";

function ProbBars({
  title,
  entries,
  chosen,
}: {
  title: string;
  entries: { key: string; label: string; p: number }[];
  chosen: string;
}) {
  return (
    <div className="prob">
      <h4>{title}</h4>
      {entries.map((e) => (
        <div key={e.key} className={`prob-row${e.key === chosen ? " chosen" : ""}`}>
          <span className="prob-label">{e.label}</span>
          <span className="track">
            <span className="fill" style={{ width: `${Math.round(e.p * 100)}%` }} />
          </span>
          <span className="prob-value">{Math.round(e.p * 100)}%</span>
        </div>
      ))}
    </div>
  );
}

function fromProbabilities(p: Record<string, number>, labels: Record<string, string>) {
  return Object.entries(p)
    .map(([key, value]) => ({ key, label: labels[key] ?? key, p: value }))
    .sort((a, b) => b.p - a.p);
}

export function Drawer({ issue, onClose }: { issue: Issue; onClose: () => void }) {
  const closeRef = useRef<HTMLButtonElement>(null);
  const href = safeUrl(issue.url);
  const a = issue.answers;

  useEffect(() => {
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const severityLabels = Object.fromEntries(SEVERITY_LABELS.map((l, i) => [String(i), l]));

  return (
    <div className="drawer-wrap">
      <button type="button" className="backdrop" aria-label="Close details" onClick={onClose} />
      <aside className="drawer" role="dialog" aria-modal="true" aria-label={`Issue ${issue.number}`}>
        <header>
          <div>
            <p className="muted">
              {issue.repo} #{issue.number} · {issue.author ?? "unknown"} · {relativeTime(issue.created_at)} ·{" "}
              {issue.state}
            </p>
            <h2>{issue.title}</h2>
          </div>
          <button ref={closeRef} type="button" className="close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </header>

        <div className="issue-tags">
          <span className="badge">{CATEGORIES[a.category.choice] ?? "Other"}</span>
          <span className="muted">{AREAS[a.area.choice] ?? "Other"}</span>
          <Severity score={a.severity.score} />
        </div>

        {issue.excerpt && <p className="excerpt">{issue.excerpt}</p>}
        {issue.labels.length > 0 && (
          <p className="muted">Labels: {issue.labels.join(", ")}</p>
        )}
        {href && (
          <a className="gh-link" href={href} target="_blank" rel="noopener noreferrer">
            Open on GitHub
          </a>
        )}

        <h3>What Jev thinks</h3>
        <ProbBars
          title={`Category (confidence ${Math.round(a.category.confidence * 100)}%)`}
          entries={fromProbabilities(a.category.probabilities, CATEGORIES)}
          chosen={a.category.choice}
        />
        <ProbBars
          title={`Area (confidence ${Math.round(a.area.confidence * 100)}%)`}
          entries={fromProbabilities(a.area.probabilities, AREAS)}
          chosen={a.area.choice}
        />
        <ProbBars
          title={`Severity (confidence ${Math.round(a.severity.confidence * 100)}%)`}
          entries={Object.entries(a.severity.probabilities)
            .map(([key, p]) => ({ key, label: severityLabels[key] ?? key, p }))
            .sort((x, y) => Number(x.key) - Number(y.key))}
          chosen={String(Math.round(a.severity.score))}
        />
        <div className="prob">
          <h4>Flags (true at {Math.round(FLAG_THRESHOLD * 100)}% or more)</h4>
          {FLAGS.map((f) => {
            const p = a[f.key].noul;
            return (
              <div key={f.key} className={`prob-row${p >= FLAG_THRESHOLD ? " chosen" : ""}`}>
                <span className="prob-label" title={f.hint}>
                  {f.label}
                </span>
                <span className="track">
                  <span className="fill" style={{ width: `${Math.round(p * 100)}%` }} />
                </span>
                <span className="prob-value">{Math.round(p * 100)}%</span>
              </div>
            );
          })}
        </div>
        <p className="muted foot">
          Classified {relativeTime(issue.classified_at)} by {issue.model}
        </p>
      </aside>
    </div>
  );
}
