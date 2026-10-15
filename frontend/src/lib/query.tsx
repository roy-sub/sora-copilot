"use client";

/**
 * TanStack Query provider.
 *
 * Retries are left to the API client, which already understands the difference between a
 * sleeping backend and a real failure — a second retry layer here would multiply the
 * wait. A problem+json error is final.
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { ApiError } from "@/lib/api";

export function QueryProvider({ children }: { children: React.ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            retry: (_count, error) => !(error instanceof ApiError),
            refetchOnWindowFocus: false,
          },
          mutations: { retry: false },
        },
      }),
  );
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
