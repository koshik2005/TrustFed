/** Design system utilities — used across every component */

import { clsx, type ClassValue } from 'clsx';

/** Merge Tailwind classes conditionally — the standard pattern */
export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

/** Format a 0–1 score as a % string */
export function formatPercent(value: number, decimals = 1): string {
  return `${(value * 100).toFixed(decimals)}%`;
}

/** Format an epsilon value to 3 decimal places */
export function formatEpsilon(value: number): string {
  return `ε = ${value.toFixed(3)}`;
}

/** Map a risk score (0–1) to a label */
export function getRiskLabel(score: number): 'Low' | 'Medium' | 'High' {
  if (score < 0.4) return 'Low';
  if (score < 0.7) return 'Medium';
  return 'High';
}

/** Map a risk label to a Tailwind color class */
export function getRiskColor(label: 'Low' | 'Medium' | 'High'): string {
  return {
    Low: 'text-emerald-400',
    Medium: 'text-amber-400',
    High: 'text-red-400',
  }[label];
}

/** Map severity to a Tailwind badge color */
export function getSeverityColor(severity: 'low' | 'medium' | 'high'): string {
  return {
    low: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
    medium: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
    high: 'bg-red-500/20 text-red-300 border-red-500/30',
  }[severity];
}

/** Format ISO timestamp to readable string */
export function formatTimestamp(iso: string): string {
  return new Date(iso).toLocaleString('en-IN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
}

/** Truncate a hash for display */
export function truncateHash(hash: string, chars = 12): string {
  return `${hash.slice(0, chars)}…${hash.slice(-4)}`;
}
