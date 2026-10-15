"use client";

/**
 * The risk chain as a horizontal readout: iGRC → GRC → ARC → residual ARC → SAIL.
 *
 * Figures count up **once** per determination, as the design requires — never on a list,
 * never on a re-render. The count is keyed to the determination id, so opening the same
 * verdict twice does not re-animate it.
 */

import { useEffect, useRef, useState } from "react";
import { useReducedMotion } from "framer-motion";
import type { Determination } from "@/lib/api-client";
import { cn } from "@/lib/cn";

export interface Link {
  key: string;
  value: string;
  note: string;
}

export function chainLinks(d: Determination): Link[] {
  return [
    {
      key: "iGRC",
      value: d.igrc === null ? "—" : String(d.igrc),
      note: "Intrinsic ground risk",
    },
    {
      key: "GRC",
      value: d.final_grc === null ? "—" : String(d.final_grc),
      note: "After ground mitigations",
    },
    { key: "ARC", value: d.initial_arc.toUpperCase(), note: "Initial air risk" },
    {
      key: "Residual ARC",
      value: d.residual_arc.toUpperCase(),
      note: d.initial_arc === d.residual_arc ? "No strategic mitigation" : "After strategic mitigation",
    },
    {
      key: "SAIL",
      value: d.sail === "certified_category" ? "—" : d.sail,
      note: d.sail === "certified_category" ? "Certified category" : `TMPR ${d.tmpr}`,
    },
  ];
}

/** Counts an integer up once. A non-numeric value is shown as-is, immediately. */
function useCountUp(target: string, enabled: boolean, ms = 900): string {
  const [shown, setShown] = useState(enabled ? "0" : target);
  const done = useRef(false);

  useEffect(() => {
    const numeric = Number(target);
    if (!enabled || done.current || !Number.isFinite(numeric) || target === "—") {
      setShown(target);
      done.current = true;
      return;
    }
    done.current = true;
    const start = performance.now();
    let frame = 0;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / ms);
      // ease-instrument: a long tail, settling rather than arriving.
      const eased = 1 - Math.pow(1 - t, 3);
      setShown(String(Math.round(numeric * eased)));
      if (t < 1) frame = requestAnimationFrame(tick);
      else setShown(target);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [target, enabled, ms]);

  return shown;
}

function Cell({ link, countUp, recomputing }: { link: Link; countUp: boolean; recomputing: boolean }) {
  const shown = useCountUp(link.value, countUp);
  return (
    <div className="flex-1 min-w-[108px] bg-sheet-well px-3.5 py-3 flex flex-col gap-1.5">
      <span className="t-micro-10 text-ink-low">{link.key}</span>
      <span
        className={cn(
          "text-[28px] font-bold leading-none tnum tr-ui",
          recomputing ? "text-ink-low" : "text-ink-hi",
        )}
      >
        {shown}
      </span>
      <span className="t-cap text-ink-low pretty">{recomputing ? "re-running" : link.note}</span>
    </div>
  );
}

export function RiskChainReadout({
  determination,
  countUp,
  recomputing = false,
}: {
  determination: Determination;
  countUp: boolean;
  recomputing?: boolean;
}) {
  const reduce = useReducedMotion();
  const links = chainLinks(determination);
  return (
    <div className="flex gap-sheet bg-hairline border border-hairline flex-wrap">
      {links.map((l) => (
        <Cell key={l.key} link={l} countUp={countUp && !reduce} recomputing={recomputing} />
      ))}
    </div>
  );
}
