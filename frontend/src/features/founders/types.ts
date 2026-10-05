export type IdentityStatusType =
  | "verified"
  | "user_asserted"
  | "reference_screen"
  | "unverified";

export type RetrievalStatusType =
  | "found"
  | "not_found"
  | "blocked"
  | "pending_evidence"
  | "user_provided"
  | "reference_screen";

export interface ExperienceItem {
  title: string;
  company: string;
  duration?: string | null;
  location?: string | null;
  description?: string | null;
}

export interface EducationItem {
  school: string;
  degree?: string | null;
  field_of_study?: string | null;
  year?: string | null;
}

export interface CertificationItem {
  name: string;
  authority?: string | null;
  license_number?: string | null;
  year?: string | null;
}

export interface FounderRetrievalSummary {
  status: RetrievalStatusType;
  source_label: string;
  retrieved_at?: string | null;
  candidate_url?: string | null;
  verification_reason?: string | null;
}

export interface FounderProfile {
  id: string;
  slug: string;
  founder_name: string;
  company_name?: string | null;
  headline?: string | null;
  location?: string | null;
  about?: string | null;
  screening_assessment?: string | null;
  linkedin_url?: string | null;
  identity_status: IdentityStatusType;
  retrieval: FounderRetrievalSummary;
  experience_timeline: ExperienceItem[];
  education: EducationItem[];
  skills: string[];
  certifications: CertificationItem[];
  notes?: string | null;
  warnings: string[];
  has_previous_version: boolean;
  created_at: string;
  updated_at: string;
}

export interface FounderProfileListResponse {
  items: FounderProfile[];
  total: number;
  page: number;
  page_size: number;
}

export interface PublicFetchResponse {
  is_blocked: boolean;
  failure_reason?: string | null;
  message: string;
  persisted: boolean;
  candidate?: FounderProfile | null;
}

export interface AddFounderProfileRequest {
  founder_name: string;
  company_name?: string | null;
  evidence_text?: string | null;
  notes?: string | null;
  allow_duplicate?: boolean;
}

export interface FetchFounderRequest {
  founder_name: string;
  linkedin_url: string;
  company_name?: string | null;
  save_as_pending?: boolean;
}

export interface SavePendingProfileRequest {
  founder_name: string;
  linkedin_url?: string | null;
  company_name?: string | null;
  notes?: string | null;
  verification_reason?: string | null;
}

export interface UpdateFounderProfileRequest {
  evidence_text?: string | null;
  notes?: string | null;
  screening_assessment?: string | null;
}
