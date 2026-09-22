"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { apiFetch } from "@/lib/api";
import type { Preferences, Profile } from "@/lib/types";

export default function PreferencesForm({
  initialPreferences,
}: {
  initialPreferences: Preferences;
}) {
  const [titles, setTitles] = useState((initialPreferences.titles ?? []).join(", "));
  const [remoteOnly, setRemoteOnly] = useState(initialPreferences.remote_only ?? false);
  const [salaryMin, setSalaryMin] = useState(initialPreferences.salary_min?.toString() ?? "");
  const [status, setStatus] = useState<"idle" | "saving" | "saved">("idle");

  async function save() {
    setStatus("saving");
    const preferences: Preferences = {
      titles: titles
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean),
      remote_only: remoteOnly,
      ...(salaryMin ? { salary_min: Number(salaryMin) } : {}),
    };

    const supabase = createClient();
    const {
      data: { session },
    } = await supabase.auth.getSession();
    if (!session) return;

    await apiFetch<Profile>("/profile", session.access_token, {
      method: "PATCH",
      body: JSON.stringify({ preferences }),
    });
    setStatus("saved");
    setTimeout(() => setStatus("idle"), 1500);
  }

  return (
    <div className="flex max-w-md flex-col gap-3 rounded-lg border border-stone-200 bg-white p-4">
      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium text-stone-700">Target titles</span>
        <input
          value={titles}
          onChange={(e) => setTitles(e.target.value)}
          placeholder="backend engineer, platform engineer"
          className="rounded-md border border-stone-300 px-3 py-2 text-sm"
        />
        <span className="text-xs text-stone-400">Comma-separated, matched against job titles.</span>
      </label>

      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={remoteOnly}
          onChange={(e) => setRemoteOnly(e.target.checked)}
          className="rounded border-stone-300"
        />
        <span className="font-medium text-stone-700">Remote only</span>
      </label>

      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium text-stone-700">Minimum salary</span>
        <input
          type="number"
          value={salaryMin}
          onChange={(e) => setSalaryMin(e.target.value)}
          placeholder="150000"
          className="rounded-md border border-stone-300 px-3 py-2 text-sm"
        />
      </label>

      <button
        onClick={save}
        disabled={status === "saving"}
        className="mt-1 self-start rounded-full bg-stone-900 px-4 py-2 text-xs font-medium text-white hover:bg-stone-700 disabled:opacity-60"
      >
        {status === "saving" ? "Saving…" : status === "saved" ? "Saved" : "Save preferences"}
      </button>
    </div>
  );
}
