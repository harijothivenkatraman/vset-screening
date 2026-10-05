import React, { useState } from "react";
import { ArrowLeft, CheckCircle2, ExternalLink, Sparkles, AlertTriangle } from "lucide-react";
import { Badge } from "@/shared/ui/Badge";
import { Button } from "@/shared/ui/Button";
import { Card } from "@/shared/ui/Card";
import { CandidateItem, ManualEvidenceItem, ResolveCandidatesResponse } from "../types";
import { useDiscoveryHealth } from "../hooks";

interface CandidateReviewProps {
  companyName: string;
  founderNames: string[];
  resolveData: ResolveCandidatesResponse;
  isStarting: boolean;
  onBack: () => void;
  onConfirm: (confirmedUrls: Record<string, string>, manualEvidence?: Record<string, ManualEvidenceItem>) => void;
}

export const CandidateReview: React.FC<CandidateReviewProps> = ({
  companyName,
  founderNames,
  resolveData,
  isStarting,
  onBack,
  onConfirm,
}) => {
  const { data: health } = useDiscoveryHealth();
  const isModelMissing = health?.model_available === false;
  // Initialize confirmed URLs from best candidates
  const [confirmedUrls, setConfirmedUrls] = useState<Record<string, string>>(() => {
    const initial: Record<string, string> = {};
    for (const [category, candidates] of Object.entries(resolveData.candidates)) {
      if (candidates && candidates.length > 0) {
        initial[category] = candidates[0].url;
      }
    }
    return initial;
  });

  const [manualEvidence, setManualEvidence] = useState<Record<string, ManualEvidenceItem>>({});

  const handleUrlChange = (category: string, url: string) => {
    setConfirmedUrls((prev) => ({
      ...prev,
      [category]: url,
    }));
  };

  const handleSelectCandidate = (category: string, candidate: CandidateItem) => {
    setConfirmedUrls((prev) => ({
      ...prev,
      [category]: candidate.url,
    }));
  };

  const handleManualTextChange = (category: string, text: string) => {
    setManualEvidence((prev) => {
      const existing = prev[category] || {};
      const updated = { ...existing, text };
      if (!text.trim() && !updated.pdf_base64) {
        const copy = { ...prev };
        delete copy[category];
        return copy;
      }
      return { ...prev, [category]: updated };
    });
  };

  const handleManualPdfUpload = (category: string, file: File | null) => {
    if (!file) {
      setManualEvidence((prev) => {
        const existing = prev[category];
        if (!existing) return prev;
        const { pdf_base64, pdf_filename, ...rest } = existing;
        if (!rest.text || !rest.text.trim()) {
          const copy = { ...prev };
          delete copy[category];
          return copy;
        }
        return { ...prev, [category]: rest };
      });
      return;
    }

    if (file.size > 2 * 1024 * 1024) {
      alert("PDF file size must be under 2 MB.");
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      const base64 = result.includes(",") ? result.split(",")[1] : result;
      setManualEvidence((prev) => ({
        ...prev,
        [category]: {
          ...(prev[category] || {}),
          pdf_base64: base64,
          pdf_filename: file.name,
        },
      }));
    };
    reader.readAsDataURL(file);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (Object.keys(manualEvidence).length > 0) {
      onConfirm(confirmedUrls, manualEvidence);
    } else {
      onConfirm(confirmedUrls);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={onBack}
          disabled={isStarting}
          className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-600 hover:text-slate-900 cursor-pointer disabled:opacity-50"
        >
          <ArrowLeft className="w-4 h-4" />
          Edit inputs
        </button>
        <Badge variant="navy" className="text-xs py-1 px-2.5">
          Review Step 2 of 3
        </Badge>
      </div>

      <div>
        <h2 className="text-2xl font-extrabold text-slate-900 tracking-tight">
          Review Public Footprint for {companyName}
        </h2>
        <p className="text-sm text-slate-500 mt-1">
          Review the discovered public sources below. You can confirm the identified URLs or
          provide your own direct links before extracting the report.
        </p>
      </div>

      {resolveData.search_unavailable && (
        <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg flex gap-3 text-amber-900 text-sm">
          <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">Search service currently unavailable</p>
            <p className="text-xs text-amber-800 mt-0.5">
              Automated web search was rate-limited or unreachable. Please paste the direct URLs
              for the company website and LinkedIn profiles below to proceed.
            </p>
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* 1. Company LinkedIn */}
        <ReviewCategorySection
          title="Company LinkedIn"
          description="Public company overview, headcount, sector, and specialties."
          categoryKey="company_linkedin"
          candidates={resolveData.candidates["company_linkedin"] || []}
          selectedUrl={confirmedUrls["company_linkedin"] || ""}
          manualItem={manualEvidence["company_linkedin"]}
          onSelect={(c) => handleSelectCandidate("company_linkedin", c)}
          onChangeUrl={(url) => handleUrlChange("company_linkedin", url)}
          onManualTextChange={(text) => handleManualTextChange("company_linkedin", text)}
          onManualPdfChange={(file) => handleManualPdfUpload("company_linkedin", file)}
          placeholder="https://www.linkedin.com/company/..."
        />

        {/* 2. Founders LinkedIn */}
        {founderNames.map((name) => {
          const catKey = `founder_linkedin_${slugify(name)}`;
          return (
            <ReviewCategorySection
              key={catKey}
              title={`${name} — LinkedIn Profile`}
              description={`Career timeline, education, and credentials for ${name}.`}
              categoryKey={catKey}
              entityName={name}
              companyName={companyName}
              candidates={resolveData.candidates[catKey] || []}
              selectedUrl={confirmedUrls[catKey] || ""}
              manualItem={manualEvidence[catKey]}
              onSelect={(c) => handleSelectCandidate(catKey, c)}
              onChangeUrl={(url) => handleUrlChange(catKey, url)}
              onManualTextChange={(text) => handleManualTextChange(catKey, text)}
              onManualPdfChange={(file) => handleManualPdfUpload(catKey, file)}
              placeholder={`https://www.linkedin.com/in/... (${name})`}
            />
          );
        })}

        {/* 3. Official Website */}
        <ReviewCategorySection
          title="Company Website"
          description="Primary product overview, value proposition, and customer messaging."
          categoryKey="website"
          candidates={resolveData.candidates["website"] || []}
          selectedUrl={confirmedUrls["website"] || ""}
          manualItem={manualEvidence["website"]}
          onSelect={(c) => handleSelectCandidate("website", c)}
          onChangeUrl={(url) => handleUrlChange("website", url)}
          onManualTextChange={(text) => handleManualTextChange("website", text)}
          onManualPdfChange={(file) => handleManualPdfUpload("website", file)}
          placeholder="https://example.com"
        />

        {/* 4. News Articles */}
        {resolveData.candidates["news"] && resolveData.candidates["news"].length > 0 && (
          <Card className="p-5 border border-slate-200">
            <h3 className="text-sm font-bold text-slate-800 uppercase tracking-wide">
              Relevant News & Funding Coverage
            </h3>
            <p className="text-xs text-slate-500 mt-0.5 mb-3">
              These articles will be referenced in the Funding and Validation sections.
            </p>
            <div className="space-y-2">
              {resolveData.candidates["news"].map((art, idx) => (
                <div
                  key={idx}
                  className="p-2.5 bg-slate-50 rounded border border-slate-200 text-xs flex items-center justify-between"
                >
                  <div className="min-w-0 pr-3">
                    <p className="font-semibold text-slate-800 truncate">{art.title}</p>
                    <p className="text-slate-500 truncate">{art.domain} — {art.snippet}</p>
                  </div>
                  <a
                    href={art.url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-slate-400 hover:text-slate-700 shrink-0"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                </div>
              ))}
            </div>
          </Card>
        )}

        {/* Action Button */}
        <div className="pt-4 flex items-center justify-between border-t border-slate-200">
          <Button
            type="button"
            variant="ghost"
            onClick={onBack}
            disabled={isStarting}
          >
            Cancel
          </Button>

          <Button type="submit" disabled={isStarting} size="lg">
            {isStarting ? (
              <span className="flex items-center gap-2">
                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Starting Discovery...
              </span>
            ) : (
              <span className="flex items-center gap-2">
                <Sparkles className="w-4 h-4" />
                Confirm Sources & Assemble Report
              </span>
            )}
          </Button>
        </div>

        {isModelMissing && (
          <div className="p-3 bg-blue-50 border border-blue-200 rounded-md text-blue-800 text-xs flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0 text-blue-600" />
            <span>
              Report will be assembled without the language model; some fields may be less complete. Run <code>ollama pull {health?.llm_model || "qwen2.5:7b-instruct"}</code> to enable full extraction.
            </span>
          </div>
        )}
      </form>
    </div>
  );
};

interface ReviewCategorySectionProps {
  title: string;
  description: string;
  categoryKey: string;
  entityName?: string;
  companyName?: string;
  candidates: CandidateItem[];
  selectedUrl: string;
  placeholder: string;
  manualItem?: ManualEvidenceItem;
  onSelect: (candidate: CandidateItem) => void;
  onChangeUrl: (url: string) => void;
  onManualTextChange?: (text: string) => void;
  onManualPdfChange?: (file: File | null) => void;
}

const ReviewCategorySection: React.FC<ReviewCategorySectionProps> = ({
  title,
  description,
  categoryKey,
  entityName,
  companyName,
  candidates,
  selectedUrl,
  placeholder,
  manualItem,
  onSelect,
  onChangeUrl,
  onManualTextChange,
  onManualPdfChange,
}) => {
  const isFounder = categoryKey.startsWith("founder_linkedin_");

  return (
    <Card className="p-5 border border-slate-200 space-y-3">
      <div>
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wide">{title}</h3>
          {isFounder && (
            <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
              Identity Verification Active
            </span>
          )}
        </div>
        <p className="text-xs text-slate-500 mt-0.5">{description}</p>
        {isFounder && (
          <p className="text-[11px] text-[#0369a1] mt-1 bg-sky-50/60 p-2 rounded border border-sky-100">
            <strong>Identity Policy:</strong> Candidates found via search require user confirmation to attach to the report. Homonyms (different companies with same name) must not be confirmed.
          </p>
        )}
      </div>

      {/* Candidates List if any */}
      {candidates.length > 0 && (
        <div className="space-y-2">
          {candidates.map((cand, idx) => {
            const isSelected = selectedUrl === cand.url;
            const candText = `${cand.title} ${cand.snippet} ${cand.url}`.toLowerCase();
            const nameMatch = entityName ? candText.includes(entityName.toLowerCase()) : false;
            const companyMatch = companyName ? candText.includes(companyName.toLowerCase()) : false;
            const isUserProvided = cand.confidence === 1.0 || cand.title.includes("user-provided");
            const isWebsiteSourced = cand.title.includes("website") || cand.url.includes("website");

            const sourceBadge = isUserProvided
              ? "P1: User confirmed"
              : isWebsiteSourced
              ? "P2: Website near name"
              : "P3: Search candidate";

            return (
              <div
                key={idx}
                onClick={() => onSelect(cand)}
                className={`p-3 rounded-md border text-xs cursor-pointer transition-all flex items-start justify-between gap-3 ${
                  isSelected
                    ? "bg-[#f0f7ff] border-[#0369a1] ring-1 ring-[#0369a1]"
                    : "bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50"
                }`}
              >
                <div className="min-w-0 flex-1 space-y-1.5">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <span className="font-semibold text-slate-800 truncate">{cand.title}</span>
                    <Badge
                      variant={cand.confidence >= 0.7 ? "success" : cand.confidence >= 0.4 ? "warning" : "default"}
                      className="text-[10px] py-0 px-1.5"
                    >
                      {Math.round(cand.confidence * 100)}% match
                    </Badge>
                  </div>

                  {/* Identity Indicators for founder profiles */}
                  {isFounder && (
                    <div className="flex flex-wrap items-center gap-1.5 pt-0.5">
                      <Badge
                        variant={nameMatch ? "success" : "default"}
                        className="text-[10px] py-0 px-1.5"
                      >
                        {nameMatch ? "✓ Name matched" : "Name mismatch"}
                      </Badge>
                      <Badge
                        variant={companyMatch ? "success" : "default"}
                        className="text-[10px] py-0 px-1.5"
                      >
                        {companyMatch ? "✓ Company mentioned" : "Company not verified"}
                      </Badge>
                      <Badge
                        variant="navy"
                        className="text-[10px] py-0 px-1.5"
                      >
                        {sourceBadge}
                      </Badge>
                      {!isUserProvided && !isWebsiteSourced && nameMatch && companyMatch && (
                        <Badge
                          variant="warning"
                          className="text-[10px] py-0 px-1.5"
                        >
                          Likely match (confirm to attach)
                        </Badge>
                      )}
                    </div>
                  )}

                  <p className="text-slate-500 truncate font-mono text-[11px]">{cand.url}</p>
                  {cand.snippet && (
                    <p className="text-slate-600 line-clamp-1 text-[11px]">{cand.snippet}</p>
                  )}
                </div>

                <div className="flex items-center gap-2 shrink-0 pt-0.5">
                  <a
                    href={cand.url}
                    target="_blank"
                    rel="noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    className="p-1 text-slate-400 hover:text-slate-700 transition-colors"
                    title="Open link in new tab"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                  {isSelected && <CheckCircle2 className="w-4 h-4 text-[#0369a1]" />}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Direct URL input override */}
      <div className="pt-1">
        <label className="block text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1">
          Confirmed URL
        </label>
        <input
          type="url"
          value={selectedUrl}
          onChange={(e) => onChangeUrl(e.target.value)}
          placeholder={placeholder}
          className="w-full px-3 py-1.5 text-xs font-mono border border-slate-300 rounded focus:outline-none focus:ring-1 focus:ring-[#1e2a3a] bg-white text-slate-900"
        />
      </div>

      {/* Manual evidence input (unverified) */}
      <div className="pt-3 border-t border-slate-100 space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-semibold text-slate-600 uppercase tracking-wider">
            Provide evidence manually (optional)
          </span>
          <Badge variant="navy" className="text-[10px] py-0.5 px-2">
            provided by user (unverified)
          </Badge>
        </div>
        <p className="text-[11px] text-slate-500">
          Paste profile text or upload an exported PDF if bot protection blocks this profile.
        </p>
        <textarea
          value={manualItem?.text || ""}
          onChange={(e) => onManualTextChange?.(e.target.value)}
          placeholder="Paste profile text, career history, education, or bio..."
          rows={2}
          className="w-full px-3 py-1.5 text-xs font-sans border border-slate-300 rounded focus:outline-none focus:ring-1 focus:ring-[#1e2a3a] bg-white text-slate-900"
        />
        <div className="flex items-center gap-3">
          <label className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded border border-slate-300 cursor-pointer transition-colors">
            <span>{manualItem?.pdf_filename ? "Replace PDF" : "Upload Profile PDF"}</span>
            <input
              type="file"
              accept=".pdf,application/pdf"
              className="hidden"
              onChange={(e) => onManualPdfChange?.(e.target.files?.[0] || null)}
            />
          </label>
          {manualItem?.pdf_filename && (
            <div className="flex items-center gap-1.5 text-xs text-slate-600">
              <span className="font-mono text-[11px] truncate max-w-xs">{manualItem.pdf_filename}</span>
              <button
                type="button"
                onClick={() => onManualPdfChange?.(null)}
                className="text-red-500 hover:text-red-700 text-xs ml-1 cursor-pointer font-bold"
                title="Remove PDF"
              >
                ×
              </button>
            </div>
          )}
          <span className="text-[10px] text-slate-400">Max 2 MB (parsed without OCR)</span>
        </div>
      </div>
    </Card>
  );
};

function slugify(text: string): string {
  return text.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
}
