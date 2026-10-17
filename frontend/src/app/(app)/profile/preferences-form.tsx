"use client";
import { useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { apiFetch } from "@/lib/api";
import type { Preferences, Profile } from "@/lib/types";
import { Icon } from "@/components/ui";

export default function PreferencesForm({
  initialPreferences,
}: {
  initialPreferences: Preferences;
}) {
  const [titles, setTitles] = useState(
    (initialPreferences.titles ?? []).join(", "),
  );
  const [remoteOnly, setRemoteOnly] = useState(
    initialPreferences.remote_only ?? false,
  );
  const [salaryMin, setSalaryMin] = useState(
    initialPreferences.salary_min?.toString() ?? "",
  );
  const [status, setStatus] = useState<"idle" | "saving" | "saved">("idle");
  const [error, setError] = useState("");

  async function save(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setStatus("saving");
    setError("");
    try {
      const preferences: Preferences = {
        titles: titles
          .split(",")
          .map((t) => t.trim())
          .filter(Boolean),
        remote_only: remoteOnly,
        ...(salaryMin ? { salary_min: Number(salaryMin) } : {}),
      };
      const {
        data: { session },
      } = await createClient().auth.getSession();
      if (!session) throw new Error("Please sign in again.");
      await apiFetch<Profile>("/profile", session.access_token, {
        method: "PATCH",
        body: JSON.stringify({ preferences }),
      });
      setStatus("saved");
    } catch {
      setError("Your preferences couldn’t be saved. Please try again.");
      setStatus("idle");
    }
  }
  return (
    <form className="form-stack" onSubmit={save}>
      <label className="field">
        <span className="field-label">Target roles</span>
        <input
          className="input"
          value={titles}
          onChange={(e) => {
            setTitles(e.target.value);
            setStatus("idle");
          }}
          placeholder="Software engineer, product engineer"
        />
        <span className="field-hint">
          Separate titles with commas to match a wider range of roles.
        </span>
      </label>
      <label className="field">
        <span className="field-label">Minimum annual salary</span>
        <input
          className="input"
          type="number"
          min="0"
          step="1000"
          value={salaryMin}
          onChange={(e) => {
            setSalaryMin(e.target.value);
            setStatus("idle");
          }}
          placeholder="e.g. 120000"
        />
        <span className="field-hint">
          USD · Leave blank to explore all salary ranges.
        </span>
      </label>
      <label className="check-label check-block">
        <input
          type="checkbox"
          checked={remoteOnly}
          onChange={(e) => {
            setRemoteOnly(e.target.checked);
            setStatus("idle");
          }}
        />
        <span>Prioritize remote opportunities</span>
      </label>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      <div>
        <button
          className="button button-primary"
          disabled={status === "saving"}
          type="submit"
        >
          {status === "saving"
            ? "Saving…"
            : status === "saved"
              ? "Preferences saved"
              : "Save preferences"}
          <Icon name={status === "saved" ? "check" : "arrow"} size={15} />
        </button>
      </div>
    </form>
  );
}
