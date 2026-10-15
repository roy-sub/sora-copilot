"use client";

/**
 * Multipart upload and authenticated download.
 *
 * Separate from `api.ts` because both need to bypass its JSON assumptions: an upload is
 * `multipart/form-data`, and a download has to become a file the browser saves rather
 * than a parsed body. An `<a download>` cannot carry an Authorization header, so a
 * download is fetched here and handed to the browser as a blob.
 */

import { ApiError, ApiUnreachable, type Problem } from "@/lib/api";
import type { Evidence } from "@/lib/api-client";
import { env } from "@/lib/env";
import { accessToken } from "@/lib/supabase";

async function problemFrom(res: Response): Promise<Problem> {
  try {
    const body = (await res.json()) as Partial<Problem>;
    if (typeof body.code === "string" && typeof body.title === "string") {
      return { ...body, code: body.code, title: body.title, status: body.status ?? res.status };
    }
  } catch {
    // Not JSON; fall through to the status line.
  }
  return { code: "http_error", title: res.statusText || "Request failed", status: res.status };
}

export async function uploadEvidence(
  operationId: string,
  file: File,
  osoId?: string,
): Promise<Evidence> {
  const form = new FormData();
  form.append("file", file);
  if (osoId) form.append("oso_id", osoId);

  const token = await accessToken();
  let res: Response;
  try {
    res = await fetch(`${env.apiUrl}/api/v1/operations/${operationId}/evidence`, {
      method: "POST",
      // No content-type: the browser sets it with the multipart boundary.
      headers: token ? { authorization: `Bearer ${token}` } : {},
      body: form,
    });
  } catch {
    throw new ApiUnreachable(1);
  }
  if (!res.ok) throw new ApiError(await problemFrom(res));
  return (await res.json()) as Evidence;
}

/**
 * Fetch a protected file and hand it to the browser to save.
 *
 * Returns the filename used, so the caller can report what happened rather than
 * guessing. A 307 to a signed URL is followed by fetch automatically.
 */
export async function downloadFile(path: string, fallbackName: string): Promise<string> {
  const token = await accessToken();
  const res = await fetch(`${env.apiUrl}${path}`, {
    headers: token ? { authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new ApiError(await problemFrom(res));

  const disposition = res.headers.get("content-disposition") ?? "";
  const match = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(disposition);
  const name = match ? decodeURIComponent(match[1]) : fallbackName;

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  try {
    const a = document.createElement("a");
    a.href = url;
    a.download = name;
    a.rel = "noopener";
    document.body.appendChild(a);
    a.click();
    a.remove();
  } finally {
    // Revoking immediately can cancel the download in some browsers.
    setTimeout(() => URL.revokeObjectURL(url), 10_000);
  }
  return name;
}

/** A JSON file built in the browser, for the trace export. */
export function downloadJson(name: string, value: unknown): void {
  const blob = new Blob([JSON.stringify(value, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
}

/** Markdown built in the browser, for "copy trace" as a file. */
export function downloadText(name: string, text: string, type = "text/markdown"): void {
  const blob = new Blob([text], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
}
