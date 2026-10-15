"use client";

/**
 * The typed API client.
 *
 * Two things it handles that a bare fetch does not:
 *
 * 1. **RFC 7807 problems.** Every backend error is `application/problem+json` with a
 *    machine-readable `code`, so callers branch on the code rather than on prose.
 * 2. **Render's cold start.** The free web service sleeps after ~15 minutes idle and can
 *    take half a minute to wake (build spec §14). A sleeping backend is not an error, so
 *    the first call retries with backoff and reports `warming` to the UI instead of
 *    failing. `onWarming` lets a screen show the warming state rather than a red box.
 *
 * Types are hand-written in Phase 1 and replaced by the generated client in Phase 3
 * (`openapi-typescript` over `backend/openapi.json`), so they cannot drift from FastAPI.
 */

import { env } from "@/lib/env";
import { accessToken } from "@/lib/supabase";

export interface Problem {
  type?: string;
  code: string;
  title: string;
  status: number;
  detail?: string;
  /** Field-level validation failures. */
  errors?: { field: string; message: string; type: string }[];
  /** Present on the 409 from POST /determine: nothing reaches the engine unconfirmed. */
  unconfirmed_fields?: string[];
  /** Present on the 402 from a plan limit. The upgrade panel is rendered from these
   *  fields rather than from the prose, so the copy and the numbers cannot disagree. */
  feature?: string;
  plan?: string;
  limit?: number | null;
  used?: number | null;
  upgrade_to?: string | null;
}

export class ApiError extends Error {
  readonly problem: Problem;

  constructor(problem: Problem) {
    super(problem.title);
    this.name = "ApiError";
    this.problem = problem;
  }

  get code(): string {
    return this.problem.code;
  }

  get status(): number {
    return this.problem.status;
  }

  /** A refusal for commercial rather than regulatory reasons. */
  get isPlanLimit(): boolean {
    return this.problem.code === "plan_limit";
  }
}

/** The backend is unreachable — asleep, restarting, or the network is down. */
export class ApiUnreachable extends Error {
  constructor(readonly attempts: number) {
    super("The determination service did not answer.");
    this.name = "ApiUnreachable";
  }
}

export interface Health {
  status: "ok";
  env: string;
  rulebase_version: string;
  git_sha: string;
  supabase_configured: boolean;
  anthropic_configured: boolean;
}

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  /** Skip the Authorization header — the public checker is unauthenticated. */
  anonymous?: boolean;
  signal?: AbortSignal;
  /** Called when a retry is pending, so the UI can say "warming" rather than "error". */
  onWarming?: (attempt: number) => void;
}

/** Backoff between cold-start retries, in ms. Totals ~31s, which covers a Render wake. */
const COLD_START_BACKOFF_MS = [1_000, 2_000, 4_000, 8_000, 16_000] as const;

const sleep = (ms: number, signal?: AbortSignal) =>
  new Promise<void>((resolve, reject) => {
    const t = setTimeout(resolve, ms);
    signal?.addEventListener("abort", () => {
      clearTimeout(t);
      reject(new DOMException("Aborted", "AbortError"));
    });
  });

async function problemFrom(res: Response): Promise<Problem> {
  try {
    const body = (await res.json()) as Partial<Problem>;
    if (typeof body.code === "string" && typeof body.title === "string") {
      return { ...body, code: body.code, title: body.title, status: body.status ?? res.status };
    }
  } catch {
    // A non-JSON body means something in front of the API answered — a proxy, or HTML.
  }
  return { code: "http_error", title: res.statusText || "Request failed", status: res.status };
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, anonymous = false, signal, onWarming } = options;

  const headers: Record<string, string> = { accept: "application/json" };
  if (body !== undefined) headers["content-type"] = "application/json";
  if (!anonymous) {
    const token = await accessToken();
    if (token) headers.authorization = `Bearer ${token}`;
  }

  const url = `${env.apiUrl}${path.startsWith("/") ? path : `/${path}`}`;
  const init: RequestInit = {
    method,
    headers,
    signal,
    ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
  };

  for (let attempt = 0; ; attempt++) {
    try {
      const res = await fetch(url, init);

      // 502/503/504 from a sleeping or restarting instance is a wait, not a failure.
      if ((res.status === 502 || res.status === 503 || res.status === 504) && attempt < COLD_START_BACKOFF_MS.length) {
        onWarming?.(attempt + 1);
        await sleep(COLD_START_BACKOFF_MS[attempt], signal);
        continue;
      }
      if (!res.ok) throw new ApiError(await problemFrom(res));
      if (res.status === 204) return undefined as T;
      return (await res.json()) as T;
    } catch (err) {
      if (err instanceof ApiError) throw err;
      if (err instanceof DOMException && err.name === "AbortError") throw err;
      // A network-level failure is the other shape a sleeping backend takes.
      if (attempt < COLD_START_BACKOFF_MS.length) {
        onWarming?.(attempt + 1);
        await sleep(COLD_START_BACKOFF_MS[attempt], signal);
        continue;
      }
      throw new ApiUnreachable(attempt + 1);
    }
  }
}

export const api = {
  health: (opts?: RequestOptions) => request<Health>("/healthz", { anonymous: true, ...opts }),
} as const;
