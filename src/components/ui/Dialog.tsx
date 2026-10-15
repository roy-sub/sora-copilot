"use client";

import * as D from "@radix-ui/react-dialog";
import { cn } from "@/lib/cn";

/** Modal / AlertDialog: --sheet-raised on --scrim, --shadow-overlay, --radius-md. */
export function Modal({ open, onOpenChange, title, children, destructive, className, description }: {
  open: boolean; onOpenChange: (o: boolean) => void; title: string; description?: string;
  children: React.ReactNode; destructive?: boolean; className?: string;
}) {
  return (
    <D.Root open={open} onOpenChange={onOpenChange}>
      <D.Portal>
        <D.Overlay className="fixed inset-0 z-[80] bg-scrim data-[state=open]:animate-[stage-tick_160ms_var(--ease-ui)_both]" />
        <D.Content
          role={destructive ? "alertdialog" : "dialog"}
          className={cn(
            "fixed z-[81] left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[min(520px,calc(100vw-32px))] bg-sheet-raised shadow-overlay rounded-md p-6 flex flex-col gap-4 focus:outline-none",
            destructive && "border-t-[3px] border-sail-6",
            "data-[state=open]:animate-[node-settle_240ms_var(--ease-ui)_both]",
            className,
          )}
        >
          <D.Title className="m-0 t-h3 text-ink-hi">{title}</D.Title>
          {description && <D.Description className="m-0 t-body-sm text-ink-mid pretty">{description}</D.Description>}
          {children}
        </D.Content>
      </D.Portal>
    </D.Root>
  );
}

/** Right drawer: 480px desktop, full-height sheet on mobile, 2px ground edge. */
export function Drawer({ open, onOpenChange, label, children }: {
  open: boolean; onOpenChange: (o: boolean) => void; label: string; children: React.ReactNode;
}) {
  return (
    <D.Root open={open} onOpenChange={onOpenChange}>
      <D.Portal>
        <D.Overlay className="fixed inset-0 z-[80] bg-scrim data-[state=open]:animate-[stage-tick_160ms_var(--ease-ui)_both]" />
        <D.Content
          aria-describedby={undefined}
          className="fixed z-[81] right-0 top-0 bottom-0 w-full md:w-[480px] bg-sheet-raised shadow-overlay border-l-2 border-ground p-6 flex flex-col gap-5 overflow-y-auto focus:outline-none data-[state=open]:animate-[drawer-in_240ms_var(--ease-ui)_both]"
        >
          <D.Title className="sr-only">{label}</D.Title>
          {children}
        </D.Content>
      </D.Portal>
    </D.Root>
  );
}

export const DialogClose = D.Close;
