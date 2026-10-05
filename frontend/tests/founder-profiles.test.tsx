import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  FounderProfilesPage,
  FounderProfileDetailPage,
  AddProfileModal,
  GuardedDeleteModal,
  UpdateProfileModal,
  FounderProfile,
} from "@/features/founders";
import * as foundersApi from "@/features/founders/api";

const mockProfiles: FounderProfile[] = [
  {
    id: "11111111-1111-1111-1111-111111111111",
    slug: "asha-example-example-corp",
    founder_name: "Asha Example",
    company_name: "Example Corp",
    headline: "CEO & Co-founder at Example Corp",
    location: "Bengaluru, India",
    about: "Building scalable distributed architectures and leading product teams.",
    screening_assessment: "Strong domain depth in payments infrastructure.",
    linkedin_url: "https://www.linkedin.com/in/asha-example",
    identity_status: "user_asserted",
    retrieval: {
      status: "user_provided",
      source_label: "Provided by user (unverified)",
      retrieved_at: "2026-10-04T10:00:00Z",
    },
    experience_timeline: [
      {
        title: "Chief Executive Officer",
        company: "Example Corp",
        duration: "2022 - Present",
        location: "Bengaluru",
        description: "Leading executive strategy and operations.",
      },
      {
        title: "Senior Director of Engineering",
        company: "Past Innovations",
        duration: "2018 - 2022",
        location: "San Francisco",
        description: "Scaled cloud infrastructure.",
      },
    ],
    education: [
      {
        school: "State University",
        degree: "Bachelor of Technology",
        field_of_study: "Computer Science",
        year: "2018",
      },
    ],
    skills: ["Distributed Systems", "TypeScript", "Python"],
    certifications: [
      {
        name: "AWS Solutions Architect Professional",
        authority: "Amazon Web Services",
        year: "2023",
      },
    ],
    notes: "Verified identity with founder email domain.",
    warnings: [],
    has_previous_version: true,
    created_at: "2026-10-04T10:00:00Z",
    updated_at: "2026-10-05T12:00:00Z",
  },
  {
    id: "22222222-2222-2222-2222-222222222222",
    slug: "john-fictional-mysa",
    founder_name: "John Fictional",
    company_name: "Mysa",
    headline: "CTO & Co-founder",
    location: "Delhi, India",
    about: null,
    screening_assessment: "Ten years at major consumer tech companies.",
    linkedin_url: null,
    identity_status: "reference_screen",
    retrieval: {
      status: "reference_screen",
      source_label: "From vSET reference screen, 28 September 2026",
      retrieved_at: "2026-09-28T22:07:41Z",
    },
    experience_timeline: [
      {
        title: "Chief Technology Officer",
        company: "Mysa",
        duration: "2023 - Present",
      },
    ],
    education: [
      {
        school: "ABV - Indian Institute of Information Technology and Management",
        year: "2013",
      },
    ],
    skills: ["Cloud Architecture"],
    certifications: [],
    notes: null,
    warnings: [],
    has_previous_version: false,
    created_at: "2026-09-28T22:07:41Z",
    updated_at: "2026-09-28T22:07:41Z",
  },
];

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
}

describe("Founder Profiles Standalone UI", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
  });

  describe("FounderProfilesPage (List View)", () => {
    it("renders profile cards, stat counters, and source chips", async () => {
      vi.spyOn(foundersApi, "listFounders").mockResolvedValue({
        items: mockProfiles,
        total: 2,
        page: 1,
        page_size: 100,
      });

      const queryClient = createTestQueryClient();
      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter>
            <FounderProfilesPage />
          </MemoryRouter>
        </QueryClientProvider>
      );

      // Verify header
      expect(screen.getByText("Founder Profiles")).toBeInTheDocument();
      expect(
        screen.getByText("Verifiable founder profile extraction and catalog")
      ).toBeInTheDocument();

      // Verify stat cards
      await waitFor(() => {
        expect(screen.getByText("Asha Example")).toBeInTheDocument();
      });
      expect(screen.getByText("John Fictional")).toBeInTheDocument();

      // Verify source chips and tabs
      expect(screen.getByText("Manual")).toBeInTheDocument();
      expect(screen.getByText("Screening report")).toBeInTheDocument();
      expect(screen.getByText(/From screening reports/i)).toBeInTheDocument();
      expect(screen.getByText(/Added manually/i)).toBeInTheDocument();
    });

    it("filters profiles by search input", async () => {
      const listSpy = vi.spyOn(foundersApi, "listFounders").mockResolvedValue({
        items: [mockProfiles[0]],
        total: 1,
        page: 1,
        page_size: 100,
      });

      const queryClient = createTestQueryClient();
      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter>
            <FounderProfilesPage />
          </MemoryRouter>
        </QueryClientProvider>
      );

      const searchInput = screen.getByPlaceholderText(/search by founder name/i);
      fireEvent.change(searchInput, { target: { value: "Asha" } });

      await waitFor(() => {
        expect(listSpy).toHaveBeenCalledWith(
          expect.objectContaining({ search: "Asha" })
        );
      });
    });
  });

  describe("FounderProfileDetailPage (Full-width Detail View)", () => {
    it("renders full-width stacked cards: screening fit, timeline, education, skills, and provenance", async () => {
      vi.spyOn(foundersApi, "getFounder").mockResolvedValue(mockProfiles[0]);

      const queryClient = createTestQueryClient();
      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter initialEntries={["/profiles/asha-example-example-corp"]}>
            <Routes>
              <Route path="/profiles/:slug" element={<FounderProfileDetailPage />} />
            </Routes>
          </MemoryRouter>
        </QueryClientProvider>
      );

      // Wait for profile to load
      await waitFor(() => {
        expect(screen.getByText("Asha Example")).toBeInTheDocument();
      });

      // 1. From vSET screening card
      expect(screen.getByText("From vSET screening")).toBeInTheDocument();
      expect(
        screen.getByText("Strong domain depth in payments infrastructure.")
      ).toBeInTheDocument();

      // 2. About section
      expect(screen.getByText("About")).toBeInTheDocument();
      expect(
        screen.getByText(
          "Building scalable distributed architectures and leading product teams."
        )
      ).toBeInTheDocument();

      // 3. Experience timeline
      expect(screen.getByText(/Experience Timeline \(2\)/)).toBeInTheDocument();
      expect(screen.getByText("Chief Executive Officer")).toBeInTheDocument();
      expect(screen.getByText("Senior Director of Engineering")).toBeInTheDocument();

      // 4. Education
      expect(screen.getByText(/Education \(1\)/)).toBeInTheDocument();
      expect(screen.getByText("State University")).toBeInTheDocument();

      // 5. Skills & Certifications
      expect(screen.getByText(/Skills \(3\)/)).toBeInTheDocument();
      expect(screen.getByText("Distributed Systems")).toBeInTheDocument();
      expect(screen.getByText("AWS Solutions Architect Professional")).toBeInTheDocument();

      // 6. Action buttons: Restore Version is visible because has_previous_version is true
      expect(screen.getByText("Restore Version")).toBeInTheDocument();
      expect(screen.getByText("Export JSON")).toBeInTheDocument();
      expect(screen.getByText("Update / Re-upload")).toBeInTheDocument();
      expect(screen.getByText("Delete")).toBeInTheDocument();
    });
  });

  describe("AddProfileModal", () => {
    it("enforces 2 MB size cap on uploaded PDF files", async () => {
      const queryClient = createTestQueryClient();
      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter>
            <AddProfileModal isOpen={true} onClose={vi.fn()} />
          </MemoryRouter>
        </QueryClientProvider>
      );

      // Open accordion for direct manual entry
      fireEvent.click(screen.getByText(/Or enter profile text \/ upload PDF directly/i));

      // Switch to PDF mode
      fireEvent.click(screen.getByText(/Upload PDF \(Max 2MB\)/i));

      // Upload file exceeding 2 MB (e.g. 2.5 MB)
      const oversizedFile = new File([new ArrayBuffer(2.5 * 1024 * 1024)], "profile.pdf", {
        type: "application/pdf",
      });
      const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
      expect(fileInput).not.toBeNull();
      fireEvent.change(fileInput, { target: { files: [oversizedFile] } });

      // Early rejection warning is displayed
      await waitFor(() => {
        expect(
          screen.getByText(/exceeds the 2 MB cap/i)
        ).toBeInTheDocument();
      });
    });

    it("displays duplicate warning on 409 conflict with disambiguation option", async () => {
      const queryClient = createTestQueryClient();
      vi.spyOn(foundersApi, "createFounderFromText").mockRejectedValue({
        status: 409,
        data: {
          detail: "A profile for Asha Example at Example Corp already exists.",
          existing_slug: "asha-example-example-corp",
        },
      });

      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter>
            <AddProfileModal isOpen={true} onClose={vi.fn()} />
          </MemoryRouter>
        </QueryClientProvider>
      );

      // Fill in form inputs
      fireEvent.change(screen.getByPlaceholderText("Asha Example"), {
        target: { value: "Asha Example" },
      });
      fireEvent.change(screen.getByPlaceholderText("Example Corp"), {
        target: { value: "Example Corp" },
      });

      // Open direct manual entry accordion
      fireEvent.click(screen.getByText(/Or enter profile text \/ upload PDF directly/i));
      fireEvent.change(screen.getByPlaceholderText(/Paste online profile text here.../i), {
        target: { value: "Asha Example\nCEO at Example Corp\nExperience:\nCEO (2022)" },
      });

      // Submit manual entry
      fireEvent.click(screen.getByText("Save Manually"));

      // Verify conflict banner
      await waitFor(() => {
        expect(screen.getByText("Profile Conflict Detected")).toBeInTheDocument();
        expect(screen.getByText("View Existing Profile")).toBeInTheDocument();
        expect(
          screen.getByText("Create anyway (auto-disambiguate slug)")
        ).toBeInTheDocument();
      });
    });

    it("runs automated discovery flow and navigates to profile on verified outcome", async () => {
      const autoDiscoverSpy = vi.spyOn(foundersApi, "autoDiscoverFounder").mockResolvedValue({
        outcome: "verified",
        persisted: true,
        message: "Profile verified and saved.",
        discovered_url: "https://www.linkedin.com/in/asha-example",
        candidate: mockProfiles[0],
      });

      const queryClient = createTestQueryClient();
      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter>
            <AddProfileModal isOpen={true} onClose={vi.fn()} />
          </MemoryRouter>
        </QueryClientProvider>
      );

      // Fill in name and company
      fireEvent.change(screen.getByPlaceholderText("Asha Example"), {
        target: { value: "Asha Example" },
      });
      fireEvent.change(screen.getByPlaceholderText("Example Corp"), {
        target: { value: "Example Corp" },
      });

      // Submit Find profile form
      const submitBtn = screen.getByRole("button", { name: /find profile/i });
      fireEvent.submit(submitBtn.closest("form")!);

      await waitFor(() => {
        expect(autoDiscoverSpy).toHaveBeenCalledWith(
          expect.objectContaining({
            founder_name: "Asha Example",
            company_name: "Example Corp",
          }),
          undefined
        );
      });
    });

    it("transitions to fallback manual entry when auto-discover is blocked", async () => {
      vi.spyOn(foundersApi, "autoDiscoverFounder").mockResolvedValue({
        outcome: "blocked",
        persisted: false,
        message: "Scraping blocked by bot challenge (HTTP 999).",
        discovered_url: "https://www.linkedin.com/in/asha-example",
        candidate: null,
      });

      const queryClient = createTestQueryClient();
      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter>
            <AddProfileModal isOpen={true} onClose={vi.fn()} />
          </MemoryRouter>
        </QueryClientProvider>
      );

      fireEvent.change(screen.getByPlaceholderText("Asha Example"), {
        target: { value: "Asha Example" },
      });

      const submitBtn = screen.getByRole("button", { name: /find profile/i });
      fireEvent.submit(submitBtn.closest("form")!);

      await waitFor(() => {
        expect(
          screen.getByText(/We couldn't retrieve this profile automatically/i)
        ).toBeInTheDocument();
        expect(
          screen.getByPlaceholderText(/Paste public profile text/i)
        ).toBeInTheDocument();
      });
    });
  });

  describe("GuardedDeleteModal", () => {
    it("disables deletion button until exact slug is entered", () => {
      const onConfirm = vi.fn();
      render(
        <GuardedDeleteModal
          isOpen={true}
          onClose={vi.fn()}
          onConfirm={onConfirm}
          slug="asha-example-example-corp"
          founderName="Asha Example"
          isLoading={false}
        />
      );

      const deleteBtn = screen.getByRole("button", { name: /Permanently Delete/i });
      expect(deleteBtn).toBeDisabled();

      const input = screen.getByPlaceholderText("Type slug here...");
      fireEvent.change(input, { target: { value: "wrong-slug" } });
      expect(deleteBtn).toBeDisabled();

      fireEvent.change(input, { target: { value: "asha-example-example-corp" } });
      expect(deleteBtn).not.toBeDisabled();

      fireEvent.click(deleteBtn);
      expect(onConfirm).toHaveBeenCalled();
    });
  });
});
