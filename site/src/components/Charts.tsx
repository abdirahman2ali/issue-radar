import { shortDay } from "../data";
import type { Bar } from "../filters";

interface PanelProps {
  title: string;
  subtitle: string;
  children: React.ReactNode;
  table: Bar[];
}

function Panel({ title, subtitle, children, table }: PanelProps) {
  return (
    <section className="panel" aria-label={title}>
      <h2>{title}</h2>
      <p className="muted">{subtitle}</p>
      {children}
      <details className="table-view">
        <summary>View as table</summary>
        <table>
          <tbody>
            {table.map((b) => (
              <tr key={b.key}>
                <th scope="row">{b.label}</th>
                <td>{b.value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </section>
  );
}

interface RowsProps {
  title: string;
  subtitle: string;
  bars: Bar[];
  selected: string[];
  onToggle: (key: string) => void;
}

/** Horizontal bars, one row per category. Clicking a row filters the board. */
export function RowsChart({ title, subtitle, bars, selected, onToggle }: RowsProps) {
  const max = Math.max(1, ...bars.map((b) => b.value));
  return (
    <Panel title={title} subtitle={subtitle} table={bars}>
      <ul className="rows">
        {bars.map((b) => {
          const on = selected.includes(b.key);
          const dim = selected.length > 0 && !on;
          return (
            <li key={b.key}>
              <button
                type="button"
                className={`row-btn${on ? " on" : ""}${dim ? " dim" : ""}`}
                aria-pressed={on}
                title={`${b.label}: ${b.value} issues`}
                onClick={() => onToggle(b.key)}
              >
                <span className="row-label">{b.label}</span>
                <span className="track">
                  <span className="fill" style={{ width: `${(b.value / max) * 100}%` }} />
                </span>
                <span className="row-value">{b.value}</span>
              </button>
            </li>
          );
        })}
      </ul>
    </Panel>
  );
}

interface DailyProps {
  bars: Bar[];
  day: string | null;
  onPick: (day: string | null) => void;
}

/** One vertical bar per day. Clicking a bar filters to that day, clicking again clears it. */
export function DailyChart({ bars, day, onPick }: DailyProps) {
  const max = Math.max(1, ...bars.map((b) => b.value));
  return (
    <Panel title="Issues per day" subtitle="Created, UTC. Click a day to filter." table={bars}>
      <div className="daily" role="group" aria-label="Issues per day">
        {bars.map((b) => {
          const on = day === b.key;
          const dim = day !== null && !on;
          return (
            <button
              key={b.key}
              type="button"
              className={`col${on ? " on" : ""}${dim ? " dim" : ""}`}
              aria-pressed={on}
              title={`${shortDay(b.key)}: ${b.value} issues`}
              onClick={() => onPick(on ? null : b.key)}
            >
              <span className="col-value">{b.value}</span>
              <span className="col-bar" style={{ height: `${(b.value / max) * 100}%` }} />
              <span className="col-label">{shortDay(b.key)}</span>
            </button>
          );
        })}
      </div>
    </Panel>
  );
}
