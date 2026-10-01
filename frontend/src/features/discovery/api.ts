import { apiClient } from "@/core/http-client";
import {
  DiscoveryHealth,
  DiscoveryJobStatus,
  ResolveCandidatesRequest,
  ResolveCandidatesResponse,
  StartDiscoveryJobRequest,
  StartDiscoveryJobResponse,
} from "./types";

export async function resolveCandidates(
  request: ResolveCandidatesRequest
): Promise<ResolveCandidatesResponse> {
  return apiClient<ResolveCandidatesResponse>("/discovery/resolve", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function startDiscoveryJob(
  request: StartDiscoveryJobRequest
): Promise<StartDiscoveryJobResponse> {
  return apiClient<StartDiscoveryJobResponse>("/discovery/jobs", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function getDiscoveryJobStatus(
  jobId: string
): Promise<DiscoveryJobStatus> {
  return apiClient<DiscoveryJobStatus>(`/discovery/jobs/${jobId}`);
}

export async function getDiscoveryHealth(): Promise<DiscoveryHealth> {
  return apiClient<DiscoveryHealth>("/discovery/health");
}
