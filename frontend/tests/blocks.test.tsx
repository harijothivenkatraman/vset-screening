import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";
import { ParaBlock } from "@/features/report/ui/blocks/ParaBlock";
import { KvBlock } from "@/features/report/ui/blocks/KvBlock";
import { OlistBlock } from "@/features/report/ui/blocks/OlistBlock";
import { ListBlock } from "@/features/report/ui/blocks/ListBlock";
import { TableBlock } from "@/features/report/ui/blocks/TableBlock";
import { CardsBlock } from "@/features/report/ui/blocks/CardsBlock";
import { ComparisonBlock } from "@/features/report/ui/blocks/ComparisonBlock";
import { UnknownBlock } from "@/features/report/ui/blocks/UnknownBlock";
import { getBlockRenderer } from "@/features/report/ui/blocks/registry";
import { MutedValue } from "@/shared/ui/MutedValue";
import { splitInvestors } from "@/shared/ui/FundingCards";

describe("Block Renderers", () => {
  it("renders standard ParaBlock", () => {
    const block: [string, string, string] = [
      "para",
      "What TerraSpark does",
      "TerraSpark is developing space-based solar power systems.",
    ];
    render(<ParaBlock block={block} />);
    expect(screen.getByText("What TerraSpark does")).toBeInTheDocument();
    expect(
      screen.getByText("TerraSpark is developing space-based solar power systems.")
    ).toBeInTheDocument();
  });

  it("renders callout-styled ParaBlock for designated titles", () => {
    const block: [string, string, string] = [
      "para",
      "Current position",
      "TerraSpark is a Pre-Seed-stage company.",
    ];
    render(<ParaBlock block={block} />);
    expect(screen.getByText("Current position")).toBeInTheDocument();
    expect(screen.getByText("TerraSpark is a Pre-Seed-stage company.")).toBeInTheDocument();
  });

  it("renders KvBlock with FactGrid", () => {
    const block: [string, string, [string, string][]] = [
      "kv",
      "Company profile",
      [
        ["Founded", "2025"],
        ["Stage", "Pre-Seed"],
      ],
    ];
    render(<KvBlock block={block} />);
    expect(screen.getByText("Company profile")).toBeInTheDocument();
    expect(screen.getByText("Founded")).toBeInTheDocument();
    expect(screen.getByText("2025")).toBeInTheDocument();
    expect(screen.getByText("Stage")).toBeInTheDocument();
    expect(screen.getByText("Pre-Seed")).toBeInTheDocument();
  });

  it("renders OlistBlock with numbering", () => {
    const block: [string, string, string[]] = [
      "olist",
      "Products & services",
      ["Space-based solar power systems", "Wireless power transmission systems"],
    ];
    render(<OlistBlock block={block} />);
    expect(screen.getByText("Products & services")).toBeInTheDocument();
    expect(screen.getByText("Space-based solar power systems")).toBeInTheDocument();
    expect(screen.getByText("Wireless power transmission systems")).toBeInTheDocument();
  });

  it("renders ListBlock with bullet list", () => {
    const block: [string, string, string[]] = [
      "list",
      "Target markets",
      ["Luxembourg", "Europe"],
    ];
    render(<ListBlock block={block} />);
    expect(screen.getByText("Target markets")).toBeInTheDocument();
    expect(screen.getByText("Luxembourg")).toBeInTheDocument();
    expect(screen.getByText("Europe")).toBeInTheDocument();
  });

  it("renders standard TableBlock with headers and rows", () => {
    const block: [string, string, string[], string[][], number[]] = [
      "table",
      "Product portfolio",
      ["#", "Product", "Primary use"],
      [["1", "Orbital Array", "Power generation"]],
      [0.1, 0.4, 0.5],
    ];
    render(<TableBlock block={block} />);
    expect(screen.getByText("Product portfolio")).toBeInTheDocument();
    expect(screen.getByText("#")).toBeInTheDocument();
    expect(screen.getByText("Product")).toBeInTheDocument();
    expect(screen.getByText("Primary use")).toBeInTheDocument();
    expect(screen.getByText("Orbital Array")).toBeInTheDocument();
  });

  it("renders TableBlock as vertical Timeline when headers are Date/Event", () => {
    const block: [string, string, string[], string[][], number[]] = [
      "table",
      "Company timeline",
      ["Date", "Event"],
      [
        ["2025", "Company founded."],
        ["March 2026", "Pre-Seed round, EUR 5m."],
      ],
      [0.2, 0.8],
    ];
    render(<TableBlock block={block} />);
    expect(screen.getByText("Company timeline")).toBeInTheDocument();
    expect(screen.getByText("Company founded.")).toBeInTheDocument();
    expect(screen.getByText("Pre-Seed round, EUR 5m.")).toBeInTheDocument();
    expect(screen.getByText("2025")).toBeInTheDocument();
    expect(screen.getByText("March 2026")).toBeInTheDocument();
  });

  it("renders TableBlock as FundingCards for funding history tables", () => {
    const block: [string, string, string[], string[][]] = [
      "table",
      "Funding timeline",
      ["Date", "Financing", "Amount", "Investors / providers", "Key details"],
      [
        [
          "March 2026",
          "Pre-Seed",
          "EUR 5m",
          "Daphni, Sake Bosch, better ventures",
          "Intended use: further technology development.",
        ],
      ],
    ];
    render(<TableBlock block={block} />);
    expect(screen.getByText("Funding timeline")).toBeInTheDocument();
    expect(screen.getByText("Pre-Seed")).toBeInTheDocument();
    expect(screen.getByText("EUR 5m")).toBeInTheDocument();
    expect(screen.getByText("Daphni")).toBeInTheDocument();
    expect(screen.getByText("Sake Bosch")).toBeInTheDocument();
    expect(screen.getByText("better ventures")).toBeInTheDocument();
  });

  it("renders CardsBlock with founder fit note", () => {
    const block: [string, string, unknown[]] = [
      "cards",
      "Founder details",
      [
        {
          name: "Jasper Deprez",
          role: "CEO · Founder",
          lines: [["Education", "MBA, Commerce"]],
          fit: "Deprez has relevant founder experience.",
        },
      ],
    ];
    render(<CardsBlock block={block} />);
    expect(screen.getByText("Jasper Deprez")).toBeInTheDocument();
    expect(screen.getByText("CEO · Founder")).toBeInTheDocument();
    expect(screen.getByText("MBA, Commerce")).toBeInTheDocument();
    expect(screen.getByText("Deprez has relevant founder experience.")).toBeInTheDocument();
  });

  it("renders ComparisonBlock shape (a): TerraSpark-style 2-column layout", () => {
    const block: [string, string, unknown] = [
      "comparison",
      "How customers may choose",
      {
        header: [],
        items: [
          [
            "Reliability / uptime",
            "continuous electricity is central",
            "Claims clean, reliable, 24/7 power",
          ],
        ],
        note: "Sample comparative note footnote",
      },
    ];
    render(<ComparisonBlock block={block} />);
    expect(screen.getByText("How customers may choose")).toBeInTheDocument();
    expect(screen.getByText("Criterion & Context")).toBeInTheDocument();
    expect(screen.getByText("Company Position")).toBeInTheDocument();
    expect(screen.getByText("Reliability / uptime")).toBeInTheDocument();
    expect(screen.getByText("continuous electricity is central")).toBeInTheDocument();
    expect(screen.getByText("Claims clean, reliable, 24/7 power")).toBeInTheDocument();
    expect(screen.getByText(/Sample comparative note footnote/)).toBeInTheDocument();
  });

  it("renders ComparisonBlock shape (b): Mysa-style matrix", () => {
    const block: [string, string, unknown] = [
      "comparison",
      "How customers may choose",
      {
        header: ["Dimension", "Mysa", "Zoho"],
        rows: [["Functional coverage", "Not established", "Integration target"]],
        items: [],
        note: "Comparable evidence on manual ops",
      },
    ];
    render(<ComparisonBlock block={block} />);
    expect(screen.getByText("Dimension")).toBeInTheDocument();
    expect(screen.getByText("Mysa")).toBeInTheDocument();
    expect(screen.getByText("Zoho")).toBeInTheDocument();
    expect(screen.getByText("Functional coverage")).toBeInTheDocument();
    expect(screen.getByText(/Comparable evidence on manual ops/)).toBeInTheDocument();
  });

  it("renders UnknownBlock without crashing and logs a console warning", () => {
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    const block: [string, string, unknown] = [
      "future_unknown_type",
      "Quantum Encryption",
      { bits: 1024 },
    ];
    render(<UnknownBlock block={block} />);
    expect(screen.getByText(/Unsupported Block Type:/)).toBeInTheDocument();
    expect(screen.getByText("Quantum Encryption")).toBeInTheDocument();
    expect(warnSpy).toHaveBeenCalled();
    warnSpy.mockRestore();
  });

  it("registry fallback returns UnknownBlock for unknown type", () => {
    const Renderer = getBlockRenderer("nonexistent_type");
    expect(Renderer).toBe(UnknownBlock);
  });

  it("renders MutedValue correctly for absent data", () => {
    const { rerender } = render(<MutedValue value="-" />);
    expect(screen.getByText("Not established")).toBeInTheDocument();

    rerender(<MutedValue value="Not established" />);
    expect(screen.getByText("Not established")).toBeInTheDocument();

    rerender(<MutedValue value="Active Value" />);
    expect(screen.getByText("Active Value")).toBeInTheDocument();
  });
});

describe("splitInvestors helper", () => {
  it("splits TerraSpark investors string on commas only and drops no text", () => {
    const raw =
      "Daphni, Sake Bosch, better ventures, Hans(wo)men Group, Luxembourg Business Angel Network, Karaoke Club and 30 strategic business angels";
    const split = splitInvestors(raw);
    expect(split).toEqual([
      "Daphni",
      "Sake Bosch",
      "better ventures",
      "Hans(wo)men Group",
      "Luxembourg Business Angel Network",
      "Karaoke Club and 30 strategic business angels",
    ]);
  });

  it("splits Mysa Seed and Pre-Series A investors strings on commas only and drops no text", () => {
    const seed =
      "Blume Ventures, Antler, Emphasis Ventures (EMVC), IIMA Ventures and Neon Fund";
    expect(splitInvestors(seed)).toEqual([
      "Blume Ventures",
      "Antler",
      "Emphasis Ventures (EMVC)",
      "IIMA Ventures and Neon Fund",
    ]);

    const preSeriesA =
      "Blume Ventures, Piper Serica, Ikemori Ventures, Raise Financial Services, QED Innovation Labs, Antler, IIMA Ventures and Neon Fund";
    expect(splitInvestors(preSeriesA)).toEqual([
      "Blume Ventures",
      "Piper Serica",
      "Ikemori Ventures",
      "Raise Financial Services",
      "QED Innovation Labs",
      "Antler",
      "IIMA Ventures and Neon Fund",
    ]);
  });

  it("handles 'Not disclosed' and missing values as empty array", () => {
    expect(splitInvestors("Not disclosed")).toEqual([]);
    expect(splitInvestors("-")).toEqual([]);
    expect(splitInvestors("")).toEqual([]);
  });
});
