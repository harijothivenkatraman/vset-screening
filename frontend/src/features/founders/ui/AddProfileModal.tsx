import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  FileText,
  Globe,
  Upload,
  AlertTriangle,
  CheckCircle2,
  AlertCircle,
  X,
  ExternalLink,
  ShieldAlert,
} from "lucide-react";
import { Button } from "@/shared/ui/Button";
import {
  useCreateFounder,
  useUploadFounderPdf,
  useTryPublicFetch,
  useSavePending,
} from "../hooks";
import { PublicFetchResponse } from "../types";

interface AddProfileModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: (slug: string) => void;
}

const MAX_PDF_BYTES = 2 * 1024 * 1024; // 2 MB

export const AddProfileModal: React.FC<AddProfileModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<"manual" | "fetch">("manual");

  // Form states - Manual
  const [founderName, setFounderName] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [notes, setNotes] = useState("");
  const [evidenceMode, setEvidenceMode] = useState<"text" | "pdf">("text");
  const [evidenceText, setEvidenceText] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [allowDuplicate, setAllowDuplicate] = useState(false);
  const [conflictSlug, setConflictSlug] = useState<string | null>(null);

  // Form states - Fetch
  const [fetchUrl, setFetchUrl] = useState("");
  const [fetchResult, setFetchResult] = useState<PublicFetchResponse | null>(null);
  const [generalError, setGeneralError] = useState<string | null>(null);

  const createMutation = useCreateFounder();
  const uploadPdfMutation = useUploadFounderPdf();
  const fetchMutation = useTryPublicFetch();
  const pendingMutation = useSavePending();

  if (!isOpen) return null;

  const resetState = () => {
    setFounderName("");
    setCompanyName("");
    setNotes("");
    setEvidenceText("");
    setSelectedFile(null);
    setFileError(null);
    setAllowDuplicate(false);
    setConflictSlug(null);
    setFetchUrl("");
    setFetchResult(null);
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
        `File size (${(file.size / (1024 * 1024)).toFixed(2)} MB) exceeds the 2 MB limit (Lightsail budget). Please select a file under 2 MB.`
      );
      setSelectedFile(null);
      return;
    }
    setSelectedFile(file);
  };

  // Submit Manual Evidence (Text or PDF)
  const handleManualSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setGeneralError(null);
    setConflictSlug(null);

    if (!founderName.trim()) {
      setGeneralError("Founder name is required.");
      return;
    }

    try {
      if (evidenceMode === "text") {
        if (!evidenceText.trim()) {
          setGeneralError("Please paste profile text evidence.");
          return;
        }
        const profile = await createMutation.mutateAsync({
          data: {
            founder_name: founderName.trim(),
            company_name: companyName.trim() || null,
            evidence_text: evidenceText.trim(),
            notes: notes.trim() || null,
            allow_duplicate: allowDuplicate,
          },
        });
        handleClose();
        if (onSuccess) onSuccess(profile.slug);
        else navigate(`/profiles/${profile.slug}`);
      } else {
        // PDF mode
        if (!selectedFile) {
          setGeneralError("Please select a PDF file under 2 MB.");
          return;
        }
        const formData = new FormData();
        formData.append("file", selectedFile);
        formData.append("founder_name", founderName.trim());
        if (companyName.trim()) formData.append("company_name", companyName.trim());
        if (notes.trim()) formData.append("notes", notes.trim());
        if (allowDuplicate) formData.append("allow_duplicate", "true");

        const profile = await uploadPdfMutation.mutateAsync({ formData });
        handleClose();
        if (onSuccess) onSuccess(profile.slug);
        else navigate(`/profiles/${profile.slug}`);
      }
    } catch (err: unknown) {
      if (typeof err === "object" && err !== null && "status" in err && (err as { status: number }).status === 409) {
        const errorData = (err as { data?: { existing_slug?: string; detail?: string } }).data;
        const slug = errorData?.existing_slug || null;
        setConflictSlug(slug);
        setGeneralError(
          errorData?.detail || "A profile for this founder and company already exists."
        );
      } else if (err instanceof Error) {
        setGeneralError(err.message);
      } else {
        setGeneralError("An error occurred while creating the profile.");
      }
    }
  };

  // Try Public Fetch
  const handleFetchSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setGeneralError(null);
    setFetchResult(null);

    if (!founderName.trim() || !fetchUrl.trim()) {
      setGeneralError("Founder name and LinkedIn URL are required.");
      return;
    }

    try {
      const res = await fetchMutation.mutateAsync({
        data: {
          founder_name: founderName.trim(),
          linkedin_url: fetchUrl.trim(),
          company_name: companyName.trim() || null,
          save_as_pending: false,
        },
      });
      setFetchResult(res);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setGeneralError(err.message);
      } else {
        setGeneralError("Fetch attempt failed.");
      }
    }
  };

  // Save as Pending from Blocked Fetch
  const handleSavePending = async () => {
    setGeneralError(null);
    try {
      const profile = await pendingMutation.mutateAsync({
        data: {
          founder_name: founderName.trim(),
          linkedin_url: fetchUrl.trim() || null,
          company_name: companyName.trim() || null,
          notes: notes.trim() || "Saved as pending after blocked public fetch",
          verification_reason: fetchResult?.failure_reason || "Public fetch blocked",
        },
      });
      handleClose();
      if (onSuccess) onSuccess(profile.slug);
      else navigate(`/profiles/${profile.slug}`);
    } catch (err: unknown) {
      if (err instanceof Error) setGeneralError(err.message);
      else setGeneralError("Failed to save pending profile.");
    }
  };

  // Switch to Manual tab with pre-filled details
  const handleSwitchToManual = () => {
    setActiveTab("manual");
    setEvidenceMode("text");
  };

  const isSubmitting =
    createMutation.isPending ||
    uploadPdfMutation.isPending ||
    fetchMutation.isPending ||
    pendingMutation.isPending;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="add-profile-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs"
    >
      <div className="bg-white rounded-xl shadow-2xl border border-slate-200 w-full max-w-xl overflow-hidden flex flex-col max-h-[92vh]">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50/80">
          <div>
            <h2 id="add-profile-modal-title" className="text-base font-semibold text-slate-900">
              Add Founder Profile
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Ingest verifiable profile evidence or test public scraping diagnostics
            </p>
          </div>
          <button
            onClick={handleClose}
            className="text-slate-400 hover:text-slate-600 p-1 rounded-md transition-colors"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-slate-200 bg-slate-50 px-6 pt-2">
          <button
            type="button"
            onClick={() => setActiveTab("manual")}
            className={`flex items-center gap-2 px-4 py-2.5 text-xs font-medium border-b-2 transition-colors ${
              activeTab === "manual"
                ? "border-sky-600 text-sky-700 bg-white rounded-t-lg"
                : "border-transparent text-slate-600 hover:text-slate-900"
            }`}
          >
            <FileText className="w-4 h-4" />
            <span>Manual Evidence (Text / PDF)</span>
            <span className="text-[10px] bg-sky-100 text-sky-800 px-1.5 py-0.2 rounded font-semibold">
              Primary
            </span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("fetch")}
            className={`flex items-center gap-2 px-4 py-2.5 text-xs font-medium border-b-2 transition-colors ${
              activeTab === "fetch"
                ? "border-sky-600 text-sky-700 bg-white rounded-t-lg"
                : "border-transparent text-slate-600 hover:text-slate-900"
            }`}
          >
            <Globe className="w-4 h-4" />
            <span>Try Public Fetch</span>
            <span className="text-[10px] bg-slate-200 text-slate-700 px-1.5 py-0.2 rounded">
              Diagnostic
            </span>
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-4">
          {generalError && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-800 flex items-start gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-600 mt-0.5" />
              <div className="flex-1">{generalError}</div>
            </div>
          )}

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
              <div className="flex items-center gap-3 pt-1">
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
                <label className="flex items-center gap-2 cursor-pointer font-medium select-none">
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

          {/* TAB 1: MANUAL EVIDENCE */}
          {activeTab === "manual" && (
            <form onSubmit={handleManualSubmit} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label
                    htmlFor="manual-founder-name"
                    className="block text-xs font-medium text-slate-700 mb-1"
                  >
                    Founder Full Name <span className="text-rose-500">*</span>
                  </label>
                  <input
                    id="manual-founder-name"
                    type="text"
                    required
                    value={founderName}
                    onChange={(e) => setFounderName(e.target.value)}
                    placeholder="e.g. Arpita Kapoor"
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-sky-500"
                  />
                </div>
                <div>
                  <label
                    htmlFor="manual-company-name"
                    className="block text-xs font-medium text-slate-700 mb-1"
                  >
                    Company Name
                  </label>
                  <input
                    id="manual-company-name"
                    type="text"
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    placeholder="e.g. Mysa"
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-sky-500"
                  />
                </div>
              </div>

              {/* Mode switch: Paste Text vs Upload PDF */}
              <div>
                <span className="block text-xs font-medium text-slate-700 mb-1.5">
                  Evidence Format <span className="text-rose-500">*</span>
                </span>
                <div className="flex gap-4">
                  <label className="flex items-center gap-2 text-xs text-slate-700 cursor-pointer">
                    <input
                      type="radio"
                      name="evidenceMode"
                      value="text"
                      checked={evidenceMode === "text"}
                      onChange={() => setEvidenceMode("text")}
                      className="text-sky-600 focus:ring-sky-500"
                    />
                    <span>Paste Profile Text</span>
                  </label>
                  <label className="flex items-center gap-2 text-xs text-slate-700 cursor-pointer">
                    <input
                      type="radio"
                      name="evidenceMode"
                      value="pdf"
                      checked={evidenceMode === "pdf"}
                      onChange={() => setEvidenceMode("pdf")}
                      className="text-sky-600 focus:ring-sky-500"
                    />
                    <span>Upload LinkedIn PDF (&lt; 2 MB)</span>
                  </label>
                </div>
              </div>

              {evidenceMode === "text" ? (
                <div>
                  <label
                    htmlFor="manual-evidence-text"
                    className="block text-xs font-medium text-slate-700 mb-1"
                  >
                    Profile Evidence Text
                  </label>
                  <textarea
                    id="manual-evidence-text"
                    rows={6}
                    required
                    value={evidenceText}
                    onChange={(e) => setEvidenceText(e.target.value)}
                    placeholder={`Paste text copied from LinkedIn profile, e.g.:\nCEO & Co-founder at Company\n\nExperience:\nCEO, Company (2022 - Present)\nVP Product, Prior Corp (2018 - 2022)\n\nEducation:\nB.S. Computer Science, University (2014 - 2018)`}
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-sky-500 font-mono"
                  />
                  <p className="text-[11px] text-slate-500 mt-1">
                    Contact info, personal phone numbers, and emails are scrubbed automatically before persistence.
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  <label
                    htmlFor="manual-pdf-upload"
                    className="block text-xs font-medium text-slate-700"
                  >
                    LinkedIn &quot;Save to PDF&quot; Document
                  </label>
                  <div className="border-2 border-dashed border-slate-300 rounded-lg p-5 text-center hover:border-sky-500 transition-colors bg-slate-50/50">
                    <Upload className="w-8 h-8 mx-auto text-slate-400 mb-2" />
                    <input
                      id="manual-pdf-upload"
                      type="file"
                      accept=".pdf,application/pdf"
                      onChange={handleFileChange}
                      className="block w-full text-xs text-slate-500 file:mr-4 file:py-1.5 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-sky-50 file:text-sky-700 hover:file:bg-sky-100 cursor-pointer"
                    />
                    <p className="text-[11px] text-slate-500 mt-2">
                      Strict 2 MB memory cap. Text is extracted locally using pure-Python streaming without OCR dependencies.
                    </p>
                  </div>
                  {fileError && (
                    <div className="p-2 bg-rose-50 border border-rose-200 rounded text-xs text-rose-700 flex items-center gap-1.5">
                      <AlertCircle className="w-4 h-4 shrink-0 text-rose-500" />
                      <span>{fileError}</span>
                    </div>
                  )}
                  {selectedFile && !fileError && (
                    <div className="p-2 bg-emerald-50 border border-emerald-200 rounded text-xs text-emerald-800 flex items-center gap-1.5">
                      <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
                      <span>
                        Selected: <strong>{selectedFile.name}</strong> (
                        {(selectedFile.size / 1024).toFixed(1)} KB)
                      </span>
                    </div>
                  )}
                </div>
              )}

              <div>
                <label htmlFor="manual-notes" className="block text-xs font-medium text-slate-700 mb-1">
                  Operator Notes (Optional)
                </label>
                <input
                  id="manual-notes"
                  type="text"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Optional verification notes or provenance notes..."
                  className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-sky-500"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
                <Button type="button" variant="outline" size="sm" onClick={handleClose}>
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant="primary"
                  size="sm"
                  disabled={isSubmitting || (evidenceMode === "pdf" && !selectedFile)}
                >
                  {isSubmitting ? "Processing..." : "Create Founder Profile"}
                </Button>
              </div>
            </form>
          )}

          {/* TAB 2: TRY PUBLIC FETCH */}
          {activeTab === "fetch" && (
            <div className="space-y-4">
              <div className="p-3 bg-slate-100 border border-slate-200 rounded-lg text-xs text-slate-700 space-y-1">
                <p className="font-semibold text-slate-900 flex items-center gap-1.5">
                  <ShieldAlert className="w-4 h-4 text-slate-600" />
                  <span>Public Retrieval Limits</span>
                </p>
                <p>
                  LinkedIn blocks cloud datacenter IPs (HTTP 999 bot challenge).
                  Failed or blocked attempts are <strong>never persisted automatically</strong> to keep the catalog clean.
                </p>
              </div>

              <form onSubmit={handleFetchSubmit} className="space-y-3">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label
                      htmlFor="fetch-founder-name"
                      className="block text-xs font-medium text-slate-700 mb-1"
                    >
                      Founder Full Name <span className="text-rose-500">*</span>
                    </label>
                    <input
                      id="fetch-founder-name"
                      type="text"
                      required
                      value={founderName}
                      onChange={(e) => setFounderName(e.target.value)}
                      placeholder="e.g. Asha Example"
                      className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-sky-500"
                    />
                  </div>
                  <div>
                    <label
                      htmlFor="fetch-company-name"
                      className="block text-xs font-medium text-slate-700 mb-1"
                    >
                      Company Name
                    </label>
                    <input
                      id="fetch-company-name"
                      type="text"
                      value={companyName}
                      onChange={(e) => setCompanyName(e.target.value)}
                      placeholder="e.g. Example Corp"
                      className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-sky-500"
                    />
                  </div>
                </div>

                <div>
                  <label
                    htmlFor="fetch-linkedin-url"
                    className="block text-xs font-medium text-slate-700 mb-1"
                  >
                    Public LinkedIn URL <span className="text-rose-500">*</span>
                  </label>
                  <input
                    id="fetch-linkedin-url"
                    type="url"
                    required
                    value={fetchUrl}
                    onChange={(e) => setFetchUrl(e.target.value)}
                    placeholder="https://www.linkedin.com/in/username"
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-sky-500 font-mono"
                  />
                </div>

                <div className="flex items-center justify-end pt-1">
                  <Button
                    type="submit"
                    variant="primary"
                    size="sm"
                    disabled={fetchMutation.isPending}
                  >
                    {fetchMutation.isPending ? "Executing Scraper..." : "Execute Public Fetch"}
                  </Button>
                </div>
              </form>

              {/* Diagnostic Results Card */}
              {fetchResult && (
                <div className="mt-4 pt-4 border-t border-slate-200">
                  {fetchResult.is_blocked ? (
                    <div className="p-4 bg-amber-50 border border-amber-300 rounded-lg space-y-3">
                      <div className="flex items-start gap-2">
                        <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                        <div>
                          <h4 className="text-xs font-bold text-amber-900 uppercase tracking-wide">
                            Fetch Blocked by Bot Protection
                          </h4>
                          <p className="text-xs text-amber-800 mt-1 leading-relaxed">
                            {fetchResult.message}
                          </p>
                          {fetchResult.failure_reason && (
                            <p className="text-[11px] font-mono text-amber-700 bg-amber-100/70 p-1.5 rounded mt-2">
                              Diagnostic: {fetchResult.failure_reason}
                            </p>
                          )}
                        </div>
                      </div>

                      <div className="pt-2 flex flex-wrap items-center gap-2">
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={handleSavePending}
                          disabled={pendingMutation.isPending}
                          className="bg-white border-amber-300 text-amber-900 hover:bg-amber-100/50"
                        >
                          {pendingMutation.isPending ? "Saving..." : "Save as Pending Evidence"}
                        </Button>
                        <Button
                          type="button"
                          variant="primary"
                          size="sm"
                          onClick={handleSwitchToManual}
                        >
                          Provide Text / PDF Instead
                        </Button>
                      </div>
                    </div>
                  ) : fetchResult.candidate ? (
                    <div className="p-4 bg-emerald-50 border border-emerald-300 rounded-lg space-y-3">
                      <div className="flex items-center gap-2 text-emerald-800 font-semibold text-xs">
                        <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                        <span>Profile Successfully Retrieved</span>
                      </div>
                      <div className="text-xs text-emerald-900 space-y-1">
                        <p><strong>Name:</strong> {fetchResult.candidate.founder_name}</p>
                        {fetchResult.candidate.headline && (
                          <p><strong>Headline:</strong> {fetchResult.candidate.headline}</p>
                        )}
                        <p>
                          <strong>Experience:</strong> {fetchResult.candidate.experience_timeline.length} roles found
                        </p>
                        <p>
                          <strong>Education:</strong> {fetchResult.candidate.education.length} records found
                        </p>
                      </div>
                      <div className="pt-2">
                        <Button
                          type="button"
                          variant="primary"
                          size="sm"
                          onClick={() => {
                            if (fetchResult.candidate) {
                              handleClose();
                              navigate(`/profiles/${fetchResult.candidate.slug}`);
                            }
                          }}
                        >
                          View Retrieved Profile
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <div className="p-3 bg-slate-100 text-xs text-slate-700 rounded-lg">
                      {fetchResult.message}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
