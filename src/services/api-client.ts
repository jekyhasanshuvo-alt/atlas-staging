import { z } from "zod";
import { apiBaseUrl, offlineDemo } from "./config";
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number | null = null,
  ) {
    super(message);
    this.name = "ApiError";
  }
}
export async function apiRequest<T>(
  path: string,
  schema: z.ZodType<T>,
  params: URLSearchParams = new URLSearchParams(),
  fetcher: typeof fetch = fetch,
  timeoutMs = 8000,
  baseUrl = apiBaseUrl,
): Promise<T> {
  if (offlineDemo) throw new ApiError("API access is disabled in this offline demo.", 503);
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetcher(
      `${baseUrl}${path}${params.size ? "?" + params.toString() : ""}`,
      {
        headers: { Accept: "application/json" },
        signal: controller.signal,
        cache: "no-store",
      },
    );
    if (!response.ok)
      throw new ApiError(
        response.status === 404
          ? "This catalog record was not found."
          : response.status === 422
            ? "The catalog filters are invalid. Review your selections."
            : "The catalog API is unavailable. Please try again.",
        response.status,
      );
    let payload: unknown;
    try {
      payload = await response.json();
    } catch {
      throw new ApiError(
        "The catalog API returned an incompatible response. Please try again.",
      );
    }
    const parsed = schema.safeParse(payload);
    if (!parsed.success)
      throw new ApiError(
        "The catalog API returned an incompatible response. Please try again.",
      );
    return parsed.data;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (controller.signal.aborted)
      throw new ApiError("The catalog request timed out. Please try again.");
    throw new ApiError(
      "Cannot connect to the catalog API. Check that FastAPI is running, then try again.",
    );
  } finally {
    clearTimeout(timer);
  }
}
export function queryParams(
  values: Record<string, string | number | boolean | undefined | string[]>,
) {
  const params = new URLSearchParams();
  Object.entries(values).forEach(([key, value]) => {
    if (value === undefined || value === "") return;
    if (Array.isArray(value)) value.forEach((v) => params.append(key, v));
    else params.set(key, String(value));
  });
  return params;
}
