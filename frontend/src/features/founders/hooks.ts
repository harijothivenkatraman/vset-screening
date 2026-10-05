import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  autoDiscoverFounder,
  createFounderFromText,
  deleteFounder,
  getFounder,
  listFounders,
  restoreFounderVersion,
  savePendingFounder,
  tryPublicFetch,
  updateFounder,
  uploadFounderPdf,
} from "./api";
import {
  AddFounderProfileRequest,
  AutoDiscoverRequest,
  FetchFounderRequest,
  SavePendingProfileRequest,
  UpdateFounderProfileRequest,
} from "./types";

export function useFounders(params?: {
  search?: string;
  status?: string;
  page?: number;
  page_size?: number;
}) {
  return useQuery({
    queryKey: ["founders", params],
    queryFn: () => listFounders(params),
  });
}

export function useFounder(slug: string | undefined) {
  return useQuery({
    queryKey: ["founder", slug],
    queryFn: () => (slug ? getFounder(slug) : Promise.reject("Slug required")),
    enabled: Boolean(slug),
  });
}

export function useCreateFounder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ data, apiKey }: { data: AddFounderProfileRequest; apiKey?: string }) =>
      createFounderFromText(data, apiKey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["founders"] });
    },
  });
}

export function useUploadFounderPdf() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ formData, apiKey }: { formData: FormData; apiKey?: string }) =>
      uploadFounderPdf(formData, apiKey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["founders"] });
    },
  });
}

export function useTryPublicFetch() {
  return useMutation({
    mutationFn: ({ data, apiKey }: { data: FetchFounderRequest; apiKey?: string }) =>
      tryPublicFetch(data, apiKey),
  });
}

export function useSavePending() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ data, apiKey }: { data: SavePendingProfileRequest; apiKey?: string }) =>
      savePendingFounder(data, apiKey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["founders"] });
    },
  });
}

export function useUpdateFounder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      slug,
      data,
      apiKey,
    }: {
      slug: string;
      data: UpdateFounderProfileRequest;
      apiKey?: string;
    }) => updateFounder(slug, data, apiKey),
    onSuccess: (_, { slug }) => {
      queryClient.invalidateQueries({ queryKey: ["founder", slug] });
      queryClient.invalidateQueries({ queryKey: ["founders"] });
    },
  });
}

export function useRestoreVersion() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ slug, apiKey }: { slug: string; apiKey?: string }) =>
      restoreFounderVersion(slug, apiKey),
    onSuccess: (_, { slug }) => {
      queryClient.invalidateQueries({ queryKey: ["founder", slug] });
      queryClient.invalidateQueries({ queryKey: ["founders"] });
    },
  });
}

export function useDeleteFounder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      slug,
      confirm,
      apiKey,
    }: {
      slug: string;
      confirm: string;
      apiKey?: string;
    }) => deleteFounder(slug, confirm, apiKey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["founders"] });
    },
  });
}

export function useAutoDiscoverFounder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ data, apiKey }: { data: AutoDiscoverRequest; apiKey?: string }) =>
      autoDiscoverFounder(data, apiKey),
    onSuccess: (res) => {
      if (res.persisted) {
        queryClient.invalidateQueries({ queryKey: ["founders"] });
      }
    },
  });
}
