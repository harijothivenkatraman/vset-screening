const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";
const API_KEY = import.meta.env.VITE_API_KEY || "dev-insecure-test-key-32-chars-long-00000";

export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public data?: unknown
  ) {
    super(`API Error ${status}: ${statusText}`);
    this.name = "ApiError";
  }
}

export async function apiClient<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = endpoint.startsWith("http") ? endpoint : `${API_BASE}${endpoint}`;

  const headers = new Headers(options?.headers);
  if (!headers.has("Content-Type") && !(options?.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (!headers.has("X-API-Key") && API_KEY) {
    headers.set("X-API-Key", API_KEY);
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorData: unknown;
    try {
      errorData = await response.json();
    } catch {
      errorData = await response.text();
    }
    throw new ApiError(response.status, response.statusText, errorData);
  }

  return response.json() as Promise<T>;
}
