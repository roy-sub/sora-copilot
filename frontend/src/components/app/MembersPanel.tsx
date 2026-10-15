"use client";

/**
 * Who is in the organisation, who has been invited, and how many seats are left.
 *
 * The thing worth explaining in the interface is that there is no emailed invitation
 * link: an invitation is claimed on first sign-in by the address in the verified
 * Supabase token. So the panel says what the owner actually has to do — tell their
 * colleague to sign up with the address that was invited — instead of implying that a
 * message has gone out.
 */

import { useState } from "react";
import { ApiError } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { FieldLabel, Input, Select } from "@/components/ui/Field";
import { useToast } from "@/components/Toast";
import { PlanLimit, isPlanLimit } from "@/components/PlanLimit";
import { useAuth } from "@/lib/auth";
import {
  useInvite,
  useRemoveMember,
  useRevokeInvite,
  useSeats,
  useSetMemberRole,
} from "@/lib/hooks";
import type { Invite, InviteRole, Member, MemberRole } from "@/lib/api-client";
import { cn } from "@/lib/cn";

const ROLE_NOTE: Record<MemberRole, string> = {
  owner: "Billing, members, everything",
  admin: "Billing and members",
  member: "Determinations and dossiers",
};

export function MembersPanel() {
  const { push } = useToast();
  const { signOut } = useAuth();
  const { data, isLoading } = useSeats();
  const invite = useInvite();
  const revoke = useRevokeInvite();
  const remove = useRemoveMember();
  const setRole = useSetMemberRole();

  const [email, setEmail] = useState("");
  const [role, setRole_] = useState<InviteRole>("member");
  const [limit, setLimit] = useState<ApiError | null>(null);

  const fail = (e: unknown, fallback: string) =>
    push({
      tone: "fail",
      text: e instanceof ApiError ? (e.problem.detail ?? e.problem.title) : fallback,
    });

  if (isLoading || !data) {
    return (
      <section className="bg-sheet-well p-5 flex flex-col gap-3.5" aria-busy>
        <span className="t-micro text-ink-low">Members</span>
        {[1, 0.6, 0.35].map((o, i) => (
          <div key={i} className="h-12 bg-sheet-alt" style={{ opacity: o }} />
        ))}
      </section>
    );
  }

  const pending = data.invites.filter((i) => i.status === "pending");
  const spent = data.invites.filter((i) => i.status !== "pending");

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const address = email.trim();
    if (!address) return;
    setLimit(null);
    invite.mutate(
      { email: address, role },
      {
        onSuccess: () => {
          setEmail("");
          push({ tone: "ok", text: `${address} can now join by signing up with that address` });
        },
        onError: (e) => {
          if (isPlanLimit(e)) {
            setLimit(e);
            return;
          }
          fail(e, "Could not send the invitation");
        },
      },
    );
  };

  return (
    <section className="bg-sheet-well p-5 flex flex-col gap-4">
      <div className="flex items-baseline justify-between gap-3 flex-wrap">
        <span className="t-micro text-ink-low">Members</span>
        <span className="t-data-sm text-ink-low tnum">
          {data.seats_committed} of {data.seats_limit}{" "}
          {data.seats_limit === 1 ? "seat" : "seats"}
          {pending.length > 0 ? ` · ${pending.length} invited` : ""}
        </span>
      </div>

      <div className="flex flex-col gap-sheet bg-hairline border border-hairline">
        {data.members.map((m) => (
          <MemberRow
            key={m.user_id}
            member={m}
            canManage={data.seats_limit > 1 || data.members.length > 1}
            onRole={(next) =>
              setRole.mutate(
                { userId: m.user_id, role: next },
                { onError: (e) => fail(e, "Could not change the role") },
              )
            }
            onRemove={() =>
              remove.mutate(m.user_id, {
                onSuccess: () => push({ tone: "ok", text: "Removed from the organisation" }),
                onError: (e) => fail(e, "Could not remove them"),
              })
            }
          />
        ))}
        {pending.map((i) => (
          <InviteRow
            key={i.id}
            invite={i}
            onRevoke={() =>
              revoke.mutate(i.id, {
                onSuccess: () => push({ tone: "ok", text: "Invitation withdrawn" }),
                onError: (e) => fail(e, "Could not withdraw it"),
              })
            }
          />
        ))}
      </div>

      {limit && <PlanLimit error={limit} compact />}

      {data.can_invite || data.seats_limit > 1 ? (
        <form className="flex flex-col gap-3" onSubmit={submit}>
          <FieldLabel label="Invite a colleague" quiet>
            <div className="flex gap-2.5 flex-wrap">
              <Input
                type="email"
                className="flex-1 min-w-[180px]"
                placeholder="name@operator.at"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
              <Select
                value={role}
                onChange={(e) => setRole_(e.target.value as InviteRole)}
                aria-label="Role"
                className="w-[130px]"
              >
                <option value="member">Member</option>
                <option value="admin">Admin</option>
              </Select>
              <Button type="submit" disabled={invite.isPending || !email.trim()}>
                {invite.isPending ? "Inviting" : "Invite"}
              </Button>
            </div>
          </FieldLabel>
          <p className="m-0 t-cap text-ink-low pretty">
            No email is sent. Tell them to sign up with exactly this address — the
            invitation is claimed from their verified sign-in, so there is no link to
            forward or leak. It lapses after 14 days.
          </p>
        </form>
      ) : (
        <p className="m-0 t-cap text-ink-mid pretty">
          This plan has one seat. Team adds five, and an invited colleague joins by
          signing up with the address you invite — no link to forward.
        </p>
      )}

      {spent.length > 0 && (
        <details className="t-cap text-ink-low">
          <summary className="cursor-pointer min-h-11 flex items-center">
            {spent.length} past invitation{spent.length === 1 ? "" : "s"}
          </summary>
          <ul className="m-0 mt-2 p-0 list-none flex flex-col gap-1">
            {spent.map((i) => (
              <li key={i.id} className="flex gap-2 justify-between">
                <span className="truncate">{i.email}</span>
                <span className="flex-none">{i.status}</span>
              </li>
            ))}
          </ul>
        </details>
      )}

      <Button variant="secondary" onClick={() => void signOut()}>
        Sign out
      </Button>
    </section>
  );
}

function MemberRow({
  member,
  canManage,
  onRole,
  onRemove,
}: {
  member: Member;
  canManage: boolean;
  onRole: (role: MemberRole) => void;
  onRemove: () => void;
}) {
  return (
    <div className="bg-sheet-well px-3.5 py-3 flex items-center gap-3 gap-y-2 flex-wrap min-w-0">
      <div className="size-8 rounded-pill bg-sheet-alt grid place-items-center t-micro-10 text-ink-hi flex-none">
        {(member.email ?? "?").slice(0, 2).toUpperCase()}
      </div>
      <div className="flex-1 basis-[150px] min-w-0">
        <span className="block t-data-13 text-ink-hi truncate">
          {member.email ?? "—"}
          {member.is_you && <span className="text-ink-low"> · you</span>}
        </span>
        <span className="block t-cap text-ink-low truncate">{ROLE_NOTE[member.role]}</span>
      </div>
      {/* The controls wrap as one unit: splitting them crushes the address instead. */}
      {canManage && !member.is_you ? (
        <div className="flex items-center gap-2 ml-auto flex-none">
          <Select
            value={member.role}
            onChange={(e) => onRole(e.target.value as MemberRole)}
            aria-label={`Role for ${member.email ?? "member"}`}
            className="w-[116px]"
          >
            <option value="member">Member</option>
            <option value="admin">Admin</option>
            <option value="owner">Owner</option>
          </Select>
          <button
            type="button"
            onClick={onRemove}
            className="min-h-11 px-2 bg-transparent border-0 t-micro-10 text-ink-mid hover:text-sail-6 tr-ui"
          >
            Remove
          </button>
        </div>
      ) : (
        <span className="t-micro-10 text-ink-low ml-auto flex-none">{member.role}</span>
      )}
    </div>
  );
}

function InviteRow({ invite, onRevoke }: { invite: Invite; onRevoke: () => void }) {
  return (
    <div className="bg-sheet-well px-3.5 py-3 flex items-center gap-3 gap-y-2 flex-wrap min-w-0">
      <div
        className={cn(
          "size-8 rounded-pill grid place-items-center t-micro-10 flex-none",
          "border border-dashed border-hairline-strong text-ink-low",
        )}
        aria-hidden
      >
        ···
      </div>
      <div className="flex-1 basis-[150px] min-w-0">
        <span className="block t-data-13 text-ink-mid truncate">{invite.email}</span>
        <span className="block t-cap text-ink-low truncate">
          Invited as {invite.role} · not joined yet
        </span>
      </div>
      <div className="flex items-center gap-2 ml-auto flex-none">
        <span className="t-micro-10 text-sail-3">invited</span>
        <button
          type="button"
          onClick={onRevoke}
          className="min-h-11 px-2 bg-transparent border-0 t-micro-10 text-ink-mid hover:text-ink-hi tr-ui"
        >
          Withdraw
        </button>
      </div>
    </div>
  );
}
