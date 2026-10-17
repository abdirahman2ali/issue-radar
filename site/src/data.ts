import type { Triage } from "./types";

export async function loadTriage(): Promise<Triage> {
  const res = await fetch(`${import.meta.env.BASE_URL}triage.json`, { cache: "no-cache" });
  if (!res.ok) throw new Error(`Could not load triage data (HTTP ${res.status})`);
  const data = (await res.json()) as Triage;
  if (!Array.isArray(data.issues)) throw new Error("triage.json has no issues list");
  return data;
}

/** Only ever link to github.com, even though the pipeline already filters URLs. */
export function safeUrl(url: string): string | undefined {
  try {
    const u = new URL(url);
    return u.protocol === "https:" && u.hostname === "github.com" ? u.href : undefined;
  } catch {
    return undefined;
  }
}

const rtf = new Intl.RelativeTimeFormat("en", { numeric: "auto" });

export function relativeTime(iso: string, now = Date.now()): string {
  const mins = Math.round((Date.parse(iso) - now) / 60_000);
  const abs = Math.abs(mins);
  if (abs < 60) return rtf.format(mins, "minute");
  if (abs < 60 * 24) return rtf.format(Math.round(mins / 60), "hour");
  return rtf.format(Math.round(mins / (60 * 24)), "day");
}

export function shortDay(day: string): string {
  return new Date(`${day}T00:00:00Z`).toLocaleDateString("en", {
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  });
}
