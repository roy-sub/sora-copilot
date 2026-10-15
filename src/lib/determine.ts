import { determine } from "@/engine/engine";
import type { Determination } from "@/engine/types";
import type { Operation } from "@/data/fixtures";

const cache = new WeakMap<object, Determination>();

/** Memoised per input object. Drafts have not reached the engine. */
export function determinationOf(op: Operation): Determination | null {
  if (op.status === "draft") return null;
  let d = cache.get(op.input);
  if (!d) { d = determine(op.input); cache.set(op.input, d); }
  return d;
}

export const sailOf = (d: Determination | null) => (d && d.outcome.kind === "sail" ? d.outcome.sail : null);
