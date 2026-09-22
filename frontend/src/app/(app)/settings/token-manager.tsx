"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { apiFetch } from "@/lib/api";
import type { AccessToken, AccessTokenCreated } from "@/lib/types";

export default function TokenManager({ initialTokens }: { initialTokens: AccessToken[] }) {
  const [tokens, setTokens] = useState(initialTokens);
  const [label, setLabel] = useState("");
  const [justCreated, setJustCreated] = useState<AccessTokenCreated | null>(null);
  const [busy, setBusy] = useState(false);

  async function getToken() {
    const supabase = createClient();
    const {
      data: { session },
    } = await supabase.auth.getSession();
    return session?.access_token ?? null;
  }

  async function createToken() {
    setBusy(true);
    try {
      const token = await getToken();
      if (!token) return;
      const created = await apiFetch<AccessTokenCreated>("/tokens", token, {
        method: "POST",
        body: JSON.stringify({ label: label.trim() || "MCP token" }),
      });
      setJustCreated(created);
      setTokens((prev) => [
        { id: created.id, label: created.label, created_at: new Date().toISOString(), last_used_at: null },
        ...prev,
      ]);
      setLabel("");
    } finally {
      setBusy(false);
    }
  }

  async function revoke(id: string) {
    const token = await getToken();
    if (!token) return;
    await apiFetch(`/tokens/${id}`, token, { method: "DELETE" });
    setTokens((prev) => prev.filter((t) => t.id !== id));
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex max-w-md items-center gap-2 rounded-lg border border-stone-200 bg-white p-4">
        <input
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          placeholder="Label (e.g. laptop MCP)"
          className="flex-1 rounded-md border border-stone-300 px-3 py-2 text-sm"
        />
        <button
          onClick={createToken}
          disabled={busy}
          className="rounded-full bg-stone-900 px-4 py-2 text-xs font-medium whitespace-nowrap text-white hover:bg-stone-700 disabled:opacity-60"
        >
          {busy ? "Creating…" : "New token"}
        </button>
      </div>

      {justCreated && (
        <div className="max-w-lg rounded-lg border border-emerald-300 bg-emerald-50 p-4 text-sm">
          <p className="font-medium text-emerald-900">
            Copy this now — it won&apos;t be shown again.
          </p>
          <code className="mt-2 block overflow-x-auto rounded bg-white p-2 text-xs text-stone-800">
            {justCreated.token}
          </code>
        </div>
      )}

      <div className="flex flex-col gap-2">
        {tokens.length === 0 && <p className="text-sm text-stone-400">No tokens yet.</p>}
        {tokens.map((t) => (
          <div
            key={t.id}
            className="flex items-center justify-between rounded-md border border-stone-200 bg-white p-3"
          >
            <div>
              <p className="text-sm font-medium text-stone-900">{t.label}</p>
              <p className="text-xs text-stone-400">
                {t.last_used_at ? `last used ${new Date(t.last_used_at).toLocaleString()}` : "never used"}
              </p>
            </div>
            <button
              onClick={() => revoke(t.id)}
              className="text-xs font-medium text-red-600 hover:underline"
            >
              Revoke
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
