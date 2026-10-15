"use client";

import { useState } from "react";
import { FAQ } from "@/data/marketing";

export function Faq() {
  const [open, setOpen] = useState(0);
  return (
    <div className="flex flex-col border-t border-hairline">
      {FAQ.map(([q, a], i) => {
        const on = open === i;
        return (
          <div key={q} className="border-b border-hairline">
            <h3 className="m-0">
              <button
                type="button"
                aria-expanded={on}
                aria-controls={`faq-${i}`}
                onClick={() => setOpen(on ? -1 : i)}
                className="w-full bg-transparent border-0 flex items-center justify-between gap-6 py-5 min-h-11 text-left t-h3 text-ink-hi hover:text-accent tr-ui"
              >
                <span>{q}</span>
                <span aria-hidden className="flex-none size-7 border border-hairline-strong rounded-pill flex items-center justify-center text-base text-ink-mid">{on ? "–" : "+"}</span>
              </button>
            </h3>
            <div id={`faq-${i}`} role="region" className="grid transition-[grid-template-rows,opacity] duration-[240ms] ease-(--ease-ui)" style={{ gridTemplateRows: on ? "1fr" : "0fr", opacity: on ? 1 : 0 }}>
              <p className="m-0 overflow-hidden t-body text-ink-mid md:pr-20" style={{ paddingBottom: on ? 24 : 0 }}>{a}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
