export function formatNumber(value: number, digits = 1): string {
  return value.toFixed(digits);
}

export function formatSpeed(mps: number): string {
  return `${(mps * 3.6).toFixed(0)} km/h`;
}

export function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}