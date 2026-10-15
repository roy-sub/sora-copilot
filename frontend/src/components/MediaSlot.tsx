"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/cn";
import { mediaEntry, type MediaId } from "@/lib/media-manifest";
import { usePrefs } from "@/lib/prefs";

export interface MediaSlotProps {
  /** A key from the media manifest. Everything else is read from there. */
  id: MediaId;
  /** Below the fold by default; set false for the hero so it is not lazy. */
  lazy?: boolean;
  className?: string;
}

const CORNERS = ["top-3 left-3", "top-3 right-3", "bottom-3 left-3", "bottom-3 right-3"];

/** Reduced motion gets the poster, not the loop. */
function usePrefersReducedMotion(): boolean {
  const [reduce, setReduce] = useState(false);
  useEffect(() => {
    const q = matchMedia("(prefers-reduced-motion: reduce)");
    setReduce(q.matches);
    const onChange = () => setReduce(q.matches);
    q.addEventListener("change", onChange);
    return () => q.removeEventListener("change", onChange);
  }, []);
  return reduce;
}

/**
 * Reserves the exact aspect ratio from the manifest, so the real asset lands with zero
 * layout shift, and renders the designed placeholder until it does.
 *
 * Asset presence is probed rather than configured, and the probe defaults to *absent*:
 * the placeholder is what shows until the file has actually loaded, rather than until
 * it has failed. That ordering matters — a `<video>` whose source 404s does not reliably
 * fire `error` in every browser, and the earlier version of this component left a black
 * rectangle where the design calls for a labelled slot. Drop the file into
 * `public/media/` with the manifest filename and it appears, with no code change.
 */
export function MediaSlot({ id, lazy = true, className }: MediaSlotProps) {
  const { slots } = usePrefs();
  const reduce = usePrefersReducedMotion();
  const entry = mediaEntry(id);
  const [failed, setFailed] = useState(false);
  const [loaded, setLoaded] = useState(false);

  const ratio = `${entry.w} / ${entry.h}`;
  const size = `${entry.w}×${entry.h}`;
  // A video under reduced motion shows its poster, which is an image.
  const asImage = entry.kind !== "video" || reduce;
  const src = asImage && entry.kind === "video" ? entry.poster : entry.src;

  return (
    <div
      className={cn(
        "relative w-full bg-sheet-well rounded-md overflow-hidden flex items-center justify-center",
        className,
      )}
      style={{ aspectRatio: ratio }}
      data-slot={id}
    >
      {!failed && src ? (
        asImage ? (
          // next/image is unavailable under static export with images.unoptimized.
          // eslint-disable-next-line @next/next/no-img-element
          <img
            className={cn(
              "absolute inset-0 size-full object-cover tr-ui",
              loaded ? "opacity-100" : "opacity-0",
            )}
            style={{ filter: "saturate(.95) contrast(1.02)" }}
            src={src}
            alt={entry.alt}
            width={entry.w}
            height={entry.h}
            loading={lazy ? "lazy" : "eager"}
            decoding="async"
            onLoad={() => setLoaded(true)}
            onError={() => setFailed(true)}
          />
        ) : (
          <video
            className={cn(
              "absolute inset-0 size-full object-cover tr-ui",
              loaded ? "opacity-100" : "opacity-0",
            )}
            src={entry.src}
            poster={entry.poster}
            muted
            autoPlay
            loop
            playsInline
            // `none` would never load, so `onLoadedData` would never fire and the slot
            // would sit on its placeholder for ever. Metadata is enough to know the
            // file is really there.
            preload={lazy ? "metadata" : "auto"}
            aria-label={entry.alt}
            onLoadedData={() => setLoaded(true)}
            onError={() => setFailed(true)}
          />
        )
      ) : null}

      {/* Underneath the asset, and visible until it has loaded. */}
      {!loaded && (
        <>
          <div
            aria-hidden
            className="absolute inset-0 opacity-50"
            style={{
              backgroundImage:
                "linear-gradient(var(--hairline) 1px,transparent 1px),linear-gradient(90deg,var(--hairline) 1px,transparent 1px)",
              backgroundSize: "48px 48px",
            }}
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
              <span className="t-micro text-ink-mid">
                {entry.kind} · {size}
              </span>
            </div>
            <p className="m-0 t-body-sm text-ink-low pretty">{entry.note}</p>
            {slots && (
              <code className="t-data-sm text-[11px] leading-none tracking-[.06em] text-accent-ink bg-accent px-[7px] py-1 rounded-sm">
                {id}
                {entry.maxBytes ? ` · ≤${(entry.maxBytes / 1_000_000).toFixed(1)} MB` : ""}
              </code>
            )}
          </div>
        </>
      )}
    </div>
  );
}
