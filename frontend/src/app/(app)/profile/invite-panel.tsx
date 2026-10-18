"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { apiFetch } from "@/lib/api";
import { Icon } from "@/components/ui";
import type { Invite } from "@/lib/types";

/** A live invite is one that hasn't been revoked — accepted or waiting.
 * It is what counts against the allowance, and revoking frees the slot. */
const isLive = (invite: Invite) => !invite.revoked_at;

export default function InvitePanel({
  initialInvites,
  inviteLimit,
  unlimited,
}: {
  initialInvites: Invite[];
  inviteLimit: number;
  unlimited: boolean;
}) {
  // Withdrawn invites are history, and history belongs in the admin
  // panel: here they would only pad the list with addresses that no
  // longer mean anything, and their slots are already back in the count.
  const [invites, setInvites] = useState(() => initialInvites.filter(isLive));
  const [email, setEmail] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [revoking, setRevoking] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [sent, setSent] = useState("");

  const used = invites.filter(isLive).length;
  const remaining = Math.max(inviteLimit - used, 0);
  const canInvite = unlimited || remaining > 0;

  async function token() {
    const {
      data: { session },
    } = await createClient().auth.getSession();
    if (!session) throw new Error("signed out");
    return session.access_token;
  }

  async function invite(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setSent("");
    try {
      const created = await apiFetch<Invite>("/invites", await token(), {
        method: "POST",
        body: JSON.stringify({ email: email.trim(), note: note.trim() || null }),
      });
      setInvites((prev) => [created, ...prev]);
      setSent(created.email);
      setEmail("");
      setNote("");
    } catch (caught) {
      // apiFetch puts the API's own message in the Error, and these are
      // worth showing verbatim: "you've used all of your invites" and
      // "that address already has access" are different problems with
      // different fixes, and a generic failure message hides which.
      setError(detail(caught, "We couldn’t send that invite. Please try again."));
    } finally {
      setBusy(false);
    }
  }

  async function revoke(id: string) {
    setRevoking(id);
    setError("");
    setSent("");
    try {
      await apiFetch(`/invites/${id}`, await token(), { method: "DELETE" });
      setInvites((prev) => prev.filter((i) => i.id !== id));
    } catch (caught) {
      setError(detail(caught, "We couldn’t withdraw that invite. Please try again."));
    } finally {
      setRevoking(null);
    }
  }

  return (
    <>
      <div className="invite-allowance" aria-live="polite">
        <span className="icon-tile">
          <Icon name="mail" size={17} />
        </span>
        <div>
          <strong>
            {unlimited
              ? "Unlimited invites"
              : `${remaining} of ${inviteLimit} invite${inviteLimit === 1 ? "" : "s"} left`}
          </strong>
          <p>
            {unlimited
              ? "As an administrator you can invite without a limit."
              : "Withdrawing an invite that hasn’t been used gives the slot back."}
          </p>
        </div>
      </div>

      <form className="token-create invite-form" onSubmit={invite}>
        <label className="field">
          <span className="field-label">Email address</span>
          <input
            className="input"
            required
            type="email"
            autoComplete="off"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="someone@example.com"
            disabled={!canInvite}
          />
        </label>
        <label className="field">
          <span className="field-label">Note (optional)</span>
          <input
            className="input"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Former colleague"
            disabled={!canInvite}
          />
        </label>
        <button
          className="button button-primary"
          type="submit"
          disabled={busy || !canInvite || !email.trim()}
        >
          <Icon name="mail" size={15} />
          {busy ? "Inviting…" : "Send invite"}
        </button>
      </form>

      {!canInvite && (
        <p className="form-status" role="status" style={{ marginTop: 16 }}>
          You’ve used all of your invites. Withdraw one that hasn’t been used, or
          ask an administrator for more.
        </p>
      )}
      {error && (
        <p className="form-error" role="alert" style={{ marginTop: 16 }}>
          {error}
        </p>
      )}
      {sent && (
        <div className="token-reveal" role="status">
          <h3>{sent} can now join Athena.</h3>
          <p>
            Nothing was emailed. Send them the sign-in link yourself — they’ll
            need to use this exact address.
          </p>
        </div>
      )}

      <div className="token-list">
        {!invites.length && (
          <div className="answer-empty">
            <Icon name="mail" size={26} />
            <h3>You haven’t invited anyone yet.</h3>
            <p>Athena is invite-only. Your invites are how someone gets in.</p>
          </div>
        )}
        {invites.map((i) => (
          <div key={i.id} className="token-row">
            <span className="icon-tile">
              <Icon name={i.accepted_at ? "check" : "mail"} size={17} />
            </span>
            <div className="token-details">
              <strong>{i.email}</strong>
              <p>
                {i.accepted_at
                  ? `Joined ${day(i.accepted_at)}`
                  : `Invited ${day(i.created_at)} · Waiting to join`}
                {i.note ? ` · ${i.note}` : ""}
              </p>
            </div>
            {i.accepted_at ? (
              <span className="pill">Member</span>
            ) : (
              <button
                className="button button-quiet"
                disabled={revoking === i.id}
                onClick={() => revoke(i.id)}
              >
                {revoking === i.id ? "Withdrawing…" : "Withdraw"}
              </button>
            )}
          </div>
        ))}
      </div>
    </>
  );
}

/** apiFetch throws `METHOD /path failed (409): {"detail":"…"}`. Pull the
 * detail back out so the person sees the reason, not the transport. */
function detail(caught: unknown, fallback: string) {
  const message = caught instanceof Error ? caught.message : "";
  const body = message.slice(message.indexOf("): ") + 3);
  try {
    const parsed = JSON.parse(body);
    if (typeof parsed.detail === "string") return parsed.detail;
    if (Array.isArray(parsed.detail)) return "Enter a valid email address.";
  } catch {
    // Not a JSON error body — a network failure, or the API being down.
  }
  return fallback;
}

const day = (iso: string) => new Date(iso).toISOString().slice(0, 10);
