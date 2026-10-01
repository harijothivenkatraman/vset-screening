import React, { useState } from "react";
import { ArrowLeft, CheckCircle2, ExternalLink, Sparkles, AlertTriangle } from "lucide-react";
import { Badge } from "@/shared/ui/Badge";
import { Button } from "@/shared/ui/Button";
import { Card } from "@/shared/ui/Card";
import { CandidateItem, ResolveCandidatesResponse } from "../types";

interface CandidateReviewProps {
  companyName: string;
  founderNames: string[];
  resolveData: ResolveCandidatesResponse;
  isStarting: boolean;
  onBack: () => void;
  onConfirm: (confirmedUrls: Record<string, string>) => void;
}

export const CandidateReview: React.FC<CandidateReviewProps> = ({
  companyName,
  founderNames,
  resolveData,
  isStarting,
  onBack,
  onConfirm,
}) => {
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

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onConfirm(confirmedUrls);
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
          onSelect={(c) => handleSelectCandidate("company_linkedin", c)}
          onChangeUrl={(url) => handleUrlChange("company_linkedin", url)}
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
              candidates={resolveData.candidates[catKey] || []}
              selectedUrl={confirmedUrls[catKey] || ""}
              onSelect={(c) => handleSelectCandidate(catKey, c)}
              onChangeUrl={(url) => handleUrlChange(catKey, url)}
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
          onSelect={(c) => handleSelectCandidate("website", c)}
          onChangeUrl={(url) => handleUrlChange("website", url)}
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
      </form>
    </div>
  );
};

interface ReviewCategorySectionProps {
  title: string;
  description: string;
  categoryKey: string;
  candidates: CandidateItem[];
  selectedUrl: string;
  placeholder: string;
  onSelect: (candidate: CandidateItem) => void;
  onChangeUrl: (url: string) => void;
}

const ReviewCategorySection: React.FC<ReviewCategorySectionProps> = ({
  title,
  description,
  candidates,
  selectedUrl,
  placeholder,
  onSelect,
  onChangeUrl,
}) => {
  return (
    <Card className="p-5 border border-slate-200 space-y-3">
      <div>
        <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wide">{title}</h3>
        <p className="text-xs text-slate-500 mt-0.5">{description}</p>
      </div>

      {/* Candidates List if any */}
      {candidates.length > 0 && (
        <div className="space-y-2">
          {candidates.map((cand, idx) => {
            const isSelected = selectedUrl === cand.url;
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
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-slate-800 truncate">{cand.title}</span>
                    <Badge
                      variant={cand.confidence >= 0.7 ? "success" : cand.confidence >= 0.4 ? "warning" : "default"}
                    >
                      {Math.round(cand.confidence * 100)}% match
                    </Badge>
                  </div>
                  <p className="text-slate-500 truncate mt-0.5 font-mono text-[11px]">{cand.url}</p>
                  {cand.snippet && (
                    <p className="text-slate-600 line-clamp-1 mt-1 text-[11px]">{cand.snippet}</p>
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
    </Card>
  );
};

function slugify(text: string): string {
  return text.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
}
