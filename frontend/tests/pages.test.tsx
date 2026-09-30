import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";
import { AtAGlanceStrip } from "@/features/report/ui/sections/AtAGlanceStrip";

describe("AtAGlanceStrip", () => {
  it("renders founding team with leading integer and original text on team tab", () => {
    const blocks: unknown[] = [
      [
        "kv",
        null,
        [
          [
            "Founding team",
            "3 - two described as co-founders (Sanjay Vijendran and Matthias Laug); one described as a founder (Jasper Deprez)",
          ],
        ],
      ],
      ["cards", "Founder details", []],
    ];

    render(<AtAGlanceStrip sectionKey="team" blocks={blocks} />);
    expect(screen.getByText(/Founding Team \(3\)/)).toBeInTheDocument();
    expect(
      screen.getByText(
        "3 - two described as co-founders (Sanjay Vijendran and Matthias Laug); one described as a founder (Jasper Deprez)"
      )
    ).toBeInTheDocument();
  });

  it("renders additional management count when present on team tab", () => {
    const blocks: unknown[] = [
      [
        "kv",
        null,
        [["Founding team", "3 (all described by the company as co-founders)"]],
      ],
      [
        "table",
        "Key management members - other than founders",
        ["Name", "Position", "Relevant responsibility"],
        [
          ["Exec 1", "VP Sales", "Sales"],
          ["Exec 2", "VP Marketing", "Marketing"],
        ],
      ],
    ];

    render(<AtAGlanceStrip sectionKey="team" blocks={blocks} />);
    expect(screen.getByText(/Founding Team \(3\)/)).toBeInTheDocument();
    expect(screen.getByText("2 executives recorded")).toBeInTheDocument();
  });

  it("renders verbatim source text for funding totals on funding tab", () => {
    const blocks: unknown[] = [
      [
        "para",
        "FINANCING POSITION",
        "Mysa has completed a USD 2.8m Seed round (February 2025) and a USD 3.4m Pre-Series A (January 2026). A financing event, undated was also reported; its completion has not been confirmed. Reported financing totals USD 6.2m across Pre-Series and Seed rounds (2025–2026); no lead investor is named.",
      ],
      [
        "table",
        "Funding timeline",
        ["Date", "Financing", "Amount", "Investors / providers", "Key details"],
        [
          ["Undated", "Financing event, undated", "Not disclosed", "Not disclosed", "-"],
          ["February 2025", "Seed", "USD 2.8m", "Blume Ventures", "-"],
          ["January 2026", "Pre-Series A", "USD 3.4m", "Blume Ventures", "-"],
        ],
      ],
    ];

    render(<AtAGlanceStrip sectionKey="funding" blocks={blocks} />);
    expect(screen.getByText("Reported Financing Baseline")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Reported financing totals USD 6.2m across Pre-Series and Seed rounds (2025–2026); no lead investor is named."
      )
    ).toBeInTheDocument();
    expect(screen.getByText("3 events in timeline")).toBeInTheDocument();
  });

  it("is hidden when absent or on unrelated tabs", () => {
    const blocks: unknown[] = [
      ["para", "Overview", "Some product description"],
    ];

    const { container } = render(
      <AtAGlanceStrip sectionKey="product" blocks={blocks} />
    );
    expect(container.firstChild).toBeNull();
  });
});
