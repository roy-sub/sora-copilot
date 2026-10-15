"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ORG } from "@/data/fixtures";
import { RULEBASE } from "@/engine/rulebase";
import { Wordmark } from "@/components/Brand";
import { ButtonLink } from "@/components/ui/Button";
import { cn } from "@/lib/cn";
import { useWorkspace } from "@/lib/workspace";

export const NAV = [
  { href: "/app/", label: "Operations", short: "Ops", d: "M3 4h14M3 9h14M3 14h9", match: (p: string) => p === "/app" },
  { href: "/app/fleet/", label: "Drone fleet", short: "Fleet", d: "M4 10h12M10 4v12", match: (p: string) => p.startsWith("/app/fleet") },
  { href: "/app/new/", label: "New operation", short: "New", d: "M10 3v14M3 10h14", match: (p: string) => p.startsWith("/app/new") },
  { href: "/app/operations/powerline-mur/", label: "Determinations", short: "Verdict", d: "M3 15l4-6 3 4 3-7 4 9", match: (p: string) => p.startsWith("/app/operations") && !p.endsWith("/dossier") },
  { href: "/app/dossiers/", label: "Dossiers", short: "Dossiers", d: "M5 3h7l3 3v11H5z", match: (p: string) => p.startsWith("/app/dossiers") || p.endsWith("/dossier") },
  { href: "/app/settings/", label: "Settings", short: "Settings", d: "M10 7a3 3 0 100 6 3 3 0 000-6z", match: (p: string) => p.startsWith("/app/settings") },
];

/** Pathname without a trailing slash (static export uses trailingSlash). */
const usePath = () => (usePathname() || "/").replace(/(.)\/$/, "$1");

const Icon = ({ d }: { d: string }) => (
  <svg width="18" height="18" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden className="flex-none"><path d={d} /></svg>
);

function Rail() {
  const path = usePath();
  const { rulebasePin } = useWorkspace();
  return (
    <aside className="hidden md:flex sticky top-0 h-screen flex-none flex-col justify-between bg-sheet w-16 rail:w-60 py-5 px-2 rail:px-3">
      <div className="flex flex-col gap-6">
        <div className="px-1.5 hidden rail:block"><Wordmark size={17} href="/app/" /></div>
        <Link href="/app/" aria-label="SORA Copilot" className="rail:hidden mx-auto block size-3 bg-accent" style={{ clipPath: "polygon(50% 0,100% 50%,50% 100%,0 50%)" }} />
        <ButtonLink href="/app/new/" className="w-full px-0 rail:px-5" aria-label="New operation">
          <span className="hidden rail:inline">New operation</span><span className="rail:hidden text-base leading-none" aria-hidden>+</span>
        </ButtonLink>
        <nav aria-label="Product" className="flex flex-col gap-sheet">
          {NAV.map((n) => {
            const on = n.match(path);
            return (
              <Link
                key={n.href}
                href={n.href}
                aria-current={on ? "page" : undefined}
                title={n.label}
                className={cn(
                  "no-underline flex items-center gap-2.5 w-full min-h-11 px-3.5 justify-center rail:justify-start whitespace-nowrap text-[13px] font-medium leading-none rounded-sm tr-ui",
                  on ? "bg-sheet-raised text-ink-hi shadow-[inset_2px_0_0_var(--accent)]" : "text-ink-mid hover:text-ink-hi",
                )}
              >
                <Icon d={n.d} />
                <span className="hidden rail:inline">{n.label}</span>
              </Link>
            );
          })}
        </nav>
      </div>
      <div className="hidden rail:flex flex-col gap-3 px-1.5">
        <div className="flex flex-col gap-1 p-3 bg-sheet-well rounded-sm">
          <span className="t-micro text-ink-low">Rulebase</span>
          <span className="t-data-13 leading-[1.3] text-ink-hi">{RULEBASE.version} · {RULEBASE.date}</span>
          <span className="text-[11px] leading-[1.3] text-ink-low">{rulebasePin === "pinned" ? "Pinned by organisation" : "Following latest"}</span>
        </div>
        <div className="flex items-center gap-2.5 min-h-11">
          <div className="size-7 rounded-pill bg-sheet-alt flex items-center justify-center t-micro-10 tracking-normal text-[11px] text-ink-hi">{ORG.user.initials}</div>
          <div className="flex flex-col min-w-0">
            <span className="text-[13px] font-medium leading-[1.2] text-ink-hi truncate">{ORG.user.name}</span>
            <span className="text-[11px] leading-[1.2] text-ink-low">{ORG.short}</span>
          </div>
        </div>
      </div>
    </aside>
  );
}

function TabBar() {
  const path = usePath();
  const items = NAV.filter((n) => n.href !== "/app/fleet/");
  return (
    <nav aria-label="Product" className="md:hidden fixed bottom-0 inset-x-0 z-50 bg-sheet grid grid-cols-5 gap-sheet pt-sheet border-t-2 border-ground pb-[env(safe-area-inset-bottom)]">
      {items.map((n) => {
        const on = n.match(path);
        return (
          <Link key={n.href} href={n.href} aria-label={n.label} aria-current={on ? "page" : undefined}
            className={cn("no-underline flex flex-col items-center justify-center gap-1 min-h-14 tr-ui", on ? "text-ink-hi bg-sheet-raised shadow-[inset_0_2px_0_var(--accent)]" : "text-ink-mid")}>
            <Icon d={n.d} />
            <span className="text-[10px] font-semibold leading-none tracking-[.04em]">{n.short}</span>
          </Link>
        );
      })}
    </nav>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen bg-ground gap-sheet">
      <Rail />
      <div className="flex-1 min-w-0 flex flex-col gap-sheet pb-16 md:pb-0">{children}</div>
      <TabBar />
    </div>
  );
}

export function PageHeader({ title, children }: { title: string; children?: React.ReactNode }) {
  return (
    <header className="bg-sheet px-4 md:px-6 min-h-16 flex items-center justify-between gap-4 flex-wrap">
      <h1 className="m-0 py-3.5 t-h2 leading-[1.25] text-ink-hi pretty">{title}</h1>
      <div className="flex items-center gap-2.5">
        {children}
        <button type="button" aria-label="Search" className="size-11 bg-transparent border border-hairline rounded-sm text-ink-mid hover:text-ink-hi hover:border-hairline-strong flex items-center justify-center tr-ui">
          <svg width="16" height="16" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden><circle cx="9" cy="9" r="5.5" /><path d="M13 13l4 4" /></svg>
        </button>
        <button type="button" aria-label="Notifications" className="size-11 bg-transparent border border-hairline rounded-sm text-ink-mid hover:text-ink-hi hover:border-hairline-strong flex items-center justify-center tr-ui">
          <svg width="16" height="16" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden><path d="M6 8a4 4 0 118 0v4l1.5 2h-11L6 12z" /></svg>
        </button>
      </div>
    </header>
  );
}
