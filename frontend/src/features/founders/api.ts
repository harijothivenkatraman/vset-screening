import { apiClient } from "@/core/http-client";
import {
  AddFounderProfileRequest,
  AutoDiscoverRequest,
  AutoDiscoverResponse,
  FetchFounderRequest,
  FounderProfile,
  FounderProfileListResponse,
  PublicFetchResponse,
  SavePendingProfileRequest,
  UpdateFounderProfileRequest,
} from "./types";

export async function listFounders(params?: {
  search?: string;
  status?: string;
  page?: number;
  page_size?: number;
}): Promise<FounderProfileListResponse> {
  const query = new URLSearchParams();
  if (params?.search) query.set("search", params.search);
  if (params?.status && params.status !== "all") query.set("status", params.status);
  if (params?.page) query.set("page", params.page.toString());
  if (params?.page_size) query.set("page_size", params.page_size.toString());

  const qs = query.toString();
  return apiClient<FounderProfileListResponse>(`/founders${qs ? `?${qs}` : ""}`, {
    method: "GET",
  });
}

export async function getFounder(slug: string): Promise<FounderProfile> {
  return apiClient<FounderProfile>(`/founders/${encodeURIComponent(slug)}`, {
    method: "GET",
  });
}

export async function createFounderFromText(
  data: AddFounderProfileRequest,
  apiKey?: string
): Promise<FounderProfile> {
  return apiClient<FounderProfile>("/founders", {
    method: "POST",
    body: JSON.stringify(data),
    apiKey,
  });
}

export async function uploadFounderPdf(
  formData: FormData,
  apiKey?: string
): Promise<FounderProfile> {
  return apiClient<FounderProfile>("/founders/upload-pdf", {
    method: "POST",
    body: formData,
    apiKey,
  });
}

export async function tryPublicFetch(
  data: FetchFounderRequest,
  apiKey?: string
): Promise<PublicFetchResponse> {
  return apiClient<PublicFetchResponse>("/founders/fetch", {
    method: "POST",
    body: JSON.stringify(data),
    apiKey,
  });
}

export async function savePendingFounder(
  data: SavePendingProfileRequest,
  apiKey?: string
): Promise<FounderProfile> {
  return apiClient<FounderProfile>("/founders/pending", {
    method: "POST",
    body: JSON.stringify(data),
    apiKey,
  });
}

export async function updateFounder(
  slug: string,
  data: UpdateFounderProfileRequest,
  apiKey?: string
): Promise<FounderProfile> {
  return apiClient<FounderProfile>(`/founders/${encodeURIComponent(slug)}`, {
    method: "PUT",
    body: JSON.stringify(data),
    apiKey,
  });
}

export async function restoreFounderVersion(
  slug: string,
  apiKey?: string
): Promise<FounderProfile> {
  return apiClient<FounderProfile>(`/founders/${encodeURIComponent(slug)}/restore`, {
    method: "POST",
    apiKey,
  });
}

export async function deleteFounder(
  slug: string,
  confirm: string,
  apiKey?: string
): Promise<{ deleted: boolean; slug: string }> {
  return apiClient<{ deleted: boolean; slug: string }>(
    `/founders/${encodeURIComponent(slug)}?confirm=${encodeURIComponent(confirm)}`,
    {
      method: "DELETE",
      apiKey,
    }
  );
}

export async function exportFounderJson(slug: string): Promise<Record<string, unknown>> {
  return apiClient<Record<string, unknown>>(`/founders/${encodeURIComponent(slug)}/export`, {
    method: "GET",
  });
}

export async function autoDiscoverFounder(
  data: AutoDiscoverRequest,
  apiKey?: string
): Promise<AutoDiscoverResponse> {
  return apiClient<AutoDiscoverResponse>("/founders/auto-discover", {
    method: "POST",
    body: JSON.stringify(data),
    apiKey,
  });
}
