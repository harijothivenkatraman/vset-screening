import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";
import { MemoryRouter } from "react-router-dom";
import {
  FounderProfileBlock,
  FounderProfilePayload,
} from "@/features/report/ui/blocks/FounderProfileBlock";
import { getBlockRenderer } from "@/features/report/ui/blocks/registry";

describe("FounderProfileBlock and Registry", () => {
  it("registers founder_profile renderer in block registry", () => {
    const renderer = getBlockRenderer("founder_profile");
    expect(renderer).toBe(FounderProfileBlock);
  });

  it("renders a retrieved public profile with timeline, education, and skills", () => {
    const payload: FounderProfilePayload = {
      founder_name: "Arpita Kapoor",
      headline: "Co-Founder & CEO at Mysa",
      location: "Bengaluru, Karnataka, India",
      about: "Building the next generation financial operating platform for modern enterprises.",
      linkedin_url: "https://www.linkedin.com/in/arpita-kapoor",
      experience_timeline: [
        {
          title: "Chief Executive Officer",
          company: "Mysa",
          start: "March 2023",
          end: "Present",
          duration: "March 2023 - Present (3 years 1 month)",
          is_current: true,
          description: "Leading company strategy and product roadmap.",
        },
        {
          title: "Vice President of Product",
          company: "Razorpay",
          start: "January 2019",
          end: "February 2023",
          duration: "4 years 2 months",
          is_current: false,
        },
      ],
      education: [
        {
          school: "Indian Institute of Technology, Delhi",
          degree: "Bachelor of Technology - BTech",
          field: "Computer Science",
          start_year: "2011",
          end_year: "2015",
        },
      ],
      skills: ["Financial Modeling", "Fintech", "Product Strategy"],
      certifications: ["Chartered Financial Analyst (CFA)"],
      languages: ["English", "Hindi"],
      retrieval: {
        status: "retrieved",
        source_type: "linkedin_public",
        retrieved_at: "2026-10-03T12:00:00Z",
        source_id: "src_arpita",
        sections_available: ["headline", "location", "about", "experience", "education", "skills"],
      },
      identity_status: "verified",
    };

    render(
      <MemoryRouter>
        <FounderProfileBlock block={["founder_profile", "Founder profile: Arpita Kapoor", payload]} />
      </MemoryRouter>
    );

    // Header & identity
    expect(screen.getByText("Arpita Kapoor")).toBeInTheDocument();
    expect(screen.getByText("Co-Founder & CEO at Mysa")).toBeInTheDocument();
    expect(screen.getByText("Bengaluru, Karnataka, India")).toBeInTheDocument();
    expect(screen.getByText(/LinkedIn public/i)).toBeInTheDocument();

    // External link with proper rel attributes
    const link = screen.getByRole("link", { name: /Open LinkedIn profile for Arpita Kapoor/i });
    expect(link).toHaveAttribute("href", "https://www.linkedin.com/in/arpita-kapoor");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");

    // Experience timeline
    expect(screen.getByText("Chief Executive Officer")).toBeInTheDocument();
    expect(screen.getAllByText(/Mysa/).length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("Current")).toBeInTheDocument();
    expect(screen.getByText("Vice President of Product")).toBeInTheDocument();

    // Education
    expect(screen.getByText("Indian Institute of Technology, Delhi")).toBeInTheDocument();
    expect(screen.getByText(/Bachelor of Technology - BTech/)).toBeInTheDocument();

    // Skills & Certs
    expect(screen.getByText("Financial Modeling")).toBeInTheDocument();
    expect(screen.getByText("Chartered Financial Analyst (CFA)")).toBeInTheDocument();
  });

  it("renders user-provided evidence with unverified chip", () => {
    const payload: FounderProfilePayload = {
      founder_name: "Mohit Rangaraju",
      headline: "Co-Founder & COO at Mysa",
      location: "Bengaluru, India",
      about: "Co-founder leading operations and banking partnerships.",
      experience_timeline: [
        {
          title: "Chief Operating Officer",
          company: "Mysa",
          duration: "2023 - Present",
          is_current: true,
        },
      ],
      retrieval: {
        status: "user_provided",
        source_type: "user_supplied",
      },
    };

    render(
      <MemoryRouter>
        <FounderProfileBlock block={["founder_profile", "Founder profile: Mohit Rangaraju", payload]} />
      </MemoryRouter>
    );

    expect(screen.getByText("Mohit Rangaraju")).toBeInTheDocument();
    expect(screen.getByText("Provided by user (unverified)")).toBeInTheDocument();
    expect(screen.getByText("Chief Operating Officer")).toBeInTheDocument();
  });

  it("renders blocked state as compact row with neutral copy and manual evidence link", () => {
    const payload: FounderProfilePayload = {
      founder_name: "Ashutosh Panigrahi",
      headline: "CTO (from company website)",
      retrieval: {
        status: "blocked_by_bot_protection",
        source_type: "linkedin_public",
      },
    };

    render(
      <MemoryRouter initialEntries={["/companies/mysa/founder_profiles"]}>
        <FounderProfileBlock block={["founder_profile", "Founder profile: Ashutosh Panigrahi", payload]} />
      </MemoryRouter>
    );

    expect(screen.getByText("Ashutosh Panigrahi")).toBeInTheDocument();
    expect(screen.getByText("Not retrievable from this server")).toBeInTheDocument();
    expect(screen.getByText("Technical diagnostics recorded in Retrieval log.")).toBeInTheDocument();
    // Neutral wording: no Cloudflare or AWS Lightsail in report tab
    expect(screen.queryByText(/Cloudflare/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/AWS Lightsail/i)).not.toBeInTheDocument();
    // No LinkedIn button when no URL exists
    expect(screen.queryByText(/Open LinkedIn profile/i)).not.toBeInTheDocument();
    // Provide manually link
    const manualLink = screen.getByRole("link", { name: /Provide manually/i });
    expect(manualLink).toHaveAttribute("href", expect.stringContaining("/discover?company="));
    expect(manualLink).toHaveAttribute("href", expect.stringContaining("founders=Ashutosh%20Panigrahi"));
  });

  it("renders unverified candidate as minimal row with Needs confirmation badge", () => {
    const payload: FounderProfilePayload = {
      founder_name: "Arpita Kapoor",
      headline: "Executive at Mysa Smart Thermostats",
      linkedin_url: "https://www.linkedin.com/in/arpita-thermostat",
      retrieval: {
        status: "identity_unverified",
        source_type: "linkedin_public",
      },
      identity_status: "likely_match",
    };

    render(
      <MemoryRouter>
        <FounderProfileBlock block={["founder_profile", "Founder profile: Arpita Kapoor", payload]} />
      </MemoryRouter>
    );

    expect(screen.getByText("Arpita Kapoor")).toBeInTheDocument();
    expect(screen.getByText("Needs confirmation")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Candidate profile/i })).toHaveAttribute(
      "href",
      "https://www.linkedin.com/in/arpita-thermostat"
    );
    expect(screen.getByRole("button", { name: /Confirm/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Paste URL or profile text/i })).toHaveAttribute(
      "href",
      expect.stringContaining("/discover?company=")
    );
    // Full details stay in Candidate Review: no timeline, no education, no about section
    expect(screen.queryByText("Experience Timeline")).not.toBeInTheDocument();
    expect(screen.queryByText("Education")).not.toBeInTheDocument();
    expect(screen.queryByText("Differences found — verify")).not.toBeInTheDocument();
  });

  it("renders cross-check conflict callout when discrepancies are detected", () => {
    const payload: FounderProfilePayload = {
      founder_name: "Ashutosh Panigrahi",
      headline: "CTO at Mysa",
      cross_checks: [
        {
          field_name: "role",
          website_value: "Co-founder & CEO",
          linkedin_value: "Chief Technology Officer",
          details: "Website states 'Co-founder & CEO' while LinkedIn lists 'Chief Technology Officer' at Mysa",
          severity: "low",
        },
      ],
      retrieval: {
        status: "retrieved",
        source_type: "linkedin_public",
      },
    };

    render(
      <MemoryRouter>
        <FounderProfileBlock block={["founder_profile", "Founder profile: Ashutosh Panigrahi", payload]} />
      </MemoryRouter>
    );

    expect(screen.getByText("Differences found — verify")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Website states 'Co-founder & CEO' while LinkedIn lists 'Chief Technology Officer' at Mysa"
      )
    ).toBeInTheDocument();
  });

  it("renders website-only data with From company website label", () => {
      const payload: FounderProfilePayload = {
        founder_name: "Jane Doe",
        retrieval: {
          status: "not_requested",
          source_type: "website",
        },
        website_data: {
          name: "Jane Doe",
          role: "Co-Founder",
          lines: [
            ["Experience", "10 years in tech"],
            ["Quote", "We are building the future"],
          ],
          fit: "Strong technical background",
        },
      };
  
      render(
        <MemoryRouter>
          <FounderProfileBlock block={["founder_profile", "Founder profile: Jane Doe", payload]} />
        </MemoryRouter>
      );
  
      expect(screen.getAllByText("Jane Doe")[0]).toBeInTheDocument();
      expect(screen.getByText("From company website")).toBeInTheDocument();
      expect(screen.getByText("Co-Founder")).toBeInTheDocument();
      expect(screen.getByText("Founder–Market Fit")).toBeInTheDocument();
      expect(screen.getByText("Strong technical background")).toBeInTheDocument();
    });
});
