import { TIERS } from "@/data/marketing";
import { ButtonLink } from "@/components/ui/Button";
import { cn } from "@/lib/cn";

export function Tiers({ tall }: { tall?: boolean }) {
  return (
    <div className="grid gap-sheet bg-hairline border border-hairline grid-cols-[repeat(auto-fit,minmax(220px,1fr))]">
      {TIERS.map((t) => (
        <div key={t.name} className={cn("bg-sheet-well p-6 flex flex-col gap-4", tall ? "min-h-[360px]" : "min-h-[300px]")}>
          <span className="t-micro text-ink-low">{t.name}</span>
          <div>
            <div className={cn("font-bold tnum text-ink-hi leading-none tracking-[-.02em]", tall ? "text-[36px]" : "text-[32px]")}>{t.price}</div>
            <div className="mt-1.5 t-cap leading-[1.4] text-ink-low">{t.unit}</div>
          </div>
          <ul className="m-0 p-0 list-none flex flex-col gap-2 flex-1">
            {t.feats.map((f) => (
              <li key={f} className="flex gap-2 t-body-sm leading-[1.45] text-ink-mid"><span aria-hidden className="text-ink-low flex-none">—</span><span>{f}</span></li>
            ))}
          </ul>
          <ButtonLink href={t.href} variant="secondary" shape="pill">{t.cta}</ButtonLink>
        </div>
      ))}
    </div>
  );
}
