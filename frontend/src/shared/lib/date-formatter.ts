/**
 * Reformat strictly ISO dates formatted as YYYY-MM-DD into British English (en-GB) UTC format, e.g. "28 September 2026".
 * All other strings (e.g. "March 2026", "Undated", "2025", null/undefined) pass through unchanged.
 */
const STRICT_ISO_DATE_REGEX = /^(\d{4})-(\d{2})-(\d{2})$/;

const EN_GB_FORMATTER = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "long",
  year: "numeric",
  timeZone: "UTC",
});

export function formatDisplayDate(dateStr: string | null | undefined): string {
  if (!dateStr || typeof dateStr !== "string") {
    return dateStr ? String(dateStr) : "";
  }

  const trimmed = dateStr.trim();
  const match = trimmed.match(STRICT_ISO_DATE_REGEX);
  if (!match) {
    return dateStr;
  }

  const [, yearStr, monthStr, dayStr] = match;
  const year = parseInt(yearStr, 10);
  const month = parseInt(monthStr, 10) - 1; // 0-indexed month
  const day = parseInt(dayStr, 10);

  // Construct UTC date
  const dateObj = new Date(Date.UTC(year, month, day));
  if (isNaN(dateObj.getTime())) {
    return dateStr;
  }

  return EN_GB_FORMATTER.format(dateObj);
}
