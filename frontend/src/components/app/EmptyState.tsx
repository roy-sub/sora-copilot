import { MediaSlot } from "@/components/MediaSlot";
import type { MediaId } from "@/lib/media-manifest";

/** Body copy always says what the next concrete step produces, never "get started". */
export function EmptyState({
  slot,
  title,
  body,
  action,
  secondaryAction,
}: {
  slot: MediaId;
  title: string;
  body: string;
  action?: React.ReactNode;
  secondaryAction?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-4 items-start max-w-[44ch]">
      <div className="w-[180px]">
        <MediaSlot id={slot} />
      </div>
      <h3 className="m-0 t-h3 text-ink-hi">{title}</h3>
      <p className="m-0 t-body-sm text-ink-mid pretty">{body}</p>
      {(action || secondaryAction) && (
        <div className="flex gap-2.5 flex-wrap">
          {action}
          {secondaryAction}
        </div>
      )}
    </div>
  );
}
