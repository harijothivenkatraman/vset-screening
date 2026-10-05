import { describe, it, expect } from "vitest";
import { formatDisplayDate, formatChipDate } from "@/shared/lib/date-formatter";

describe("Date Formatter", () => {
  it("formats strict YYYY-MM-DD dates into UTC en-GB format", () => {
    expect(formatDisplayDate("2026-09-28")).toBe("28 September 2026");
    expect(formatDisplayDate("2026-02-16")).toBe("16 February 2026");
    expect(formatDisplayDate("2025-01-05")).toBe("5 January 2025");
  });

  it("passes non-ISO or non-strict strings through unchanged", () => {
    expect(formatDisplayDate("March 2026")).toBe("March 2026");
    expect(formatDisplayDate("Undated")).toBe("Undated");
    expect(formatDisplayDate("2025")).toBe("2025");
    expect(formatDisplayDate("Q1 2026")).toBe("Q1 2026");
    expect(formatDisplayDate("Not established")).toBe("Not established");
  });

  it("handles null, undefined, or empty values safely", () => {
    expect(formatDisplayDate(null)).toBe("");
    expect(formatDisplayDate(undefined)).toBe("");
    expect(formatDisplayDate("")).toBe("");
  });

  it("formats source chip timestamps into short month en-GB UTC format", () => {
    expect(formatChipDate("2026-10-03T14:30:00Z")).toBe("3 Oct 2026");
    expect(formatChipDate("2026-09-28")).toBe("28 Sept 2026");
    expect(formatChipDate(null)).toBe("");
    expect(formatChipDate(undefined)).toBe("");
  });
});

