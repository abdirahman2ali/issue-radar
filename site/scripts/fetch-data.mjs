// Download the latest triage.json from the `data` branch for local development.
import { mkdir, writeFile } from "node:fs/promises";

const url = "https://raw.githubusercontent.com/abdirahman2ali/issue-radar/data/triage.json";
const res = await fetch(url);
if (!res.ok) {
  console.error(`Could not fetch ${url}: HTTP ${res.status}`);
  process.exit(1);
}
const text = await res.text();
const data = JSON.parse(text);
await mkdir("public", { recursive: true });
await writeFile("public/triage.json", text);
console.log(`Saved public/triage.json (${data.issues.length} issues, ${text.length} bytes)`);
