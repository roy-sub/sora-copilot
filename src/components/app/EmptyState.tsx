import { MediaSlot } from "@/components/MediaSlot";

export function EmptyState({ slot, note, title, body, action }: { slot: string; note: string; title: string; body: string; action?: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-4 items-start max-w-[44ch]">
      <div className="w-[180px]"><MediaSlot slot={slot} kind="illustration" ratio="1/1" size="480×480" note={note} /></div>
      <h3 className="m-0 t-h3 text-ink-hi">{title}</h3>
      <p className="m-0 t-body-sm text-ink-mid pretty">{body}</p>
      {action}
    </div>
  );
}
