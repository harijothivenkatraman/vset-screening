import React, { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  Search,
  FileText,
  Upload,
  AlertTriangle,
  CheckCircle2,
  AlertCircle,
  X,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  Loader2,
  Clock,
} from "lucide-react";
import { Button } from "@/shared/ui/Button";
import {
  useAutoDiscoverFounder,
  useCreateFounder,
  useUploadFounderPdf,
  useSavePending,
} from "../hooks";
import { AutoDiscoverResponse, FounderProfile } from "../types";
import { getAdminKey } from "./AdminKeyModal";

interface AddProfileModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: (slug: string) => void;
}

const MAX_PDF_BYTES = 2 * 1024 * 1024; // 2 MB Lightsail cap

export const AddProfileModal: React.FC<AddProfileModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const navigate = useNavigate();
  const modalRef = useRef<HTMLDivElement>(null);

  // Form states
  const [founderName, setFounderName] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [profileUrl, setProfileUrl] = useState("");
  const [companyWebsite, setCompanyWebsite] = useState("");
  const [notes, setNotes] = useState("");

  // Flow states: 'idle' | 'searching' | 'likely_match' | 'fallback_manual'
  const [flowState, setFlowState] = useState<"idle" | "searching" | "likely_match" | "fallback_manual">("idle");
  const [autoDiscoverResult, setAutoDiscoverResult] = useState<AutoDiscoverResponse | null>(null);

  // Manual fallback inputs
  const [showDirectManual, setShowDirectManual] = useState(false);
  const [evidenceMode, setEvidenceMode] = useState<"text" | "pdf">("text");
  const [evidenceText, setEvidenceText] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [conflictSlug, setConflictSlug] = useState<string | null>(null);
  const [allowDuplicate, setAllowDuplicate] = useState(false);
  const [generalError, setGeneralError] = useState<string | null>(null);

  // Mutations
  const autoDiscoverMutation = useAutoDiscoverFounder();
  const createMutation = useCreateFounder();
  const uploadPdfMutation = useUploadFounderPdf();
  const pendingMutation = useSavePending();

  // Escape key handler
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        handleClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen]);

  if (!isOpen) return null;

  const resetState = () => {
    setFounderName("");
    setCompanyName("");
    setProfileUrl("");
    setCompanyWebsite("");
    setNotes("");
    setFlowState("idle");
    setAutoDiscoverResult(null);
    setShowDirectManual(false);
    setEvidenceMode("text");
    setEvidenceText("");
    setSelectedFile(null);
    setFileError(null);
    setConflictSlug(null);
    setAllowDuplicate(false);
    setGeneralError(null);
  };

  const handleClose = () => {
    resetState();
    onClose();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFileError(null);
    const file = e.target.files?.[0];
    if (!file) {
      setSelectedFile(null);
      return;
    }
    if (file.size > MAX_PDF_BYTES) {
      setFileError(
        `File size (${(file.size / (1024 * 1024)).toFixed(2)} MB) exceeds the 2 MB cap. Please select a file under 2 MB.`
      );
      setSelectedFile(null);
      return;
    }
    setSelectedFile(file);
  };

  // ── Primary Action: Find profile (Auto-extract flow) ───────────────────────
  const handleFindProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!founderName.trim()) {
      setGeneralError("Founder name is required.");
      return;
    }

    setGeneralError(null);
    setFlowState("searching");
    const adminKey = getAdminKey() || undefined;

    try {
      const res = await autoDiscoverMutation.mutateAsync({
        data: {
          founder_name: founderName.trim(),
          company_name: companyName.trim() || undefined,
          profile_url: profileUrl.trim() || undefined,
          company_website: companyWebsite.trim() || undefined,
        },
        apiKey: adminKey,
      });

      setAutoDiscoverResult(res);

      if (res.outcome === "verified" && res.candidate) {
        // Outcome 1: Verified match -> Saved and navigate
        const targetSlug = res.candidate.slug;
        handleClose();
        if (onSuccess) onSuccess(targetSlug);
        navigate(`/profiles/${targetSlug}`);
      } else if (res.outcome === "likely_match") {
        // Outcome 2: Likely match -> Needs confirmation in dialog
        setFlowState("likely_match");
      } else {
        // Outcome 3: Blocked or Not found -> In-place switch to manual input
        setFlowState("fallback_manual");
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to run automated profile search.";
      setGeneralError(msg);
      setFlowState("fallback_manual");
    }
  };

  // ── Manual / Fallback Submit ───────────────────────────────────────────────
  const handleManualSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!founderName.trim()) {
      setGeneralError("Founder name is required.");
      return;
    }

    setGeneralError(null);
    setConflictSlug(null);
    const adminKey = getAdminKey() || undefined;

    try {
      let saved: FounderProfile;

      if (evidenceMode === "pdf") {
        if (!selectedFile) {
          setFileError("Please choose a profile PDF to upload.");
          return;
        }
        const formData = new FormData();
        formData.append("founder_name", founderName.trim());
        if (companyName.trim()) formData.append("company_name", companyName.trim());
        if (notes.trim()) formData.append("notes", notes.trim());
        if (allowDuplicate) formData.append("allow_duplicate", "true");
        formData.append("file", selectedFile);

        saved = await uploadPdfMutation.mutateAsync({ formData, apiKey: adminKey });
      } else {
        if (!evidenceText.trim()) {
          setGeneralError("Please paste online profile text into the evidence box.");
          return;
        }
        saved = await createMutation.mutateAsync({
          data: {
            founder_name: founderName.trim(),
            company_name: companyName.trim() || undefined,
            evidence_text: evidenceText.trim(),
            notes: notes.trim() || undefined,
            allow_duplicate: allowDuplicate,
          },
          apiKey: adminKey,
        });
      }

      handleClose();
      if (onSuccess) onSuccess(saved.slug);
      navigate(`/profiles/${saved.slug}`);
    } catch (err: any) {
      const status = err?.status || err?.response?.status;
      const data = err?.data || err?.response?.data;
      if (status === 409 || data?.existing_slug || err?.existing_slug) {
        setConflictSlug(data?.existing_slug || err?.existing_slug || "existing-profile");
        setGeneralError(data?.detail || err?.detail || "A profile for this founder and company already exists.");
      } else {
        setGeneralError(err?.message || "Failed to save profile.");
      }
    }
  };

  // ── Save as Pending ────────────────────────────────────────────────────────
  const handleSaveAsPending = async () => {
    if (!founderName.trim()) return;
    const adminKey = getAdminKey() || undefined;

    try {
      const saved = await pendingMutation.mutateAsync({
        data: {
          founder_name: founderName.trim(),
          company_name: companyName.trim() || undefined,
          linkedin_url: autoDiscoverResult?.discovered_url || profileUrl.trim() || undefined,
          notes: notes.trim() || "Saved as pending evidence by operator",
          verification_reason: "Saved as pending after automated retrieval could not complete.",
        },
        apiKey: adminKey,
      });

      handleClose();
      if (onSuccess) onSuccess(saved.slug);
      navigate(`/profiles/${saved.slug}`);
    } catch (err: any) {
      setGeneralError(err?.message || "Failed to save profile as pending.");
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="add-profile-dialog-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs overflow-y-auto"
    >
      <div
        ref={modalRef}
        className="bg-white rounded-xl shadow-xl border border-slate-200 w-full max-w-xl overflow-hidden my-8"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50/70">
          <div>
            <h2 id="add-profile-dialog-title" className="text-base font-bold text-slate-900">
              Add Founder Profile
            </h2>
            <p className="text-xs text-slate-500">
              Find public profile online or provide manual profile evidence
            </p>
          </div>
          <button
            type="button"
            onClick={handleClose}
            className="text-slate-400 hover:text-slate-600 p-1 rounded-md transition-colors"
            aria-label="Close dialog"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* 409 Conflict Banner */}
          {conflictSlug && (
            <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-900 space-y-2">
              <div className="flex items-center gap-2 font-semibold">
                <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
                <span>Profile Conflict Detected</span>
              </div>
              <p>
                A profile for this founder and company already exists in the catalog (
                <code className="bg-amber-100 px-1 rounded font-mono text-[11px]">{conflictSlug}</code>
                ).
              </p>
              <div className="flex flex-wrap items-center gap-3 pt-1">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    handleClose();
                    navigate(`/profiles/${conflictSlug}`);
                  }}
                  className="bg-white"
                >
                  <ExternalLink className="w-3.5 h-3.5 mr-1" />
                  View Existing Profile
                </Button>
                <label className="flex items-center gap-2 cursor-pointer font-medium select-none text-slate-800">
                  <input
                    type="checkbox"
                    checked={allowDuplicate}
                    onChange={(e) => setAllowDuplicate(e.target.checked)}
                    className="rounded border-slate-300 text-sky-600 focus:ring-sky-500"
                  />
                  <span>Create anyway (auto-disambiguate slug)</span>
                </label>
              </div>
            </div>
          )}

          {generalError && !conflictSlug && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-800 flex items-start gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-600 mt-0.5" />
              <div className="flex-1">{generalError}</div>
            </div>
          )}

          {/* ── STATE 1: Searching Spinner ───────────────────────────────────── */}
          {flowState === "searching" && (
            <div className="py-12 flex flex-col items-center justify-center text-center space-y-4">
              <Loader2 className="w-10 h-10 text-sky-600 animate-spin" />
              <div className="space-y-1">
                <h3 className="text-sm font-semibold text-slate-900">
                  Searching for {founderName}...
                </h3>
                <p className="text-xs text-slate-500 max-w-sm">
                  Checking company website team pages and public search fallback. Verifying identity corroboration.
                </p>
              </div>
            </div>
          )}

          {/* ── STATE 2: Likely Match (Needs Confirmation) ────────────────────── */}
          {flowState === "likely_match" && autoDiscoverResult?.candidate && (
            <div className="space-y-4">
              <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl space-y-2">
                <div className="flex items-center gap-2 text-amber-900 font-semibold text-xs">
                  <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
                  <span>Candidate found — Needs confirmation</span>
                </div>
                <p className="text-xs text-amber-800 leading-relaxed">
                  We found an online profile matching <strong>{founderName}</strong> at <strong>{companyName || "the company"}</strong>, but it lacks full domain corroboration.
                </p>
                {autoDiscoverResult.discovered_url && (
                  <div className="pt-1">
                    <a
                      href={autoDiscoverResult.discovered_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-xs text-sky-700 hover:underline"
                    >
                      <span>{autoDiscoverResult.discovered_url}</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>
                )}
              </div>

              <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-2">
                <div className="text-xs font-semibold text-slate-900">
                  {autoDiscoverResult.candidate.founder_name}
                </div>
                {autoDiscoverResult.candidate.headline && (
                  <div className="text-xs text-slate-600">
                    {autoDiscoverResult.candidate.headline}
                  </div>
                )}
                <div className="text-[11px] text-slate-500">
                  Status: Saved as &ldquo;Needs confirmation&rdquo; in catalog
                </div>
              </div>

              <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setFlowState("fallback_manual")}
                  className="w-full sm:w-auto"
                >
                  Paste profile text instead
                </Button>

                <Button
                  type="button"
                  variant="primary"
                  size="sm"
                  onClick={() => {
                    const slug = autoDiscoverResult.candidate!.slug;
                    handleClose();
                    if (onSuccess) onSuccess(slug);
                    navigate(`/profiles/${slug}`);
                  }}
                  className="w-full sm:w-auto"
                >
                  <CheckCircle2 className="w-4 h-4 mr-1.5" />
                  View in Catalog
                </Button>
              </div>
            </div>
          )}

          {/* ── STATE 3: Fallback Manual (Blocked / Not found) ────────────────── */}
          {flowState === "fallback_manual" && (
            <div className="space-y-4">
              <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl space-y-2">
                <div className="flex items-center gap-2 text-amber-900 font-semibold text-xs">
                  <AlertCircle className="w-4 h-4 text-amber-600 shrink-0" />
                  <span>We couldn&apos;t retrieve this profile automatically</span>
                </div>
                <p className="text-xs text-amber-800 leading-relaxed">
                  Automated fetch was blocked by bot protection or no public profile could be confirmed. Paste the profile text or upload a &ldquo;Save to PDF&rdquo; export below.
                </p>
              </div>

              <form onSubmit={handleManualSubmit} className="space-y-4">
                {/* Method selector */}
                <div className="flex gap-2 p-1 bg-slate-100 rounded-lg">
                  <button
                    type="button"
                    onClick={() => setEvidenceMode("text")}
                    className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-md text-xs font-semibold transition-all ${
                      evidenceMode === "text"
                        ? "bg-white text-slate-900 shadow-xs"
                        : "text-slate-600 hover:text-slate-900"
                    }`}
                  >
                    <FileText className="w-3.5 h-3.5" />
                    <span>Paste Profile Text</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setEvidenceMode("pdf")}
                    className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-md text-xs font-semibold transition-all ${
                      evidenceMode === "pdf"
                        ? "bg-white text-slate-900 shadow-xs"
                        : "text-slate-600 hover:text-slate-900"
                    }`}
                  >
                    <Upload className="w-3.5 h-3.5" />
                    <span>Upload Profile PDF</span>
                  </button>
                </div>

                {evidenceMode === "text" ? (
                  <div>
                    <label className="block text-xs font-medium text-slate-700 mb-1">
                      Profile Text Evidence <span className="text-rose-500">*</span>
                    </label>
                    <textarea
                      value={evidenceText}
                      onChange={(e) => setEvidenceText(e.target.value)}
                      placeholder="Paste public profile text (headline, summary, experience timeline, education)..."
                      rows={5}
                      className="w-full p-3 text-xs font-mono border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-sky-500 bg-slate-50/50"
                      required
                    />
                  </div>
                ) : (
                  <div>
                    <label className="block text-xs font-medium text-slate-700 mb-1">
                      Profile PDF File <span className="text-rose-500">*</span>
                    </label>
                    <div className="border-2 border-dashed border-slate-300 rounded-lg p-5 text-center bg-slate-50/50 hover:bg-slate-50 transition-colors">
                      <Upload className="w-6 h-6 text-slate-400 mx-auto mb-2" />
                      <input
                        type="file"
                        accept="application/pdf"
                        onChange={handleFileChange}
                        className="text-xs text-slate-500 file:mr-3 file:py-1 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-sky-50 file:text-sky-700 hover:file:bg-sky-100"
                      />
                      <p className="text-[11px] text-slate-400 mt-2">
                        Upload a public profile &ldquo;Save to PDF&rdquo; export (Max 2 MB). Contact info &amp; PII are stripped automatically.
                      </p>
                    </div>
                    {fileError && <p className="text-xs text-rose-600 mt-1">{fileError}</p>}
                  </div>
                )}

                <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-3 border-t border-slate-200">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleSaveAsPending}
                    className="w-full sm:w-auto text-amber-700 hover:bg-amber-50 border-amber-300"
                    title="Persist profile as pending manual evidence"
                  >
                    <Clock className="w-3.5 h-3.5 mr-1 text-amber-600" />
                    Save as pending
                  </Button>

                  <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => setFlowState("idle")}
                    >
                      Back
                    </Button>
                    <Button
                      type="submit"
                      variant="primary"
                      size="sm"
                      disabled={createMutation.isPending || uploadPdfMutation.isPending}
                    >
                      {createMutation.isPending || uploadPdfMutation.isPending ? "Saving..." : "Save Profile"}
                    </Button>
                  </div>
                </div>
              </form>
            </div>
          )}

          {/* ── STATE 4: Idle Primary Form ───────────────────────────────────── */}
          {flowState === "idle" && (
            <form onSubmit={handleFindProfile} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Founder Name <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={founderName}
                    onChange={(e) => setFounderName(e.target.value)}
                    placeholder="Asha Example"
                    required
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-sky-500 bg-white"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Company Name
                  </label>
                  <input
                    type="text"
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    placeholder="Example Corp"
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-sky-500 bg-white"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">
                    Online Profile URL <span className="text-slate-400 font-normal">(optional)</span>
                  </label>
                  <input
                    type="url"
                    value={profileUrl}
                    onChange={(e) => setProfileUrl(e.target.value)}
                    placeholder="https://www.linkedin.com/in/asha-example"
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-sky-500 bg-white"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">
                    Company Website <span className="text-slate-400 font-normal">(optional)</span>
                  </label>
                  <input
                    type="url"
                    value={companyWebsite}
                    onChange={(e) => setCompanyWebsite(e.target.value)}
                    placeholder="https://example.com"
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-sky-500 bg-white"
                  />
                </div>
              </div>

              {/* Collapsible Direct Entry Accordion */}
              <div className="pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowDirectManual((prev) => !prev)}
                  className="flex items-center justify-between w-full text-xs font-medium text-slate-600 hover:text-slate-900 py-1"
                >
                  <span>Or enter profile text / upload PDF directly</span>
                  {showDirectManual ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </button>

                {showDirectManual && (
                  <div className="mt-3 p-3 bg-slate-50 border border-slate-200 rounded-xl space-y-3">
                    <div className="flex gap-2 p-1 bg-white rounded-lg border border-slate-200">
                      <button
                        type="button"
                        onClick={() => setEvidenceMode("text")}
                        className={`flex-1 py-1 text-xs font-medium rounded-md transition-all ${
                          evidenceMode === "text" ? "bg-slate-100 text-slate-900 font-semibold" : "text-slate-600"
                        }`}
                      >
                        Pasted Text
                      </button>
                      <button
                        type="button"
                        onClick={() => setEvidenceMode("pdf")}
                        className={`flex-1 py-1 text-xs font-medium rounded-md transition-all ${
                          evidenceMode === "pdf" ? "bg-slate-100 text-slate-900 font-semibold" : "text-slate-600"
                        }`}
                      >
                        Upload PDF (Max 2MB)
                      </button>
                    </div>

                    {evidenceMode === "text" ? (
                      <textarea
                        value={evidenceText}
                        onChange={(e) => setEvidenceText(e.target.value)}
                        placeholder="Paste online profile text here..."
                        rows={4}
                        className="w-full p-2.5 text-xs font-mono border border-slate-300 rounded-lg bg-white"
                      />
                    ) : (
                      <div>
                        <input
                          type="file"
                          accept="application/pdf"
                          onChange={handleFileChange}
                          className="text-xs text-slate-500 file:mr-2 file:py-1 file:px-2.5 file:rounded file:border-0 file:text-xs file:font-semibold file:bg-sky-50 file:text-sky-700"
                        />
                        {fileError && <p className="text-xs text-rose-600 mt-1">{fileError}</p>}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-end gap-2 pt-4 border-t border-slate-200">
                <Button type="button" variant="outline" size="sm" onClick={handleClose}>
                  Cancel
                </Button>
                {showDirectManual && (evidenceText.trim() || selectedFile) ? (
                  <Button
                    type="button"
                    variant="primary"
                    size="sm"
                    onClick={handleManualSubmit}
                    disabled={createMutation.isPending || uploadPdfMutation.isPending}
                  >
                    Save Manually
                  </Button>
                ) : (
                  <Button
                    type="submit"
                    variant="primary"
                    size="sm"
                    disabled={autoDiscoverMutation.isPending}
                    className="gap-1.5"
                  >
                    <Search className="w-3.5 h-3.5" />
                    <span>Find profile</span>
                  </Button>
                )}
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
