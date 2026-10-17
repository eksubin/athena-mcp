"use client";
import { useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { apiFetch } from "@/lib/api";
import type { AccessToken, AccessTokenCreated } from "@/lib/types";
import { Icon } from "@/components/ui";

export default function TokenManager({
  initialTokens,
}: {
  initialTokens: AccessToken[];
}) {
  const [tokens, setTokens] = useState(initialTokens);
  const [label, setLabel] = useState("");
  const [justCreated, setJustCreated] = useState<AccessTokenCreated | null>(
    null,
  );
  const [busy, setBusy] = useState(false);
  const [revoking, setRevoking] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  async function getToken() {
    const {
      data: { session },
    } = await createClient().auth.getSession();
    if (!session) throw new Error("Please sign in again.");
    return session.access_token;
  }
  async function createToken(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setCopied(false);
    try {
      const created = await apiFetch<AccessTokenCreated>(
        "/tokens",
        await getToken(),
        {
          method: "POST",
          body: JSON.stringify({ label: label.trim() || "My assistant" }),
        },
      );
      setJustCreated(created);
      setTokens((prev) => [
        {
          id: created.id,
          label: created.label,
          created_at: new Date().toISOString(),
          last_used_at: null,
        },
        ...prev,
      ]);
      setLabel("");
    } catch {
      setError("We couldn’t create your token. Please try again.");
    } finally {
      setBusy(false);
    }
  }
  async function revoke(id: string) {
    setRevoking(id);
    setError("");
    try {
      await apiFetch(`/tokens/${id}`, await getToken(), { method: "DELETE" });
      setTokens((prev) => prev.filter((t) => t.id !== id));
      if (justCreated?.id === id) setJustCreated(null);
    } catch {
      setError("We couldn’t revoke this token. Please try again.");
    } finally {
      setRevoking(null);
    }
  }
  async function copyToken() {
    if (!justCreated) return;
    try {
      await navigator.clipboard.writeText(justCreated.token);
      setCopied(true);
    } catch {
      setError(
        "Clipboard access is unavailable. Select and copy the token below.",
      );
    }
  }
  return (
    <>
      <form className="token-create" onSubmit={createToken}>
        <label className="field">
          <span className="field-label">Connection name</span>
          <input
            className="input"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            placeholder="Claude on my laptop"
          />
        </label>
        <button className="button button-primary" type="submit" disabled={busy}>
          <Icon name="key" size={15} />
          {busy ? "Creating…" : "Create token"}
        </button>
      </form>
      {error && (
        <p className="form-error" role="alert" style={{ marginTop: 18 }}>
          {error}
        </p>
      )}
      {justCreated && (
        <div className="token-reveal" role="status">
          <h3>Your connection is ready.</h3>
          <p>Copy your token now. You won’t be able to view it again.</p>
          <code>{justCreated.token}</code>
          <button
            className="text-action"
            onClick={copyToken}
            style={{ marginTop: 12 }}
          >
            <Icon name={copied ? "check" : "key"} size={14} />
            {copied ? "Copied" : "Copy token"}
          </button>
        </div>
      )}
      <div className="token-list">
        {!tokens.length && (
          <div className="answer-empty">
            <Icon name="key" size={26} />
            <h3>No connections yet.</h3>
            <p>Create a token to give your assistant access to Athena.</p>
          </div>
        )}
        {tokens.map((t) => (
          <div key={t.id} className="token-row">
            <span className="icon-tile">
              <Icon name="key" size={17} />
            </span>
            <div className="token-details">
              <strong>{t.label}</strong>
              <p>
                {t.last_used_at
                  ? `Last used ${new Date(t.last_used_at).toISOString().slice(0, 10)}`
                  : "Ready to connect · Not used yet"}
              </p>
            </div>
            <button
              className="button button-quiet"
              disabled={revoking === t.id}
              onClick={() => revoke(t.id)}
            >
              {revoking === t.id ? "Revoking…" : "Revoke"}
            </button>
          </div>
        ))}
      </div>
    </>
  );
}
