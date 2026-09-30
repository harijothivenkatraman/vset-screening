import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { FactBar } from "@/shared/ui/FactBar";
import { FactGrid } from "@/shared/ui/FactGrid";
import { Avatar, getInitials } from "@/shared/ui/Avatar";
import { Collapsible } from "@/shared/ui/Collapsible";
import { Timeline } from "@/shared/ui/Timeline";
import { Callout, determineCalloutVariant } from "@/shared/ui/Callout";

describe("Shared UI Primitives", () => {
  it("computes initials correctly in Avatar", () => {
    expect(getInitials("Jasper Deprez")).toBe("JD");
    expect(getInitials("Arpita Kapoor")).toBe("AK");
    expect(getInitials("Sanjay Vijendran")).toBe("SV");
    expect(getInitials("Mysa")).toBe("MY");
    expect(getInitials("")).toBe("?");
  });

  it("renders FactBar with label above value", () => {
    const items: [string, string][] = [
      ["Base country", "Luxembourg"],
      ["Stage", "Pre-Seed"],
    ];
    render(<FactBar items={items} />);
    expect(screen.getByText("Base country")).toBeInTheDocument();
    expect(screen.getByText("Luxembourg")).toBeInTheDocument();
    expect(screen.getByText("Stage")).toBeInTheDocument();
    expect(screen.getByText("Pre-Seed")).toBeInTheDocument();
  });

  it("renders FactGrid with 2-3 column layout", () => {
    const items: [string, unknown][] = [
      ["Founded", "2025"],
      ["Headquarters", "Luxembourg"],
    ];
    render(<FactGrid items={items} />);
    expect(screen.getByText("Founded")).toBeInTheDocument();
    expect(screen.getByText("2025")).toBeInTheDocument();
    expect(screen.getByText("Headquarters")).toBeInTheDocument();
    expect(screen.getByText("Luxembourg")).toBeInTheDocument();
  });

  it("toggles Collapsible on button click", () => {
    const toggleSpy = vi.fn();
    const { rerender } = render(
      <Collapsible
        id="test-col"
        title="Test Topic"
        count={5}
        isOpen={false}
        onToggle={toggleSpy}
      >
        <p>Collapsible Body Content</p>
      </Collapsible>
    );

    expect(screen.getByText("Test Topic")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
    expect(screen.queryByText("Collapsible Body Content")).not.toBeInTheDocument();

    const button = screen.getByRole("button", { name: /Test Topic/i });
    fireEvent.click(button);
    expect(toggleSpy).toHaveBeenCalled();

    rerender(
      <Collapsible
        id="test-col"
        title="Test Topic"
        count={5}
        isOpen={true}
        onToggle={toggleSpy}
      >
        <p>Collapsible Body Content</p>
      </Collapsible>
    );
    expect(screen.getByText("Collapsible Body Content")).toBeInTheDocument();
  });

  it("renders Timeline maintaining source order", () => {
    const events = [
      { date: "2025", event: "Company founded in Luxembourg." },
      { date: "March 2026", event: "Pre-Seed round EUR 5m." },
    ];
    render(<Timeline events={events} />);
    expect(screen.getByText("2025")).toBeInTheDocument();
    expect(screen.getByText("Company founded in Luxembourg.")).toBeInTheDocument();
    expect(screen.getByText("March 2026")).toBeInTheDocument();
    expect(screen.getByText("Pre-Seed round EUR 5m.")).toBeInTheDocument();
  });

  it("determines correct callout variant from title", () => {
    expect(determineCalloutVariant("Current position")).toBe("position");
    expect(determineCalloutVariant("Validation position")).toBe("position");
    expect(determineCalloutVariant("Next validation milestone")).toBe("position");
    expect(determineCalloutVariant("Product & technology differentiation")).toBe("analyst");
    expect(determineCalloutVariant("Market opportunity analyst view")).toBe("analyst");
    expect(determineCalloutVariant("Team-market fit")).toBe("analyst");
    expect(determineCalloutVariant("General notes")).toBe("default");
  });
});
