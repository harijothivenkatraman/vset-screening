import { apiClient } from "@/core/http-client";
import { CompanySummary } from "@/features/report/domain/types";

interface CompaniesResponse {
  companies: CompanySummary[];
}

export async function fetchCompanies(): Promise<CompanySummary[]> {
  const res = await apiClient<CompaniesResponse>("/companies");
  return res.companies;
}
