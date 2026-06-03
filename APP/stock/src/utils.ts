import type { Company, SnapshotChange, WatchlistItem } from "./types";

export function formatChange(change: SnapshotChange): string {
  if (change.status !== "ok" || typeof change.percent !== "number") {
    return "本地快照不足";
  }
  const sign = change.percent > 0 ? "+" : "";
  return `${sign}${change.percent.toFixed(2)}% · ${change.fromDate}`;
}

export function heatLevel(value: number, max: number): number {
  if (!value || !max) return 0;
  const ratio = value / max;
  if (ratio >= 0.8) return 5;
  if (ratio >= 0.55) return 4;
  if (ratio >= 0.35) return 3;
  if (ratio >= 0.15) return 2;
  return 1;
}

export function matchesSearch(company: Company, query: string): boolean {
  const trimmed = query.trim().toLowerCase();
  if (!trimmed) return true;
  const haystack = [
    company.name,
    company.code,
    ...company.chains,
    ...company.stages,
    ...company.notes,
    company.summary
  ]
    .join(" ")
    .toLowerCase();
  return haystack.includes(trimmed);
}

export function matchesWatchlistSearch(item: WatchlistItem, query: string): boolean {
  const trimmed = query.trim().toLowerCase();
  if (!trimmed) return true;
  return [item.name, item.code, item.ownership, item.priority, ...item.chains].join(" ").toLowerCase().includes(trimmed);
}

export function priorityRank(priority: string): number {
  return { P0: 0, P1: 1, P2: 2, P3: 3 }[priority as "P0" | "P1" | "P2" | "P3"] ?? 9;
}

export function unique<T>(items: T[]): T[] {
  return Array.from(new Set(items));
}
