export function retryDelayMs(value, fallbackMs = 1000, nowMs = Date.now()) {
  if (value === null || value === undefined || value.trim() === '') return fallbackMs;
  const seconds = Number(value);
  if (Number.isFinite(seconds)) return seconds * 1000 || fallbackMs;
  const deadline = Date.parse(value);
  return Number.isFinite(deadline) ? Math.max(0, deadline - nowMs) : fallbackMs;
}
