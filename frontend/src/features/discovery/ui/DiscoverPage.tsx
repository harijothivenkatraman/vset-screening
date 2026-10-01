import React, { useState } from "react";
import { Link } from "react-router-dom";
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
  const [step, setStep] = useState<Step>("form");
  const [formValues, setFormValues] = useState<ResolveCandidatesRequest | null>(null);
  const [resolveData, setResolveData] = useState<ResolveCandidatesResponse | null>(null);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);

  const { data: health } = useDiscoveryHealth();
  const resolveMutation = useResolveCandidates();
  const startJobMutation = useStartDiscoveryJob();

  const handleFormSubmit = async (values: ResolveCandidatesRequest) => {
    setFormValues(values);
    try {
      const data = await resolveMutation.mutateAsync(values);
      setResolveData(data);
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

  const handleConfirmSources = async (confirmedUrls: Record<string, string>) => {
    if (!formValues) return;
    try {
      const resp = await startJobMutation.mutateAsync({
        company_name: formValues.company_name,
        founder_names: formValues.founder_names,
        confirmed_urls: confirmedUrls,
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
          {health && (
            <>
              <span className="hidden sm:inline-flex items-center gap-1.5 text-slate-500">
                <HardDrive className="w-3.5 h-3.5" />
                {health.free_disk_gb.toFixed(1)} GB disk free
              </span>
              <Badge
                variant={health.llm_reachable ? "success" : "warning"}
                className="py-1 px-2.5 flex items-center gap-1"
              >
                <Cpu className="w-3 h-3" />
                {health.llm_reachable ? `LLM: ${health.llm_model}` : "Rules-first mode"}
              </Badge>
            </>
          )}
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 py-10 px-4 sm:px-8 max-w-(--content-max-width) w-full mx-auto">
        {step === "form" && (
          <DiscoveryForm
            initialValues={formValues || undefined}
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
          <JobProgress jobId={activeJobId} onReset={handleReset} />
        )}
      </main>
    </div>
  );
};
