import Link from "next/link";
import { forwardRef } from "react";
import { cn } from "@/lib/cn";

type Variant = "primary" | "secondary" | "ghost" | "destructive";
type Shape = "sm" | "pill";
type Size = "md" | "lg";

const base = "inline-flex items-center justify-center gap-2 border t-micro whitespace-nowrap tr-ui press select-none disabled:opacity-35 disabled:cursor-not-allowed no-underline";
const variants: Record<Variant, string> = {
  primary: "bg-accent text-accent-ink border-transparent hover:bg-accent-press hover:text-accent-ink",
  secondary: "bg-transparent text-ink-hi border-hairline-strong hover:bg-sheet-raised hover:text-ink-hi",
  ghost: "bg-transparent text-ink-mid border-hairline hover:text-ink-hi hover:border-hairline-strong",
  destructive: "bg-sail-6 text-white border-transparent",
};
const sizes: Record<Size, string> = { md: "min-h-11 px-5", lg: "min-h-12 px-6" };

export interface ButtonStyleProps { variant?: Variant; shape?: Shape; size?: Size; className?: string }

export const buttonClass = ({ variant = "primary", shape = "sm", size = "md", className }: ButtonStyleProps) =>
  cn(base, variants[variant], sizes[size], shape === "pill" ? "rounded-pill" : "rounded-sm", className);

export const Button = forwardRef<HTMLButtonElement, React.ButtonHTMLAttributes<HTMLButtonElement> & ButtonStyleProps>(
  function Button({ variant, shape, size, className, type = "button", ...rest }, ref) {
    return <button ref={ref} type={type} className={buttonClass({ variant, shape, size, className })} {...rest} />;
  },
);

export function ButtonLink({ variant, shape, size, className, ...rest }: ButtonStyleProps & Omit<React.ComponentProps<typeof Link>, "className">) {
  return <Link className={buttonClass({ variant, shape, size, className })} {...rest} />;
}
