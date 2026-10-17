import { relativeTime } from "../data";
import { isFlagged } from "../filters";
import { AREAS, CATEGORIES, FLAGS, SEVERITY_LABELS, type Issue } from "../types";

export function severityLevel(score: number): number {
  return Math.min(3, Math.max(0, Math.round(score)));
}

export function Severity({ score }: { score: number }) {
  const level = severityLevel(score);
  return (
    <span className="severity" title={`Severity ${score.toFixed(1)} of 3`}>
      <span className="pips" aria-hidden="true">
        {[0, 1, 2, 3].map((i) => (
          <span key={i} className={`pip${i <= level ? " filled" : ""}`} />
        ))}
      </span>
      {SEVERITY_LABELS[level]}
    </span>
  );
}

interface Props {
  issues: Issue[];
  visible: number;
  selected: number | null;
  onSelect: (n: number) => void;
  onMore: () => void;
}

export function IssueList({ issues, visible, selected, onSelect, onMore }: Props) {
  if (!issues.length) {
    return <p className="empty">No issues match these filters.</p>;
  }
  return (
    <>
      <ul className="issues">
        {issues.slice(0, visible).map((i) => {
          const flags = FLAGS.filter((f) => isFlagged(i, f.key));
          return (
            <li key={i.number}>
              <button
                type="button"
                className={`issue${selected === i.number ? " on" : ""}`}
                onClick={() => onSelect(i.number)}
              >
                <span className="issue-meta">
                  <span>#{i.number}</span>
                  <span>{i.author ?? "unknown"}</span>
                  <span>{relativeTime(i.created_at)}</span>
                  <span className={`state ${i.state}`}>{i.state}</span>
                </span>
                <span className="issue-title">{i.title}</span>
                <span className="issue-excerpt">{i.excerpt}</span>
                <span className="issue-tags">
                  <span className="badge">{CATEGORIES[i.answers.category.choice] ?? "Other"}</span>
                  <span className="muted">{AREAS[i.answers.area.choice] ?? "Other"}</span>
                  <Severity score={i.answers.severity.score} />
                  {flags.map((f) => (
                    <span key={f.key} className={`flag ${f.key}`}>
                      {f.label}
                    </span>
                  ))}
                  {i.comments > 0 && <span className="muted">{i.comments} comments</span>}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
      {visible < issues.length && (
        <button type="button" className="more" onClick={onMore}>
          Show more ({issues.length - visible} left)
        </button>
      )}
    </>
  );
}
