"use client";

import { usePrefs } from "@/lib/prefs";
import { cn } from "@/lib/cn";

export interface MediaSlotProps {
  slot: string;
  kind: "image" | "video" | "illustration";
  /** CSS aspect-ratio, e.g. "16/9" */
  ratio: string;
  /** Intrinsic asset size, e.g. "1440×810" */
  size: string;
  note: string;
  /** When the real asset lands: set src (and poster for video). */
  src?: string;
  poster?: string;
  alt?: string;
  className?: string;
}

const CORNERS = ["top-3 left-3", "top-3 right-3", "bottom-3 left-3", "bottom-3 right-3"];

/** Reserves the exact aspect ratio so the real asset lands with zero layout shift. */
export function MediaSlot({ slot, kind, ratio, size, note, src, poster, alt = "", className }: MediaSlotProps) {
  const { slots } = usePrefs();
  return (
    <div className={cn("relative w-full bg-sheet-well rounded-md overflow-hidden flex items-center justify-center", className)} style={{ aspectRatio: ratio }} data-slot={slot}>
      {src ? (
        kind === "video" ? (
          <video className="absolute inset-0 size-full object-cover" src={src} poster={poster} muted autoPlay loop playsInline preload="none" />
        ) : (
          // eslint-disable-next-line @next/next/no-img-element
          <img className="absolute inset-0 size-full object-cover" style={{ filter: "saturate(.95) contrast(1.02)" }} src={src} alt={alt} />
        )
      ) : (
        <>
          <div
            aria-hidden
            className="absolute inset-0 opacity-50"
            style={{ backgroundImage: "linear-gradient(var(--hairline) 1px,transparent 1px),linear-gradient(90deg,var(--hairline) 1px,transparent 1px)", backgroundSize: "48px 48px" }}
          />
          {CORNERS.map((c) => (
            <span key={c} aria-hidden>
              <span className={cn("absolute w-[18px] h-[2px] bg-ink-low", c)} />
              <span className={cn("absolute w-[2px] h-[18px] bg-ink-low", c)} />
            </span>
          ))}
          <div className="relative flex flex-col items-center gap-2.5 p-6 text-center max-w-[380px]">
            <div className="flex items-center gap-2">
              <div className="size-[7px] bg-accent" />
              <span className="t-micro text-ink-mid">{kind} · {size}</span>
            </div>
            <p className="m-0 t-body-sm text-ink-low pretty">{note}</p>
            {slots && <code className="t-data-sm text-[11px] leading-none tracking-[.06em] text-accent-ink bg-accent px-[7px] py-1 rounded-sm">{slot}</code>}
          </div>
        </>
      )}
    </div>
  );
}
