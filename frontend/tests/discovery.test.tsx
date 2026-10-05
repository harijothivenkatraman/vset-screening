import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { DiscoveryForm } from "@/features/discovery/ui/DiscoveryForm";
import { CandidateReview } from "@/features/discovery/ui/CandidateReview";
import { JobProgress } from "@/features/discovery/ui/JobProgress";
import { ResolveCandidatesResponse } from "@/features/discovery/types";

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
}

describe("DiscoveryForm", () => {
  it("renders form fields and requires company and founder names", () => {
    const handleSubmit = vi.fn();
    render(<DiscoveryForm isLoading={false} onSubmit={handleSubmit} />);

    expect(screen.getByText("Discover New Company")).toBeInTheDocument();
    expect(screen.getByLabelText(/Company Name/)).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Founder #1 Name")).toBeInTheDocument();

    // Submit empty -> validation error
    fireEvent.click(screen.getByRole("button", { name: /Find Public Footprint/ }));
    expect(handleSubmit).not.toHaveBeenCalled();
  });

  it("allows adding and removing founder rows", () => {
    render(<DiscoveryForm isLoading={false} onSubmit={vi.fn()} />);

    expect(screen.getAllByPlaceholderText(/Founder #/)).toHaveLength(1);

    // Add founder
    fireEvent.click(screen.getByText("Add another founder"));
    expect(screen.getAllByPlaceholderText(/Founder #/)).toHaveLength(2);

    // Remove founder
    const removeButtons = screen.getAllByTitle("Remove founder");
    expect(removeButtons).toHaveLength(2);
    fireEvent.click(removeButtons[0]);
    expect(screen.getAllByPlaceholderText(/Founder #/)).toHaveLength(1);
  });

  it("submits trimmed form values", () => {
    const handleSubmit = vi.fn();
    render(<DiscoveryForm isLoading={false} onSubmit={handleSubmit} />);

    fireEvent.change(screen.getByPlaceholderText("e.g. Terraspark Robotics"), {
      target: { value: "  Acme Robotics  " },
    });
    fireEvent.change(screen.getByPlaceholderText("Founder #1 Name"), {
      target: { value: "  Alice Vance  " },
    });

    fireEvent.click(screen.getByRole("button", { name: /Find Public Footprint/ }));
    expect(handleSubmit).toHaveBeenCalledWith({
      company_name: "Acme Robotics",
      founder_names: ["Alice Vance"],
      website_override: undefined,
      company_linkedin_override: undefined,
    }, false);
  });

  it("submits with reviewBeforeStart when advanced checkbox is checked", () => {
    const handleSubmit = vi.fn();
    render(<DiscoveryForm isLoading={false} onSubmit={handleSubmit} />);

    fireEvent.change(screen.getByPlaceholderText("e.g. Terraspark Robotics"), {
      target: { value: "Acme" },
    });
    fireEvent.change(screen.getByPlaceholderText("Founder #1 Name"), {
      target: { value: "Alice" },
    });

    fireEvent.click(screen.getByLabelText(/Review sources before starting/));
    fireEvent.click(screen.getByRole("button", { name: /Find Public Footprint/ }));

    expect(handleSubmit).toHaveBeenCalledWith(
      expect.objectContaining({ company_name: "Acme" }),
      true
    );
  });

  it("initializes with initialValues", () => {
    render(
      <DiscoveryForm
        isLoading={false}
        onSubmit={vi.fn()}
        initialValues={{ company_name: "Test Co", founder_names: ["Bob", "Alice"] }}
      />
    );
    expect(screen.getByDisplayValue("Test Co")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Bob")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Alice")).toBeInTheDocument();
  });
});

describe("CandidateReview", () => {
  const mockResolveData: ResolveCandidatesResponse = {
    candidates: {
      company_linkedin: [
        {
          url: "https://linkedin.com/company/acme",
          title: "Acme Corp | LinkedIn",
          snippet: "Official page",
          domain: "linkedin.com",
          confidence: 0.95,
          category: "company_linkedin",
          search_query: "acme",
          entity_name: "Acme",
        },
      ],
      founder_linkedin_alice_vance: [
        {
          url: "https://linkedin.com/in/alicevance",
          title: "Alice Vance - CEO",
          snippet: "Founder profile",
          domain: "linkedin.com",
          confidence: 0.85,
          category: "founder_linkedin_alice_vance",
          search_query: "alice vance",
          entity_name: "Alice Vance",
        },
      ],
      website: [
        {
          url: "https://acme.io",
          title: "Acme Home",
          snippet: "Robotics platform",
          domain: "acme.io",
          confidence: 0.9,
          category: "website",
          search_query: "acme website",
          entity_name: "Acme",
        },
      ],
    },
    search_unavailable: false,
  };

  it("renders candidates with confidence percentages", () => {
    render(
      <QueryClientProvider client={createTestQueryClient()}>
        <CandidateReview
          companyName="Acme"
          founderNames={["Alice Vance"]}
          resolveData={mockResolveData}
          isStarting={false}
          onBack={vi.fn()}
          onConfirm={vi.fn()}
        />
      </QueryClientProvider>
    );

    expect(screen.getByText("Review Public Footprint for Acme")).toBeInTheDocument();
    expect(screen.getByText("95% match")).toBeInTheDocument();
    expect(screen.getByText("85% match")).toBeInTheDocument();
    expect(screen.getByText("90% match")).toBeInTheDocument();
  });

  it("shows search unavailable warning when search_unavailable is true", () => {
    const fallbackData: ResolveCandidatesResponse = {
      candidates: {},
      search_unavailable: true,
      error_message: "Rate limit reached",
    };

    render(
      <QueryClientProvider client={createTestQueryClient()}>
        <CandidateReview
          companyName="Acme"
          founderNames={["Alice"]}
          resolveData={fallbackData}
          isStarting={false}
          onBack={vi.fn()}
          onConfirm={vi.fn()}
        />
      </QueryClientProvider>
    );

    expect(screen.getByText("Search service currently unavailable")).toBeInTheDocument();
  });

  it("calls onConfirm when user submits confirmed URLs", () => {
    const handleConfirm = vi.fn();
    render(
      <QueryClientProvider client={createTestQueryClient()}>
        <CandidateReview
          companyName="Acme"
          founderNames={["Alice Vance"]}
          resolveData={mockResolveData}
          isStarting={false}
          onBack={vi.fn()}
          onConfirm={handleConfirm}
        />
      </QueryClientProvider>
    );

    fireEvent.click(
      screen.getByRole("button", { name: /Confirm Sources & Assemble Report/ })
    );
    expect(handleConfirm).toHaveBeenCalledWith({
      company_linkedin: "https://linkedin.com/company/acme",
      founder_linkedin_alice_vance: "https://linkedin.com/in/alicevance",
      website: "https://acme.io",
    });
  });

  it("submits manual evidence text alongside confirmed URLs", () => {
    const handleConfirm = vi.fn();
    render(
      <QueryClientProvider client={createTestQueryClient()}>
        <CandidateReview
          companyName="Acme"
          founderNames={["Alice Vance"]}
          resolveData={mockResolveData}
          isStarting={false}
          onBack={vi.fn()}
          onConfirm={handleConfirm}
        />
      </QueryClientProvider>
    );

    const textareas = screen.getAllByPlaceholderText(/Paste profile text/);
    expect(textareas.length).toBeGreaterThan(0);
    // Paste text into first textarea (company_linkedin)
    fireEvent.change(textareas[0], {
      target: { value: "Acme was founded in 2021 by robotics experts." },
    });

    fireEvent.click(
      screen.getByRole("button", { name: /Confirm Sources & Assemble Report/ })
    );
    expect(handleConfirm).toHaveBeenCalledWith(
      {
        company_linkedin: "https://linkedin.com/company/acme",
        founder_linkedin_alice_vance: "https://linkedin.com/in/alicevance",
        website: "https://acme.io",
      },
      {
        company_linkedin: {
          text: "Acme was founded in 2021 by robotics experts.",
        },
      }
    );
  });
});

describe("JobProgress", () => {
  it("renders stage progress and direct dashboard link on completion", () => {
    const queryClient = createTestQueryClient();
    queryClient.setQueryData(["discovery", "job", "job-123"], {
      job_id: "job-123",
      company_name: "Apex AI",
      state: "succeeded",
      stage: "Complete",
      progress: 1.0,
      warnings: ["One news article could not be reached"],
      result_slug: "apex-ai",
    });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <JobProgress jobId="job-123" onReset={vi.fn()} />
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(screen.getByText("Report Ready: Apex AI")).toBeInTheDocument();
    expect(screen.getByText("View Startup Screening Dashboard")).toBeInTheDocument();
    expect(
      screen.getByText("One news article could not be reached")
    ).toBeInTheDocument();
  });

  it("renders error state on job failure", () => {
    const queryClient = createTestQueryClient();
    queryClient.setQueryData(["discovery", "job", "job-fail"], {
      job_id: "job-fail",
      company_name: "Failed Corp",
      state: "failed",
      stage: "Failed",
      progress: 0.5,
      warnings: [],
      error_message: "Network timeout scraping website",
    });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <JobProgress jobId="job-fail" onReset={vi.fn()} />
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(
      screen.getByText("Discovery Job Encountered an Error")
    ).toBeInTheDocument();
    expect(
      screen.getByText("Network timeout scraping website")
    ).toBeInTheDocument();
    expect(screen.getByText("Discover Another Company")).toBeInTheDocument();
  });
});
