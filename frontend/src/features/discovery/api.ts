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
  request: ResolveCandidatesRequest,
  apiKey?: string
): Promise<ResolveCandidatesResponse> {
  return apiClient<ResolveCandidatesResponse>("/discovery/resolve", {
    method: "POST",
    body: JSON.stringify(request),
    apiKey,
  });
}

export async function startDiscoveryJob(
  request: StartDiscoveryJobRequest,
  apiKey?: string
): Promise<StartDiscoveryJobResponse> {
  return apiClient<StartDiscoveryJobResponse>("/discovery/jobs", {
    method: "POST",
    body: JSON.stringify(request),
    apiKey,
  });
}

export async function getDiscoveryJobStatus(
  jobId: string,
  apiKey?: string
): Promise<DiscoveryJobStatus> {
  return apiClient<DiscoveryJobStatus>(`/discovery/jobs/${jobId}`, { apiKey });
}

export async function getDiscoveryHealth(): Promise<DiscoveryHealth> {
  return apiClient<DiscoveryHealth>("/discovery/health");
}
