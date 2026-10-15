"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { cn } from "@/lib/cn";

type Tone = "ok" | "warn" | "fail";
export interface ToastInput { tone: Tone; text: string; action?: { label: string; onClick?: () => void } }
interface ToastItem extends ToastInput { id: number }

const Ctx = createContext<{ push: (t: ToastInput) => void }>({ push: () => {} });
export const useToast = () => useContext(Ctx);

const BAND: Record<Tone, string> = { ok: "border-l-accent", warn: "border-l-sail-3", fail: "border-l-sail-6" };

function ToastRow({ t, onClose }: { t: ToastItem; onClose: () => void }) {
  const [paused, setPaused] = useState(false);
  const reduce = useReducedMotion();
  // Auto-dismiss 6s, paused on hover or focus, never for failures.
  useEffect(() => {
    if (t.tone === "fail" || paused) return;
    const h = setTimeout(onClose, 6000);
    return () => clearTimeout(h);
  }, [t.tone, paused, onClose]);
  return (
    <motion.div
      layout={!reduce}
      initial={reduce ? false : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0, transition: { duration: 0.24, ease: [0.22, 0.61, 0.36, 1] } }}
      exit={{ opacity: 0, y: 8, transition: { duration: 0.16, ease: [0.4, 0, 1, 1] } }}
      role={t.tone === "fail" ? "alert" : "status"}
      onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(false)}
      onFocus={() => setPaused(true)} onBlur={() => setPaused(false)}
      className={cn("pointer-events-auto flex items-center gap-3 bg-sheet-raised border-l-[3px] pl-4 pr-2 py-1 shadow-overlay w-full", BAND[t.tone])}
    >
      <span className="flex-1 t-data-13 text-ink-hi py-2.5">{t.text}</span>
      {t.action && (
        <button type="button" onClick={() => { t.action?.onClick?.(); onClose(); }} className={cn("t-micro-10 min-h-11 px-2 border-0 bg-transparent", t.tone === "ok" ? "text-accent" : "text-ink-mid hover:text-ink-hi")}>
          {t.action.label}
        </button>
      )}
      <button type="button" aria-label="Dismiss" onClick={onClose} className="size-11 border-0 bg-transparent text-ink-low hover:text-ink-hi">✕</button>
    </motion.div>
  );
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const id = useRef(0);
  const push = useCallback((t: ToastInput) => setItems((s) => [...s.slice(-3), { ...t, id: ++id.current }]), []);
  const close = useCallback((i: number) => setItems((s) => s.filter((x) => x.id !== i)), []);
  return (
    <Ctx.Provider value={{ push }}>
      {children}
      <div aria-live="polite" className="fixed z-[100] bottom-20 md:bottom-6 right-4 left-4 md:left-auto md:w-[400px] flex flex-col gap-2 pointer-events-none">
        <AnimatePresence initial={false}>
          {items.map((t) => <ToastRow key={t.id} t={t} onClose={() => close(t.id)} />)}
        </AnimatePresence>
      </div>
    </Ctx.Provider>
  );
}
