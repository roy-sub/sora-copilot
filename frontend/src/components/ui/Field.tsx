import { cn } from "@/lib/cn";

const field = "w-full bg-field border border-field-border rounded-sm text-ink-hi min-h-11 px-3 tr-ui hover:border-field-border-hover placeholder:text-ink-low";

export function FieldLabel({ label, children, quiet, className }: { label: string; children: React.ReactNode; quiet?: boolean; className?: string }) {
  return (
    <label className={cn("flex flex-col gap-2", className)}>
      <span className={quiet ? "t-cap text-ink-mid" : "t-micro text-ink-low"}>{label}</span>
      {children}
    </label>
  );
}

export function Input({ className, ...p }: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input className={cn(field, className)} {...p} />;
}

export function Select({ className, ...p }: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className={cn(field, className)} {...p} />;
}

export function Textarea({ className, ...p }: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={cn(field, "py-3 min-h-24", className)} {...p} />;
}

/** Hairline-gapped segmented control: the selected option takes the accent. */
export function Segmented<T extends string>({
  options, value, onChange, label, size = "md", disabled = [], className,
}: {
  options: { value: T; label: string }[];
  value: T;
  onChange: (v: T) => void;
  label: string;
  size?: "md" | "lg";
  disabled?: T[];
  className?: string;
}) {
  return (
    <div role="radiogroup" aria-label={label} className={cn("flex gap-sheet bg-hairline border border-hairline rounded-sm overflow-hidden", className)}>
      {options.map((o) => {
        const on = o.value === value;
        const off = disabled.includes(o.value);
        return (
          <button
            key={o.value}
            type="button"
            role="radio"
            aria-checked={on}
            disabled={off}
            onClick={() => onChange(o.value)}
            className={cn(
              "flex-1 t-micro tracking-[.08em] tr-ui border-0 disabled:opacity-35 disabled:cursor-not-allowed",
              size === "lg" ? "min-h-12" : "min-h-11",
              on ? "bg-accent text-accent-ink" : "bg-sheet-well text-ink-mid hover:text-ink-hi",
            )}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}

/** Radio row on the well, hairline-gapped list. */
export function RadioRow({ name, checked, onChange, title, body, className }: {
  name: string; checked: boolean; onChange: () => void; title: string; body?: string; className?: string;
}) {
  return (
    <label className={cn("bg-sheet-well hover:bg-sheet-raised tr-ui p-4 flex gap-3 cursor-pointer min-h-11", body ? "items-start" : "items-center", className)}>
      <input type="radio" name={name} checked={checked} onChange={onChange} className={cn("size-[18px] flex-none", body && "mt-[3px]")} />
      <span>
        <span className="block t-data text-[14px] font-semibold leading-[1.3] text-ink-hi">{title}</span>
        {body && <span className="block mt-1 t-cap text-ink-mid">{body}</span>}
      </span>
    </label>
  );
}
