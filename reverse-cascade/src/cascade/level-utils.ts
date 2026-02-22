import path from "node:path";
import fs from "node:fs";

export type CascadeLevel = "day" | "week" | "month" | "quarter" | "year";

/** Propagation order: upward from day to year */
export const LEVELS_ASCENDING: CascadeLevel[] = [
  "day",
  "week",
  "month",
  "quarter",
  "year",
];

export function getNextLevelUp(
  level: CascadeLevel,
): CascadeLevel | null {
  const idx = LEVELS_ASCENDING.indexOf(level);
  if (idx === -1 || idx === LEVELS_ASCENDING.length - 1) return null;
  return LEVELS_ASCENDING[idx + 1];
}

export function isAbove(a: CascadeLevel, b: CascadeLevel): boolean {
  return LEVELS_ASCENDING.indexOf(a) > LEVELS_ASCENDING.indexOf(b);
}

/**
 * Match a cascade data file to its level based on filename patterns.
 * Returns null for files that don't map to a level (tracker.csv, adaptations.md, etc.)
 */
export function fileToLevel(filename: string): CascadeLevel | null {
  const name = path.basename(filename).toLowerCase();

  // day-feb-17-2026.md or similar — not used yet, but future-proofed
  if (name.startsWith("day-")) return "day";

  // week-feb14-20.md
  if (name.startsWith("week-")) return "week";

  // feb-2026.md (month files)
  const monthPattern =
    /^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)-\d{4}\.md$/;
  if (monthPattern.test(name)) return "month";

  // q1-jan-feb-mar.md (quarter files)
  if (/^q\d-/.test(name)) return "quarter";

  // 2026-goals.md (year files)
  if (/^\d{4}-goals\.md$/.test(name)) return "year";

  return null;
}

/**
 * Scan the data directory and map each cascade file to its level.
 */
export function discoverFiles(
  dataDir: string,
): Record<CascadeLevel, { path: string; content: string }> {
  const result: Partial<
    Record<CascadeLevel, { path: string; content: string }>
  > = {};

  if (!fs.existsSync(dataDir)) {
    throw new Error(`Data directory not found: ${dataDir}`);
  }

  const files = fs.readdirSync(dataDir).filter((f) => f.endsWith(".md"));

  for (const file of files) {
    const level = fileToLevel(file);
    if (!level) continue;

    const filePath = path.join(dataDir, file);
    const content = fs.readFileSync(filePath, "utf-8");

    // For levels with multiple files (e.g., multiple week files),
    // pick the most recently modified one
    if (
      !result[level] ||
      fs.statSync(filePath).mtimeMs >
        fs.statSync(result[level]!.path).mtimeMs
    ) {
      result[level] = { path: filePath, content };
    }
  }

  return result as Record<CascadeLevel, { path: string; content: string }>;
}
