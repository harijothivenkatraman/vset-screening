import React, { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ArrowLeft, Cpu, HardDrive, Search, Sparkles } from "lucide-react";
import { Badge } from "@/shared/ui/Badge";
import {
  useDiscoveryHealth,
  useResolveCandidates,
  useStartDiscoveryJob,
} from "../hooks";
import { ResolveCandidatesRequest, ResolveCandidatesResponse } from "../types";
import { CandidateReview } from "./CandidateReview";
import { DiscoveryForm } from "./DiscoveryForm";
import { JobProgress } from "./JobProgress";

type Step = "form" | "review" | "progress";

export const DiscoverPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const prefillCompany = searchParams.get("company") || "";
  const prefillFoundersParam = searchParams.get("founders") || searchParams.get("founder") || "";
  const prefillFounders = prefillFoundersParam
    ? prefillFoundersParam.split(",").map((s) => s.trim()).filter(Boolean)
    : [];

  const initialFormValues: Partial<ResolveCandidatesRequest> = {
    company_name: prefillCompany,
    founder_names: prefillFounders.length > 0 ? prefillFounders : undefined,
  };

  const [step, setStep] = useState<Step>("form");
  const [formValues, setFormValues] = useState<ResolveCandidatesRequest | null>(null);
  const [resolveData, setResolveData] = useState<ResolveCandidatesResponse | null>(null);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);

  const [apiKey, setApiKeyState] = useState<string>(() => sessionStorage.getItem("vset_admin_api_key") || "");

  const setApiKey = (key: string) => {
    setApiKeyState(key);
    sessionStorage.setItem("vset_admin_api_key", key);
  };

  const { data: health } = useDiscoveryHealth();
  const resolveMutation = useResolveCandidates(apiKey);
  const startJobMutation = useStartDiscoveryJob(apiKey);

  const handleFormSubmit = async (values: ResolveCandidatesRequest, reviewBeforeStart: boolean) => {
    setFormValues(values);
    try {
      const data = await resolveMutation.mutateAsync(values);
      setResolveData(data);

      if (!reviewBeforeStart) {
        const confirmedUrls: Record<string, string> = {};
        for (const [category, candidates] of Object.entries(data.candidates)) {
          if (candidates && candidates.length > 0) {
            confirmedUrls[category] = candidates[0].url;
          }
        }

        try {
          const resp = await startJobMutation.mutateAsync({
            company_name: values.company_name,
            founder_names: values.founder_names,
            confirmed_urls: confirmedUrls,
          });
          setActiveJobId(resp.job_id);
          setStep("progress");
          return;
        } catch (startErr) {
          console.error(startErr);
        }
      }

      setStep("review");
    } catch (err) {
      // If error occurs, create empty fallback response allowing manual input
      setResolveData({
        candidates: {},
        search_unavailable: true,
        error_message: (err as Error).message || "Search failed",
      });
      setStep("review");
    }
  };

  const handleConfirmSources = async (
    confirmedUrls: Record<string, string>,
    manualEvidence?: Record<string, any>,
  ) => {
    if (!formValues) return;
    try {
      const resp = await startJobMutation.mutateAsync({
        company_name: formValues.company_name,
        founder_names: formValues.founder_names,
        confirmed_urls: confirmedUrls,
        manual_evidence: manualEvidence,
      });
      setActiveJobId(resp.job_id);
      setStep("progress");
    } catch (err) {
      alert(`Failed to start discovery job: ${(err as Error).message}`);
    }
  };

  const handleReset = () => {
    setStep("form");
    setFormValues(null);
    setResolveData(null);
    setActiveJobId(null);
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* Top Header */}
      <header className="h-(--topbar-height) bg-white border-b border-slate-200 sticky top-0 z-30 px-4 sm:px-8 flex items-center justify-between shadow-2xs">
        <div className="flex items-center gap-4">
          <Link
            to="/"
            className="p-1.5 rounded text-slate-500 hover:text-slate-900 hover:bg-slate-100 transition-colors"
            title="Back to dashboard"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div className="flex items-baseline gap-2">
            <span className="font-extrabold tracking-tight text-xl text-[#1e2a3a]">
              vSET
            </span>
            <span className="text-[10px] uppercase font-bold tracking-widest text-slate-400">
              Company Discovery
            </span>
          </div>
        </div>

        {/* System Health Status Pills */}
        <div className="flex items-center gap-3 text-xs">
          <div className="flex items-center gap-2 mr-2">
            <label className="text-slate-500 font-medium hidden sm:inline-block">Admin API Key</label>
            <input 
              type="password" 
              value={apiKey} 
              onChange={(e) => setApiKey(e.target.value)} 
              className="px-2 py-1 border border-slate-200 rounded-md text-xs w-24 sm:w-32 focus:outline-hidden focus:ring-2 focus:ring-blue-500"
              placeholder="API Key"
            />
          </div>
          {health && (
            <>
              <span className="hidden sm:inline-flex items-center gap-1.5 text-slate-500">
                <HardDrive className="w-3.5 h-3.5" />
                {health.free_disk_gb.toFixed(1)} GB disk free
              </span>
              <Badge
                variant={health.llm_reachable ? (health.model_available === false ? "warning" : "success") : "warning"}
                className="py-1 px-2.5 flex items-center gap-1"
              >
                <Cpu className="w-3 h-3" />
                {!health.llm_reachable ? "Rules-first mode" : (health.model_available === false ? "LLM: model not loaded" : `LLM: ${health.llm_model}`)}
              </Badge>
            </>
          )}
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 py-10 px-4 sm:px-8 max-w-(--content-max-width) w-full mx-auto">
        {step === "form" && (
          <DiscoveryForm
            initialValues={formValues || initialFormValues}
            isLoading={resolveMutation.isPending}
            onSubmit={handleFormSubmit}
          />
        )}

        {step === "review" && formValues && resolveData && (
          <CandidateReview
            companyName={formValues.company_name}
            founderNames={formValues.founder_names}
            resolveData={resolveData}
            isStarting={startJobMutation.isPending}
            onBack={() => setStep("form")}
            onConfirm={handleConfirmSources}
          />
        )}

        {step === "progress" && activeJobId && (
          <JobProgress 
            jobId={activeJobId} 
            apiKey={apiKey} 
            onReset={handleReset}
            onBackToReview={() => setStep("review")}
          />
        )}
      </main>
    </div>
  );
};
