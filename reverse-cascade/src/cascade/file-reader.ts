import fs from "node:fs";
import { CascadeLevel, discoverFiles } from "./level-utils.js";

export interface CascadeFile {
  path: string;
  content: string;
}

/**
 * Read all cascade files from the data directory, mapped by level.
 */
export function readCascadeFiles(
  dataDir: string,
): Record<CascadeLevel, CascadeFile> {
  return discoverFiles(dataDir);
}

/**
 * Read a single file's current content (used for conflict detection).
 */
export function readFileContent(filePath: string): string {
  return fs.readFileSync(filePath, "utf-8");
}
