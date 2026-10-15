import Link from "next/link";
import { cn } from "@/lib/cn";
import { RULEBASE } from "@/engine/rulebase";

export const DISCLAIMER = "SORA Copilot prepares and verifies your risk assessment. Your national aviation authority grants the authorisation.";
export const STAMP = `Rulebase ${RULEBASE.version} · ${RULEBASE.date}`;

export function Wordmark({ size = 20, href = "/", ink = "text-ink-hi", className }: { size?: number; href?: string | null; ink?: string; className?: string }) {
  const body = (
    <span className={cn("flex items-center gap-2.5", className)}>
      <span aria-hidden className="bg-accent flex-none" style={{ width: size * 0.7, height: size * 0.7, clipPath: "polygon(50% 0,100% 50%,50% 100%,0 50%)" }} />
      <span className={cn("font-display font-light whitespace-nowrap", ink)} style={{ fontSize: size, letterSpacing: "-.03em" }}>SORA Copilot</span>
    </span>
  );
  return href ? <Link href={href} className="no-underline" aria-label="SORA Copilot home">{body}</Link> : body;
}

export function RulebaseStamp({ authoritative, className, suffix }: { authoritative?: boolean; className?: string; suffix?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-2.5 t-data-sm text-ink-low", authoritative && "text-ink-mid", className)}>
      {authoritative && <span aria-hidden className="size-[7px] bg-accent flex-none" />}
      {STAMP}{suffix}
    </span>
  );
}

/** Never dismissible. `inline` on verdict/dossier, `footer` on the black ground. */
export function Disclaimer({ variant = "inline", className }: { variant?: "inline" | "footer"; className?: string }) {
  return (
    <div className={cn("flex gap-3 items-start", variant === "footer" && "gap-4 max-w-[72ch]", className)}>
      <div aria-hidden className={cn("self-stretch flex-none", variant === "footer" ? "w-1 bg-accent" : "w-[3px] bg-hairline-strong")} />
      <p className={cn("m-0 t-body-sm pretty", variant === "footer" ? "leading-[1.6] text-paper/70" : "leading-[1.55] text-ink-mid")}>{DISCLAIMER}</p>
    </div>
  );
}

export function CitationChip({ reference, size = "sm" }: { reference: string; size?: "sm" | "md" }) {
  return (
    <span className={cn("inline-flex items-center px-2 border border-accent-line rounded-pill text-ink-hi font-medium leading-[1.2]", size === "sm" ? "min-h-[22px] text-[10px]" : "min-h-6 px-2.5 text-[10px]")}>
      {reference}
    </span>
  );
}

export function RobustnessPill({ level }: { level: string }) {
  const l = level.toLowerCase();
  return (
    <span className={cn("inline-flex items-center min-h-6 px-2.5 rounded-pill t-micro-10 border border-hairline-strong text-ink-mid flex-none", l === "high" && "bg-sheet-alt")}>
      {l === "nr" ? "NOT REQ." : l}
    </span>
  );
}

export const STATUS_GLYPH = { draft: "□", determined: "■", "dossier ready": "◆", submitted: "◧", authorised: "▣" } as const;
const STATUS_INK = { draft: "text-ink-low", determined: "text-ink-hi", "dossier ready": "text-ink-hi", submitted: "text-ink-mid", authorised: "text-ink-hi" } as const;

/** Deliberately not on the risk ramp: one ink level, five glyph shapes. */
export function StatusPill({ status }: { status: keyof typeof STATUS_GLYPH }) {
  return (
    <span className={cn("inline-flex items-center gap-[7px] t-data-sm leading-none", STATUS_INK[status])}>
      <span aria-hidden>{STATUS_GLYPH[status]}</span>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}

export const EVIDENCE_TONE = {
  evidenced: { glyph: "▣", label: "Evidenced", ink: "text-ink-hi" },
  partial: { glyph: "◧", label: "Partial", ink: "text-sail-3" },
  gap: { glyph: "□", label: "Gap", ink: "text-sail-6" },
  na: { glyph: "⊘", label: "Not applicable", ink: "text-ink-low" },
} as const;
export type EvidenceState = keyof typeof EVIDENCE_TONE;

export function EvidenceMark({ state, className }: { state: EvidenceState; className?: string }) {
  const t = EVIDENCE_TONE[state];
  return (
    <span className={cn("inline-flex items-center gap-1.5 t-data-sm leading-none", t.ink, className)}>
      <span aria-hidden>{t.glyph}</span>{t.label}
    </span>
  );
}

export function Micro({ children, className, as: As = "span" }: { children: React.ReactNode; className?: string; as?: "span" | "div" | "h2" | "h3" }) {
  return <As className={cn("t-micro text-ink-low", className)}>{children}</As>;
}
