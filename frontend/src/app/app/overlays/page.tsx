"use client";

/**
 * Toasts, modals and confirmation dialogs, firing for real.
 *
 * The destructive dialog is the one worth having here: it requires the record's name to
 * be typed before it will delete, because a determination and its dossiers are the
 * record of what was submitted to an authority.
 */

import { useState } from "react";
import { PageHeader } from "@/components/app/Shell";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Field";
import { Modal } from "@/components/ui/Dialog";
import { useToast } from "@/components/Toast";
import { useOperations, useRulebase } from "@/lib/hooks";

export default function Overlays() {
  const { push } = useToast();
  const { data: rulebase } = useRulebase();
  const { data: operations = [] } = useOperations();
  const [rulebaseModal, setRulebaseModal] = useState(false);
  const [deleteModal, setDeleteModal] = useState(false);
  const [typed, setTyped] = useState("");

  const sample = operations[0];
  const target = sample?.name ?? "Powerline corridor — Mur valley";
  const matches = typed.trim() === target;

  return (
    <>
      <PageHeader title="Overlays" />
      <main className="flex-1 flex flex-col gap-sheet min-w-0">
        <div className="bg-sheet px-4 md:px-6 py-5">
          <p className="m-0 max-w-[68ch] t-body-sm text-ink-mid pretty">
            Every overlay the product uses, firing for real rather than mocked. A toast
            auto-dismisses after six seconds, pauses on hover or focus, and never
            auto-dismisses a failure.
          </p>
        </div>

        <section className="bg-sheet p-4 md:p-6 flex flex-col gap-4">
          <h3 className="m-0 t-h3 text-ink-hi">Toasts</h3>
          <div className="flex gap-2.5 flex-wrap">
            <Button onClick={() => push({ tone: "ok", text: "Dossier v4 generated", action: { label: "Download" } })}>
              Success, with an action
            </Button>
            <Button
              variant="secondary"
              onClick={() => push({ tone: "warn", text: "OSO #08 still has no evidence" })}
            >
              Warning
            </Button>
            <Button
              variant="secondary"
              onClick={() =>
                push({ tone: "fail", text: "The run stopped at the airspace assessment · ref ENG-5081" })
              }
            >
              Failure, which does not auto-dismiss
            </Button>
          </div>
        </section>

        <section className="bg-sheet p-4 md:p-6 flex flex-col gap-4">
          <h3 className="m-0 t-h3 text-ink-hi">Rulebase change</h3>
          <p className="m-0 max-w-[68ch] t-body-sm text-ink-mid pretty">
            Changing the pinned rulebase affects every future determination, so the modal
            lists what is already determined before it asks.
          </p>
          <Button variant="secondary" onClick={() => setRulebaseModal(true)}>
            Open the rulebase modal
          </Button>
        </section>

        <section className="bg-sheet p-4 md:p-6 flex flex-col gap-4">
          <h3 className="m-0 t-h3 text-ink-hi">Destructive confirmation</h3>
          <p className="m-0 max-w-[68ch] t-body-sm text-ink-mid pretty">
            Deleting an operation deletes its determination and every dossier generated
            from it — the record of what was submitted. The confirm stays disabled until
            the name is typed exactly.
          </p>
          <Button
            variant="destructive"
            onClick={() => {
              setTyped("");
              setDeleteModal(true);
            }}
          >
            Delete this operation
          </Button>
        </section>
      </main>

      <Modal
        open={rulebaseModal}
        onOpenChange={setRulebaseModal}
        title="Change the pinned rulebase?"
        description="This affects every future determination, not the ones already computed."
      >
        <div className="flex flex-col gap-4">
          <p className="m-0 t-body-sm text-ink-mid pretty">
            Determinations already computed keep the rulebase they were computed against.
            {rulebase ? ` The current rulebase is ${rulebase.version}.` : ""}
          </p>
          <Button onClick={() => setRulebaseModal(false)}>Understood</Button>
        </div>
      </Modal>

      <Modal
        open={deleteModal}
        onOpenChange={setDeleteModal}
        destructive
        title="Delete this operation and everything generated from it?"
        description="This cannot be undone."
      >
        <div className="flex flex-col gap-4">
          <p className="m-0 t-body-sm text-ink-mid pretty">
            The determination and every dossier version are deleted with it. Type{" "}
            <strong className="text-ink-hi">{target}</strong> to confirm.
          </p>
          <Input
            value={typed}
            onChange={(e) => setTyped(e.target.value)}
            placeholder={target}
            aria-label="Type the operation name to confirm"
          />
          <div className="flex gap-2.5 flex-wrap">
            <Button
              variant="destructive"
              disabled={!matches}
              onClick={() => {
                setDeleteModal(false);
                push({ tone: "warn", text: "Nothing was deleted — this page is a demonstration." });
              }}
            >
              Delete
            </Button>
            <Button variant="secondary" onClick={() => setDeleteModal(false)}>
              Cancel
            </Button>
          </div>
        </div>
      </Modal>
    </>
  );
}
