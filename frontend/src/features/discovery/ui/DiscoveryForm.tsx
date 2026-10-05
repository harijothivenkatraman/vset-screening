import React, { useState, useEffect } from "react";
import { Plus, Trash2, Search, Globe, Building2, User } from "lucide-react";
import { Button } from "@/shared/ui/Button";
import { Card } from "@/shared/ui/Card";
import { ResolveCandidatesRequest } from "../types";

interface DiscoveryFormProps {
  initialValues?: Partial<ResolveCandidatesRequest>;
  isLoading: boolean;
  onSubmit: (values: ResolveCandidatesRequest, reviewBeforeStart: boolean) => void;
}

export const DiscoveryForm: React.FC<DiscoveryFormProps> = ({
  initialValues,
  isLoading,
  onSubmit,
}) => {
  const [companyName, setCompanyName] = useState(initialValues?.company_name || "");
  const [founders, setFounders] = useState<string[]>(
    initialValues?.founder_names?.length ? initialValues.founder_names : [""]
  );
  const [websiteOverride, setWebsiteOverride] = useState(
    initialValues?.website_override || ""
  );
  const [companyLinkedinOverride, setCompanyLinkedinOverride] = useState(
    initialValues?.company_linkedin_override || ""
  );
  const [reviewBeforeStart, setReviewBeforeStart] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (initialValues) {
      setCompanyName(initialValues.company_name || "");
      setFounders(initialValues.founder_names?.length ? initialValues.founder_names : [""]);
      setWebsiteOverride(initialValues.website_override || "");
      setCompanyLinkedinOverride(initialValues.company_linkedin_override || "");
    }
  }, [initialValues]);

  const handleAddFounder = () => {
    setFounders([...founders, ""]);
  };

  const handleRemoveFounder = (index: number) => {
    if (founders.length <= 1) return;
    setFounders(founders.filter((_, i) => i !== index));
  };

  const handleFounderChange = (index: number, value: string) => {
    const updated = [...founders];
    updated[index] = value;
    setFounders(updated);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const trimmedCompany = companyName.trim();
    if (!trimmedCompany) {
      setError("Please enter a company name.");
      return;
    }

    const validFounders = founders.map((f) => f.trim()).filter(Boolean);
    if (validFounders.length === 0) {
      setError("Please specify at least one founder name.");
      return;
    }

    onSubmit({
      company_name: trimmedCompany,
      founder_names: validFounders,
      website_override: websiteOverride.trim() || undefined,
      company_linkedin_override: companyLinkedinOverride.trim() || undefined,
    }, reviewBeforeStart);
  };

  return (
    <Card className="p-6 max-w-2xl mx-auto shadow-sm border border-slate-200">
      <form onSubmit={handleSubmit} className="space-y-6">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <Building2 className="w-5 h-5 text-[#1e2a3a]" />
            Discover New Company
          </h2>
          <p className="text-sm text-slate-500 mt-1">
            Enter the company and founder details. We will find their public footprint across
            web, LinkedIn, and news sources to assemble an investor screening report.
          </p>
        </div>

        {error && (
          <div className="p-3 text-sm text-rose-700 bg-rose-50 border border-rose-200 rounded-md">
            {error}
          </div>
        )}

        {/* Company Name */}
        <div>
          <label
            htmlFor="company_name"
            className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1"
          >
            Company Name *
          </label>
          <input
            id="company_name"
            type="text"
            required
            value={companyName}
            onChange={(e) => setCompanyName(e.target.value)}
            placeholder="e.g. Terraspark Robotics"
            className="w-full px-3.5 py-2 text-sm border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#1e2a3a] focus:border-transparent bg-white text-slate-900 placeholder:text-slate-400"
          />
        </div>

        {/* Founders List */}
        <div>
          <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
            Founder(s) *
          </label>
          <div className="space-y-2.5">
            {founders.map((founder, idx) => (
              <div key={idx} className="flex items-center gap-2">
                <div className="relative flex-1">
                  <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                    <User className="w-4 h-4" />
                  </span>
                  <input
                    type="text"
                    required={idx === 0}
                    value={founder}
                    onChange={(e) => handleFounderChange(idx, e.target.value)}
                    placeholder={`Founder #${idx + 1} Name`}
                    className="w-full pl-9 pr-3.5 py-2 text-sm border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#1e2a3a] focus:border-transparent bg-white text-slate-900 placeholder:text-slate-400"
                  />
                </div>
                {founders.length > 1 && (
                  <button
                    type="button"
                    onClick={() => handleRemoveFounder(idx)}
                    className="p-2 text-slate-400 hover:text-rose-600 transition-colors cursor-pointer"
                    title="Remove founder"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>
            ))}
          </div>

          <button
            type="button"
            onClick={handleAddFounder}
            className="mt-2.5 inline-flex items-center gap-1.5 text-xs font-medium text-[#1e2a3a] hover:underline cursor-pointer"
          >
            <Plus className="w-3.5 h-3.5" />
            Add another founder
          </button>
        </div>

        {/* Optional Overrides */}
        <div className="pt-2 border-t border-slate-100 space-y-4">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
            Optional URL Overrides (bypasses search if known)
          </p>

          <div>
            <label
              htmlFor="website_url"
              className="block text-xs font-medium text-slate-600 mb-1"
            >
              Company Website URL
            </label>
            <div className="relative">
              <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                <Globe className="w-4 h-4" />
              </span>
              <input
                id="website_url"
                type="url"
                value={websiteOverride}
                onChange={(e) => setWebsiteOverride(e.target.value)}
                placeholder="https://example.com"
                className="w-full pl-9 pr-3.5 py-2 text-sm border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#1e2a3a] focus:border-transparent bg-white text-slate-900 placeholder:text-slate-400"
              />
            </div>
          </div>

          <div>
            <label
              htmlFor="linkedin_url"
              className="block text-xs font-medium text-slate-600 mb-1"
            >
              Company LinkedIn Page URL
            </label>
            <input
              id="linkedin_url"
              type="url"
              value={companyLinkedinOverride}
              onChange={(e) => setCompanyLinkedinOverride(e.target.value)}
              placeholder="https://linkedin.com/company/example"
              className="w-full px-3.5 py-2 text-sm border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#1e2a3a] focus:border-transparent bg-white text-slate-900 placeholder:text-slate-400"
            />
          </div>
        </div>

        {/* Submit */}
        <div className="pt-2 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
            <input
              type="checkbox"
              checked={reviewBeforeStart}
              onChange={(e) => setReviewBeforeStart(e.target.checked)}
              className="rounded border-slate-300 text-[#1e2a3a] focus:ring-[#1e2a3a]"
            />
            Review sources before starting (Advanced)
          </label>
          <Button type="submit" disabled={isLoading} size="lg" className="w-full sm:w-auto">
            {isLoading ? (
              <span className="flex items-center gap-2">
                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Searching Public Sources...
              </span>
            ) : (
              <span className="flex items-center gap-2">
                <Search className="w-4 h-4" />
                Find Public Footprint
              </span>
            )}
          </Button>
        </div>
      </form>
    </Card>
  );
};
