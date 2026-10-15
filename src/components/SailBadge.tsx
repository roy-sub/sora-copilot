"use client";

import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/cn";
import { roman } from "@/engine/engine";

type Size = "sm" | "md" | "lg";
const DIM = { sm: 40, md: 64, lg: 132 } as const;
const NUM = { sm: 14, md: 24, lg: 56 } as const;
const PAD = { sm: 4, md: 8, lg: 16 } as const;

/**
 * The identity object. Three redundant encodings, always on: the Roman numeral,
 * a six-segment bar with `level` filled, and plate geometry — I–II square,
 * III–IV one notched corner, V–VI notched plus a 2px inset band.
 */
export function SailBadge({ level, size = "md", className }: { level: number; size?: Size; className?: string }) {
  const lvl = Math.min(6, Math.max(1, Math.round(level)));
  const lg = size === "lg";
  const dim = DIM[size];
  return (
    <div
      role="img"
      aria-label={`SAIL ${roman(lvl)} of VI`}
      className={cn("inline-flex flex-none flex-col items-center justify-center box-border", className)}
      style={{
        width: dim, height: dim, padding: PAD[size], gap: lg ? 12 : 5,
        background: `var(--sail-${lvl})`, color: `var(--sail-${lvl}-ink)`,
        clipPath: lvl >= 3 ? "polygon(0 0,100% 0,100% calc(100% - 14px),calc(100% - 14px) 100%,0 100%)" : "none",
        outline: lvl >= 5 ? `2px solid var(--sail-${lvl}-ink)` : "0",
        outlineOffset: lg ? -7 : -4,
      }}
    >
      <span className="tnum" style={{ font: `600 ${NUM[size]}px/1 var(--font-heading)`, letterSpacing: ".02em" }}>{roman(lvl)}</span>
      <div className="flex" style={{ gap: lg ? 4 : 2, width: lg ? 84 : dim - PAD[size] * 2 - 4 }}>
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <i key={i} className="block flex-1" style={{ height: lg ? 6 : 3, background: "currentColor", opacity: i <= lvl ? 1 : 0.22 }} />
        ))}
      </div>
      {size !== "sm" && <span style={{ font: `600 ${lg ? 12 : 9}px/1 var(--font-heading)`, letterSpacing: ".14em" }}>SAIL</span>}
    </div>
  );
}

/** Plate for a determination without a SAIL: never run, or certified category. */
export function SailPlaceholder({ size = "md", label }: { size?: Size; label: string }) {
  const dim = DIM[size];
  return (
    <div role="img" aria-label={label} className="inline-flex flex-none items-center justify-center border border-dashed border-hairline-strong text-ink-low" style={{ width: dim, height: dim }}>
      <span style={{ font: `600 ${size === "lg" ? 13 : 10}px/1.1 var(--font-heading)`, letterSpacing: ".1em" }} className="text-center px-1">{size === "sm" ? "—" : label}</span>
    </div>
  );
}

/**
 * sail-step (motion.md): when the target changes, the badge walks one plate at a
 * time, 180ms per level, so fill, segments and geometry change together.
 */
export function useSteppedLevel(target: number, stepMs = 180, from?: number) {
  const [shown, setShown] = useState(from ?? target);
  const t = useRef<ReturnType<typeof setTimeout>>(undefined);
  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) { setShown(target); return; }
    const tick = () => setShown((s) => {
      if (s === target) return s;
      const n = s + (target > s ? 1 : -1);
      if (n !== target) t.current = setTimeout(tick, stepMs);
      return n;
    });
    t.current = setTimeout(tick, stepMs);
    return () => clearTimeout(t.current);
  }, [target, stepMs]);
  return shown;
}

export function SailScale() {
  return (
    <div className="flex items-center gap-3 flex-wrap">
      <span className="t-micro text-ink-low">SAIL scale</span>
      <div className="flex gap-sheet">
        {[1, 2, 3, 4, 5, 6].map((l) => (
          <span key={l} className="flex items-center justify-center w-[30px] h-5 t-micro-10 tracking-normal" style={{ background: `var(--sail-${l})`, color: `var(--sail-${l}-ink)` }}>
            {roman(l)}
          </span>
        ))}
      </div>
    </div>
  );
}
