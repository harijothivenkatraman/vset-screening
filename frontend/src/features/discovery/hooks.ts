import { useMutation, useQuery } from "@tanstack/react-query";
import {
  getDiscoveryHealth,
  getDiscoveryJobStatus,
  resolveCandidates,
  startDiscoveryJob,
} from "./api";
import {
  DiscoveryHealth,
  DiscoveryJobStatus,
  ResolveCandidatesRequest,
  ResolveCandidatesResponse,
  StartDiscoveryJobRequest,
  StartDiscoveryJobResponse,
} from "./types";

export const discoveryKeys = {
  all: ["discovery"] as const,
  health: () => [...discoveryKeys.all, "health"] as const,
  job: (id: string) => [...discoveryKeys.all, "job", id] as const,
};

export function useDiscoveryHealth() {
  return useQuery<DiscoveryHealth>({
    queryKey: discoveryKeys.health(),
    queryFn: getDiscoveryHealth,
    staleTime: 30_000,
  });
}

export function useResolveCandidates() {
  return useMutation<ResolveCandidatesResponse, Error, ResolveCandidatesRequest>({
    mutationFn: resolveCandidates,
  });
}

export function useStartDiscoveryJob() {
  return useMutation<StartDiscoveryJobResponse, Error, StartDiscoveryJobRequest>({
    mutationFn: startDiscoveryJob,
  });
}

export function useDiscoveryJobStatus(jobId: string | null) {
  return useQuery<DiscoveryJobStatus>({
    queryKey: discoveryKeys.job(jobId || ""),
    queryFn: () => getDiscoveryJobStatus(jobId!),
    enabled: Boolean(jobId),
    refetchInterval: (query) => {
      const job = query.state.data;
      if (!job) return 3000;
      if (
        job.state === "succeeded" ||
        job.state === "partial" ||
        job.state === "failed"
      ) {
        return false;
      }
      return 3000;
    },
  });
}
