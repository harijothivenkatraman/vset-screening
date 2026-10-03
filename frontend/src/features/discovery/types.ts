export interface CandidateItem {
  url: string;
  title: string;
  snippet: string;
  domain: string;
  confidence: number;
  category: string;
  search_query: string;
  entity_name: string;
}

export interface ResolveCandidatesRequest {
  company_name: string;
  founder_names: string[];
  website_override?: string | null;
  company_linkedin_override?: string | null;
  founder_linkedin_overrides?: Record<string, string> | null;
}

export interface ResolveCandidatesResponse {
  candidates: Record<string, CandidateItem[]>;
  search_unavailable: boolean;
  error_message?: string | null;
}

export interface ManualEvidenceItem {
  text?: string;
  pdf_base64?: string;
  pdf_filename?: string;
}

export interface StartDiscoveryJobRequest {
  company_name: string;
  founder_names: string[];
  confirmed_urls: Record<string, string>;
  manual_evidence?: Record<string, ManualEvidenceItem>;
}

export interface StartDiscoveryJobResponse {
  job_id: string;
  state: "queued" | "running" | "succeeded" | "partial" | "failed";
  message: string;
}

export interface SourceDiagnostic {
  url: string;
  outcome: string;
  bytes_fetched: number;
  fields_extracted: string[];
  error_details?: string | null;
}

export interface DiscoveryJobStatus {
  job_id: string;
  company_name: string;
  state: "queued" | "running" | "succeeded" | "partial" | "failed";
  stage: string;
  progress: number;
  warnings: string[];
  result_slug?: string | null;
  error_message?: string | null;
  diagnostics?: SourceDiagnostic[];
}

export interface DiscoveryHealth {
  status: "healthy" | "degraded";
  discovery_enabled: boolean;
  llm_reachable: boolean;
  model_available?: boolean;
  llm_model: string;
  search_providers: string[];
  free_disk_gb: number;
}
