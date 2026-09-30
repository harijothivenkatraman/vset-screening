import { useQuery } from "@tanstack/react-query";
import { fetchCompanies } from "@/features/companies/api";
import { CompanySummary } from "@/features/report/domain/types";

export function useCompanies() {
  return useQuery<CompanySummary[], Error>({
    queryKey: ["companies"],
    queryFn: fetchCompanies,
  });
}
