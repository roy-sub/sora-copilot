"use client";

/**
 * One OSO: what it requires, what evidence satisfies it, and what is attached.
 *
 * The plain-language "what it requires" and the evidence checklist are **our wording**,
 * not the regulation's — the normative text is the rulebase, and the drawer says so.
 * Confusing a helpful summary for the clause is how a tool like this gets someone into
 * trouble.
 */

import { useRef, useState } from "react";
import { CitationChip, EvidenceMark, RobustnessPill } from "@/components/Brand";
import { Drawer } from "@/components/ui/Dialog";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/Toast";
import { OSO_TEXT } from "@/data/oso";
import type { Oso } from "@/lib/api-client";
import { api } from "@/lib/api-client";
import { cn } from "@/lib/cn";
import { evidenceStateOf } from "@/components/verdict/GapAnalysis";
import { useDeleteEvidence, useUploadEvidence } from "@/lib/hooks";
import { downloadFile } from "@/lib/upload";

const ACCEPT = ".pdf,.docx,.xlsx,.doc,.xls,.png,.jpg,.jpeg";
const MAX_MB = 40;

const osoNumber = (osoId: string): number => Number(osoId.replace(/\D/g, ""));

export function OsoDrawer({
  operationId,
  oso,
  onClose,
}: {
  operationId: string;
  oso: Oso | null;
  onClose: () => void;
}) {
  const { push } = useToast();
  const upload = useUploadEvidence(operationId);
  const remove = useDeleteEvidence(operationId);
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const copy = oso ? OSO_TEXT[osoNumber(oso.oso_id)] : undefined;
  const files = oso?.evidence ?? [];
  const state = oso ? evidenceStateOf(oso) : "gap";

  const send = (files: FileList | null) => {
    if (!files?.length || !oso) return;
    setError(null);
    for (const file of Array.from(files)) {
      if (file.size > MAX_MB * 1024 * 1024) {
        setError(`${file.name} is larger than ${MAX_MB} MB.`);
        continue;
      }
      upload.mutate(
        { file, osoId: oso.oso_id },
        {
          onSuccess: () => push({ tone: "ok", text: `${file.name} attached to ${oso.oso_id}` }),
          onError: (e) => setError(e instanceof Error ? e.message : `${file.name} was not accepted.`),
        },
      );
    }
  };

  return (
    <Drawer open={Boolean(oso)} onOpenChange={(open) => !open && onClose()} label={oso?.oso_id ?? "OSO"}>
      {oso && (
        <div className="flex flex-col gap-5">
          <div className="flex flex-col gap-2.5">
            <h3 className="m-0 t-h3 text-ink-hi pretty">{oso.title}</h3>
            <div className="flex items-center gap-2.5 flex-wrap">
              <RobustnessPill level={oso.required_robustness} />
              <EvidenceMark state={state} />
            </div>
            <CitationChip
              reference={`${oso.citation.document.replace("JARUS ", "")} · ${oso.citation.section}`}
              size="md"
            />
            {!oso.citation.verified && (
              <span className="t-cap text-sail-3 pretty">
                UNVERIFIED — the OSO matrix has not been checked against the official
                text, so this robustness level must be confirmed before you rely on it.
              </span>
            )}
          </div>

          {copy && (
            <div className="flex flex-col gap-2">
              <span className="t-micro text-ink-low">What it requires</span>
              <p className="m-0 t-body-sm text-ink-mid pretty">{copy.requires}</p>
              <span className="t-cap text-ink-low pretty">
                Our summary, to orient you. The normative wording is the clause cited
                above.
              </span>
            </div>
          )}

          {copy && (
            <div className="flex flex-col gap-2">
              <span className="t-micro text-ink-low">Evidence that typically satisfies it</span>
              <ul className="m-0 p-0 list-none flex flex-col gap-sheet bg-hairline border border-hairline">
                {copy.evidence.map((item) => (
                  <li key={item} className="bg-sheet-well px-3.5 py-3 t-body-sm text-ink-mid pretty">
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="flex flex-col gap-2.5">
            <span className="t-micro text-ink-low">
              Attached evidence · {files.length}
            </span>
            {files.length === 0 && (
              <p className="m-0 t-cap text-ink-low pretty">
                Nothing attached yet. This objective counts as a gap in the dossier until
                something is.
              </p>
            )}
            {files.map((file) => (
              <div
                key={file.id}
                className="flex items-center justify-between gap-3 p-3 bg-sheet-well rounded-sm"
              >
                <span className="min-w-0 flex flex-col gap-0.5">
                  <span className="t-data-13 text-ink-hi truncate">{file.filename}</span>
                  <span className="t-cap text-ink-low tnum">
                    {file.bytes ? `${Math.round(file.bytes / 1024).toLocaleString("en-GB")} kB` : "—"}
                    {" · "}
                    {new Date(file.uploaded_at).toLocaleDateString("en-GB")}
                  </span>
                </span>
                <span className="flex gap-1.5 flex-none">
                  <button
                    type="button"
                    onClick={() =>
                      downloadFile(
                        api.evidenceDownloadPath(operationId, file.id),
                        file.filename,
                      ).catch((e) =>
                        push({
                          tone: "fail",
                          text: e instanceof Error ? e.message : "Download failed",
                        }),
                      )
                    }
                    className="min-h-11 px-2 bg-transparent border-0 t-micro-10 text-ink-mid hover:text-ink-hi tr-ui"
                  >
                    Get
                  </button>
                  <button
                    type="button"
                    onClick={() =>
                      remove.mutate(file.id, {
                        onSuccess: () => push({ tone: "ok", text: `${file.filename} removed` }),
                      })
                    }
                    className="min-h-11 px-2 bg-transparent border-0 t-micro-10 text-ink-low hover:text-sail-6 tr-ui"
                  >
                    Remove
                  </button>
                </span>
              </div>
            ))}
          </div>

          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragging(false);
              send(e.dataTransfer.files);
            }}
            className={cn(
              "p-5 rounded-sm border border-dashed flex flex-col items-center gap-2.5 text-center tr-ui",
              dragging ? "border-accent bg-sheet-well" : "border-hairline-strong",
            )}
          >
            <span className={cn("t-micro-10", dragging ? "text-accent" : "text-ink-low")}>
              {upload.isPending ? "Uploading" : dragging ? "Drop to attach" : "Attach evidence"}
            </span>
            <p className="m-0 t-cap text-ink-mid pretty">
              Drop a file here, or choose one. PDF, DOCX, XLSX or an image, up to {MAX_MB} MB.
            </p>
            <input
              ref={inputRef}
              type="file"
              multiple
              accept={ACCEPT}
              className="sr-only"
              onChange={(e) => send(e.target.files)}
            />
            <Button variant="secondary" onClick={() => inputRef.current?.click()} disabled={upload.isPending}>
              Choose a file
            </Button>
            {error && (
              <p className="m-0 t-cap text-ink-mid">
                <span className="text-sail-6" aria-hidden>
                  □{" "}
                </span>
                {error}
              </p>
            )}
          </div>

          <p className="m-0 t-cap text-ink-low pretty">
            Attaching a file marks the objective <strong className="text-ink-hi">documented</strong>,
            not verified. SORA Copilot does not review your evidence, and it will not
            claim to have.
          </p>
        </div>
      )}
    </Drawer>
  );
}
