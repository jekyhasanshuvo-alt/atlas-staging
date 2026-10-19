"use client";
import { useCallback, useEffect, useState } from "react";
import { catalogRepository } from "@/services/repository";
// Query contents are serialized: identical inputs do not refetch on unrelated local state changes.
// A response is rendered only for its own key. Cleanup prevents old responses replacing newer searches.
export function useCatalogQuery<K extends keyof typeof catalogRepository>(
  method: K,
  ...args: Parameters<(typeof catalogRepository)[K]>
) {
  type Result = Awaited<ReturnType<(typeof catalogRepository)[K]>>;
  const [attempt, setAttempt] = useState(0);
  const key = JSON.stringify({ method, args, attempt });
  const [state, setState] = useState<{
    key: string;
    data?: Result;
    error?: string;
  }>({ key: "" });
  useEffect(() => {
    let active = true;
    const request = JSON.parse(key) as {
      method: K;
      args: Parameters<(typeof catalogRepository)[K]>;
    };
    const run = catalogRepository[request.method] as (
      ...params: Parameters<(typeof catalogRepository)[K]>
    ) => Promise<Result>;
    // Debounce search changes; cancellation discards stale responses and prevents rapid keystrokes issuing requests.
    const timer = setTimeout(() => {
      run(...request.args)
        .then((data) => {
          if (active) setState({ key, data });
        })
        .catch((error: unknown) => {
          if (active)
            setState({
              key,
              error:
                error instanceof Error
                  ? error.message
                  : "The catalog could not be loaded.",
            });
        });
    }, 150);
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [key]);
  const retry = useCallback(() => setAttempt((value) => value + 1), []);
  const current = state.key === key ? state : undefined;
  return {
    data: current?.data,
    error: current?.error,
    loading: !current,
    retry,
  };
}
