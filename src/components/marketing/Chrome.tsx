import Link from "next/link";
import { Disclaimer, STAMP, Wordmark } from "@/components/Brand";
import { ButtonLink } from "@/components/ui/Button";

const NAV = [
  ["How it works", "/#how"],
  ["Pricing", "/pricing"],
  ["Category checker", "/checker"],
  ["Sign in", "/signin"],
] as const;

export function MarketingHeader({ variant = "nav" }: { variant?: "nav" | "cta" | "stamp" | "plain" }) {
  return (
    <header className="bg-sheet flex items-center justify-between gap-6 px-4 md:px-6 min-h-16 flex-wrap">
      <div className="py-3"><Wordmark /></div>
      {variant === "nav" && (
        <nav aria-label="Main" className="flex items-center gap-1 flex-nowrap overflow-x-auto max-w-full no-scrollbar">
          {NAV.map(([label, href]) => (
            <Link key={href} href={href} className="no-underline text-ink-mid hover:text-ink-hi t-micro px-3 min-h-11 flex items-center whitespace-nowrap flex-none">
              {label}
            </Link>
          ))}
          <ButtonLink href="/app/new" shape="pill" className="ml-2 flex-none">Start a SORA</ButtonLink>
        </nav>
      )}
      {variant === "cta" && <ButtonLink href="/app/new" shape="pill">Start a SORA</ButtonLink>}
      {variant === "stamp" && <span className="t-data-sm text-ink-low">{STAMP}</span>}
    </header>
  );
}

export function MarketingFooter({ compact }: { compact?: boolean }) {
  if (compact)
    return (
      <footer className="bg-ground px-4 md:px-12 py-10">
        <Disclaimer variant="footer" />
      </footer>
    );
  const col = (title: string, links: [string, string][]) => (
    <div className="flex flex-col gap-sheet">
      <span className="t-micro text-paper/45 mb-1.5">{title}</span>
      {links.map(([l, h]) => (
        <Link key={l} href={h} className="flex items-center min-h-11 text-paper no-underline text-[13px] hover:text-lime">{l}</Link>
      ))}
    </div>
  );
  return (
    <footer className="bg-ground px-4 md:px-12 py-12 flex flex-col gap-8">
      <div className="grid gap-8 grid-cols-[repeat(auto-fit,minmax(180px,1fr))]">
        <div className="flex flex-col gap-3">
          <Wordmark size={18} ink="text-paper" />
          <span className="t-data-sm text-paper/45">{STAMP}</span>
        </div>
        {col("Product", [["Category checker", "/checker"], ["Pricing", "/pricing"], ["Worked example", "/app/operations/powerline-mur"]])}
        {col("Legal", [["Terms", "/legal#terms"], ["Privacy", "/legal#privacy"], ["Rulebase changelog", "/legal#changelog"]])}
        <div className="flex flex-col gap-sheet">
          <span className="t-micro text-paper/45 mb-1.5">Data region</span>
          <span className="text-paper/70 text-[13px]">EU · Frankfurt</span>
        </div>
      </div>
      <div className="border-t border-paper/20 pt-6">
        <Disclaimer variant="footer" />
      </div>
    </footer>
  );
}
