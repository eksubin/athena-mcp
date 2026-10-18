"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { apiFetch } from "@/lib/api";
import { Icon } from "@/components/ui";
import Avatar from "@/components/avatar";
import type { AccountRole, AdminAccount, AdminInvite } from "@/lib/types";

type Tab = "accounts" | "invites";

export default function AdminConsole({
  initialAccounts,
  initialInvites,
  currentUserId,
}: {
  initialAccounts: AdminAccount[];
  initialInvites: AdminInvite[];
  currentUserId: string;
}) {
  const [tab, setTab] = useState<Tab>("accounts");
  const [accounts, setAccounts] = useState(initialAccounts);
  const [invites, setInvites] = useState(initialInvites);
  const [query, setQuery] = useState("");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<AccountRole>("member");
  const [note, setNote] = useState("");

  const search = query.trim().toLowerCase();
  const matchingAccounts = accounts.filter(
    (a) =>
      !search ||
      [a.email, a.username, a.real_name, a.role]
        .join(" ")
        .toLowerCase()
        .includes(search),
  );
  const matchingInvites = invites.filter(
    (i) =>
      !search ||
      [i.email, i.invited_by_username, i.note, i.role]
        .join(" ")
        .toLowerCase()
        .includes(search),
  );

  async function token() {
    const {
      data: { session },
    } = await createClient().auth.getSession();
    if (!session) throw new Error("signed out");
    return session.access_token;
  }

  async function act<T>(id: string, run: (jwt: string) => Promise<T>) {
    setBusyId(id);
    setError("");
    setStatus("");
    try {
      return await run(await token());
    } catch (caught) {
      setError(detail(caught, "That change didn’t go through. Please try again."));
      return null;
    } finally {
      setBusyId(null);
    }
  }

  async function patchAccount(
    account: AdminAccount,
    changes: { role?: AccountRole; disabled?: boolean; invite_limit?: number },
    description: string,
  ) {
    const updated = await act(account.id, (jwt) =>
      apiFetch<AdminAccount>(`/admin/users/${account.id}`, jwt, {
        method: "PATCH",
        body: JSON.stringify(changes),
      }),
    );
    if (!updated) return;
    setAccounts((prev) => prev.map((a) => (a.id === updated.id ? updated : a)));
    setStatus(`${updated.email} — ${description}`);
  }

  async function revokeInvite(invite: AdminInvite) {
    const updated = await act(invite.id, (jwt) =>
      apiFetch<AdminInvite>(`/admin/invites/${invite.id}`, jwt, {
        method: "DELETE",
      }),
    );
    if (!updated) return;
    setInvites((prev) => prev.map((i) => (i.id === updated.id ? updated : i)));
    if (updated.accepted_user_id) {
      // Revoking a used invite suspends the account it admitted, so the
      // accounts list is now stale.
      setAccounts((prev) =>
        prev.map((a) =>
          a.id === updated.accepted_user_id
            ? { ...a, disabled_at: new Date().toISOString() }
            : a,
        ),
      );
      setStatus(`${updated.email} — invite withdrawn and access suspended`);
    } else {
      setStatus(`${updated.email} — invite withdrawn`);
    }
  }

  async function sendInvite(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const created = await act("new-invite", (jwt) =>
      apiFetch<AdminInvite>("/admin/invites", jwt, {
        method: "POST",
        body: JSON.stringify({
          email: email.trim(),
          role,
          note: note.trim() || null,
        }),
      }),
    );
    if (!created) return;
    setInvites((prev) => [created, ...prev]);
    setStatus(
      `${created.email} can now create an account${created.role === "admin" ? " as an administrator" : ""}.`,
    );
    setEmail("");
    setNote("");
    setRole("member");
  }

  return (
    <>
      <div className="board-toolbar">
        <div className="segmented" aria-label="Admin view">
          <button
            className={tab === "accounts" ? "selected" : ""}
            aria-pressed={tab === "accounts"}
            onClick={() => setTab("accounts")}
          >
            <Icon name="users" size={14} /> Accounts ({accounts.length})
          </button>
          <button
            className={tab === "invites" ? "selected" : ""}
            aria-pressed={tab === "invites"}
            onClick={() => setTab("invites")}
          >
            <Icon name="mail" size={14} /> Invites ({invites.length})
          </button>
        </div>
        <label className="search-field">
          <Icon name="search" size={16} />
          <input
            type="search"
            aria-label="Search accounts and invites"
            placeholder="Search by email or name…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>
      </div>

      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      {status && (
        <p className="form-status" role="status">
          {status}
        </p>
      )}

      {tab === "accounts" ? (
        <div className="admin-table" role="table" aria-label="Accounts">
          <div className="admin-row admin-head" role="row">
            <span role="columnheader">Account</span>
            <span role="columnheader">Role</span>
            <span role="columnheader">Invites</span>
            <span role="columnheader">Activity</span>
            <span role="columnheader">Access</span>
          </div>
          {matchingAccounts.map((a) => {
            const suspended = Boolean(a.disabled_at);
            const self = a.id === currentUserId;
            return (
              <div className="admin-row" role="row" key={a.id}>
                <div role="cell" className="admin-identity">
                  <Avatar name={a.avatar} size={32} />
                  <div>
                    <strong>{a.email}</strong>
                    <p>
                      {a.username}
                      {a.real_name ? ` · ${a.real_name}` : ""}
                      {self ? " · you" : ""}
                    </p>
                  </div>
                </div>
                <div role="cell">
                  <select
                    className="input input-compact"
                    aria-label={`Role for ${a.email}`}
                    value={a.role}
                    disabled={busyId === a.id || self}
                    onChange={(e) =>
                      patchAccount(
                        a,
                        { role: e.target.value as AccountRole },
                        `role set to ${e.target.value}`,
                      )
                    }
                  >
                    <option value="member">Member</option>
                    <option value="admin">Administrator</option>
                  </select>
                </div>
                <div role="cell">
                  {a.role === "admin" ? (
                    <span className="pill">No limit</span>
                  ) : (
                    <label className="invite-limit-field">
                      <input
                        className="input input-compact"
                        type="number"
                        min={0}
                        max={1000}
                        aria-label={`Invite allowance for ${a.email}`}
                        defaultValue={a.invite_limit}
                        disabled={busyId === a.id}
                        onBlur={(e) => {
                          const next = Number(e.target.value);
                          if (
                            !Number.isInteger(next) ||
                            next < 0 ||
                            next === a.invite_limit
                          )
                            return;
                          patchAccount(
                            a,
                            { invite_limit: next },
                            `invite allowance set to ${next}`,
                          );
                        }}
                      />
                      <span>{a.invites_used} used</span>
                    </label>
                  )}
                </div>
                <div role="cell">
                  <p>
                    {a.application_count} application
                    {a.application_count === 1 ? "" : "s"}
                  </p>
                  <p>
                    {a.last_sign_in_at
                      ? `Last seen ${day(a.last_sign_in_at)}`
                      : "Never signed in"}
                  </p>
                </div>
                <div role="cell">
                  <span className={`status-dot ${suspended ? "rejected" : "offer"}`} />
                  <button
                    className="button button-quiet"
                    disabled={busyId === a.id || self}
                    title={
                      self ? "Ask another administrator to change your own access" : undefined
                    }
                    onClick={() =>
                      patchAccount(
                        a,
                        { disabled: !suspended },
                        suspended ? "access restored" : "access withdrawn",
                      )
                    }
                  >
                    {busyId === a.id
                      ? "Saving…"
                      : suspended
                        ? "Restore"
                        : "Withdraw"}
                  </button>
                </div>
              </div>
            );
          })}
          {!matchingAccounts.length && (
            <div className="column-empty">No accounts match “{query}”.</div>
          )}
        </div>
      ) : (
        <>
          <form className="token-create admin-invite-form" onSubmit={sendInvite}>
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
              />
            </label>
            <label className="field">
              <span className="field-label">Joins as</span>
              <select
                className="input"
                value={role}
                onChange={(e) => setRole(e.target.value as AccountRole)}
              >
                <option value="member">Member</option>
                <option value="admin">Administrator</option>
              </select>
            </label>
            <label className="field">
              <span className="field-label">Note (optional)</span>
              <input
                className="input"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Why they’re joining"
              />
            </label>
            <button
              className="button button-primary"
              type="submit"
              disabled={busyId === "new-invite" || !email.trim()}
            >
              <Icon name="mail" size={15} />
              {busyId === "new-invite" ? "Inviting…" : "Invite"}
            </button>
          </form>
          <div className="admin-table" role="table" aria-label="Invites">
            <div className="admin-row admin-head invite-row" role="row">
              <span role="columnheader">Address</span>
              <span role="columnheader">Invited by</span>
              <span role="columnheader">State</span>
              <span role="columnheader" />
            </div>
            {matchingInvites.map((i) => (
              <div className="admin-row invite-row" role="row" key={i.id}>
                <div role="cell">
                  <strong>{i.email}</strong>
                  <p>
                    {i.role === "admin" ? "Administrator invite" : "Member invite"}
                    {i.note ? ` · ${i.note}` : ""}
                  </p>
                </div>
                <div role="cell">
                  <p>{i.invited_by_username ?? "Athena"}</p>
                  <p>{day(i.created_at)}</p>
                </div>
                <div role="cell">
                  <span className={`pill ${inviteState(i).tone}`}>
                    {inviteState(i).label}
                  </span>
                </div>
                <div role="cell">
                  {i.revoked_at ? (
                    <span className="pill">Withdrawn {day(i.revoked_at)}</span>
                  ) : (
                    <button
                      className="button button-quiet"
                      disabled={busyId === i.id}
                      onClick={() => revokeInvite(i)}
                      title={
                        i.accepted_user_id
                          ? "Withdraws the invite and suspends the account it admitted"
                          : "Withdraws the invite before it is used"
                      }
                    >
                      {busyId === i.id ? "Withdrawing…" : "Withdraw"}
                    </button>
                  )}
                </div>
              </div>
            ))}
            {!matchingInvites.length && (
              <div className="column-empty">No invites match “{query}”.</div>
            )}
          </div>
        </>
      )}
    </>
  );
}

function inviteState(invite: AdminInvite) {
  if (invite.revoked_at) return { label: "Withdrawn", tone: "pill-quiet" };
  if (invite.accepted_at) return { label: "Joined", tone: "pill-good" };
  return { label: "Waiting", tone: "pill-warn" };
}

/** apiFetch throws `METHOD /path failed (409): {"detail":"…"}`; the API's
 * own refusals explain themselves better than a generic message can. */
function detail(caught: unknown, fallback: string) {
  const message = caught instanceof Error ? caught.message : "";
  const body = message.slice(message.indexOf("): ") + 3);
  try {
    const parsed = JSON.parse(body);
    if (typeof parsed.detail === "string") return parsed.detail;
    if (Array.isArray(parsed.detail)) return "Check the values and try again.";
  } catch {
    // Not a JSON error body — a network failure, or the API being down.
  }
  return fallback;
}

const day = (iso: string) => new Date(iso).toISOString().slice(0, 10);
