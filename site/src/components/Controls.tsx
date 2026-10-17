import { SORTS, toggle, type Filters, type SortKey, type StateFilter } from "../filters";
import { FLAGS, SEVERITY_LABELS, type FlagKey } from "../types";

interface Props {
  filters: Filters;
  onChange: (patch: Partial<Filters>) => void;
  onReset: () => void;
  activeCount: number;
}

export function Controls({ filters, onChange, onReset, activeCount }: Props) {
  return (
    <div className="controls">
      <div className="control-row">
        <label className="search">
          <span className="sr-only">Search issues</span>
          <input
            type="search"
            placeholder="Search title, text, author or #number"
            value={filters.q}
            onChange={(e) => onChange({ q: e.target.value })}
          />
        </label>
        <label className="select">
          <span>State</span>
          <select
            value={filters.state}
            onChange={(e) => onChange({ state: e.target.value as StateFilter })}
          >
            <option value="all">All</option>
            <option value="open">Open</option>
            <option value="closed">Closed</option>
          </select>
        </label>
        <label className="select">
          <span>Sort</span>
          <select value={filters.sort} onChange={(e) => onChange({ sort: e.target.value as SortKey })}>
            {SORTS.map((s) => (
              <option key={s.key} value={s.key}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="control-row">
        <div className="chips" role="group" aria-label="Jev flags">
          {FLAGS.map((f) => {
            const on = filters.flags.includes(f.key);
            return (
              <button
                key={f.key}
                type="button"
                className={`chip${on ? " on" : ""}`}
                aria-pressed={on}
                title={f.hint}
                onClick={() => onChange({ flags: toggle<FlagKey>(filters.flags, f.key) })}
              >
                {f.label}
              </button>
            );
          })}
        </div>
        <div className="chips" role="group" aria-label="Minimum severity">
          <span className="chips-label">Severity</span>
          {[0, 1, 2, 3].map((level) => {
            const on = filters.minSeverity === level;
            return (
              <button
                key={level}
                type="button"
                className={`chip${on ? " on" : ""}`}
                aria-pressed={on}
                onClick={() => onChange({ minSeverity: level })}
              >
                {level === 0 ? "Any" : `${SEVERITY_LABELS[level]}+`}
              </button>
            );
          })}
        </div>
        {activeCount > 0 && (
          <button type="button" className="link-btn" onClick={onReset}>
            Clear {activeCount} filter{activeCount === 1 ? "" : "s"}
          </button>
        )}
      </div>
    </div>
  );
}
