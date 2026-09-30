/**
 * List of paragraph section titles that must be styled as highlighted callouts.
 * Placed in a single configuration file per the architectural specification.
 */
export const CALLOUT_TITLES: ReadonlySet<string> = new Set([
  "Current position",
  "Validation position",
  "Next validation milestone",
  "Competitive position",
  "Financing position",
  "Product & technology differentiation",
  "Current product maturity",
  "Market opportunity analyst view",
  "Team-market fit",
]);

export function isCalloutTitle(title: string): boolean {
  if (!title) return false;
  // Match exact or case-insensitive trim
  const normalized = title.trim();
  if (CALLOUT_TITLES.has(normalized)) return true;
  for (const item of CALLOUT_TITLES) {
    if (item.toLowerCase() === normalized.toLowerCase()) return true;
  }
  return false;
}
