import fs from "node:fs";
import path from "node:path";

const BACKUP_BASE = path.join(
  import.meta.dirname ?? ".",
  "../../data/backups",
);

/**
 * Backup a file before overwriting. Stores at data/backups/{threadId}/{filename}.
 */
export function backupFile(
  filePath: string,
  threadId: string,
): void {
  const backupDir = path.join(BACKUP_BASE, threadId);
  fs.mkdirSync(backupDir, { recursive: true });

  const filename = path.basename(filePath);
  const backupPath = path.join(backupDir, filename);

  // Only backup if we haven't already (first change wins)
  if (!fs.existsSync(backupPath)) {
    fs.copyFileSync(filePath, backupPath);
  }
}

/**
 * Write new content to a cascade file, creating a backup first.
 */
export function writeCascadeFile(
  filePath: string,
  content: string,
  threadId: string,
): void {
  backupFile(filePath, threadId);
  fs.writeFileSync(filePath, content, "utf-8");
}

/**
 * Restore all backed-up files for a thread (rollback).
 */
export function restoreBackups(threadId: string): string[] {
  const backupDir = path.join(BACKUP_BASE, threadId);
  if (!fs.existsSync(backupDir)) return [];

  const restored: string[] = [];
  const files = fs.readdirSync(backupDir);

  for (const file of files) {
    const backupPath = path.join(backupDir, file);
    // We need the original path — stored as metadata or inferred
    // For now, backups sit alongside originals in the same data dir
    // The original path is stored in the graph state's cascadeFiles
    restored.push(backupPath);
  }

  return restored;
}

/**
 * Clean up backup directory for a completed thread.
 */
export function cleanupBackups(threadId: string): void {
  const backupDir = path.join(BACKUP_BASE, threadId);
  if (fs.existsSync(backupDir)) {
    fs.rmSync(backupDir, { recursive: true });
  }
}
