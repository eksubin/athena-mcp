"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { apiFetch } from "@/lib/api";
import { Icon } from "@/components/ui";
import Avatar, { AVATARS } from "@/components/avatar";
import type { AvatarName, Profile } from "@/lib/types";

export default function IdentityForm({ profile }: { profile: Profile }) {
  const router = useRouter();
  const [saved, setSaved] = useState({
    username: profile.username,
    avatar: profile.avatar,
  });
  const [username, setUsername] = useState(profile.username);
  const [avatar, setAvatar] = useState<AvatarName>(profile.avatar);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  const cleaned = username.trim().toLowerCase();
  const changed = cleaned !== saved.username || avatar !== saved.avatar;
  // Mirrors the database's own rule, so the problem is visible while
  // typing rather than after a round trip.
  const shapeProblem =
    cleaned.length < 3 || cleaned.length > 24
      ? "Between 3 and 24 characters."
      : !/^[a-z][a-z0-9]*(-[a-z0-9]+)*$/.test(cleaned)
        ? "Lowercase letters, numbers and single hyphens, starting with a letter."
        : "";

  async function save(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!changed || shapeProblem) return;
    setBusy(true);
    setError("");
    setDone(false);
    try {
      const {
        data: { session },
      } = await createClient().auth.getSession();
      if (!session) throw new Error("Please sign in again.");
      const updated = await apiFetch<Profile>("/profile", session.access_token, {
        method: "PATCH",
        body: JSON.stringify({ username: cleaned, avatar }),
      });
      setSaved({ username: updated.username, avatar: updated.avatar });
      setUsername(updated.username);
      setAvatar(updated.avatar);
      setDone(true);
      // The sidebar and the shared world render this name and face from
      // server data, so they stay stale until the route re-renders.
      router.refresh();
    } catch (caught) {
      setError(detail(caught, "We couldn’t save that. Please try again."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="identity-form" onSubmit={save}>
      <div className="identity-preview">
        <Avatar name={avatar} size={64} />
        <div>
          <strong>{cleaned || profile.username}</strong>
          <p>
            Your public identity in the shared world
            {profile.role === "admin" && " · Administrator"}
          </p>
        </div>
      </div>

      <fieldset className="avatar-picker">
        <legend className="field-label">Choose your look</legend>
        <div className="avatar-options">
          {AVATARS.map((option) => (
            <label
              key={option.name}
              className={`avatar-option ${avatar === option.name ? "selected" : ""}`}
            >
              <input
                type="radio"
                name="avatar"
                value={option.name}
                checked={avatar === option.name}
                onChange={() => setAvatar(option.name)}
              />
              <Avatar name={option.name} size={46} />
              <span>{option.label}</span>
            </label>
          ))}
        </div>
      </fieldset>

      <label className="field identity-name">
        <span className="field-label">Your name in the world</span>
        <input
          className="input"
          value={username}
          maxLength={24}
          autoComplete="off"
          spellCheck={false}
          aria-describedby="username-hint"
          onChange={(e) => {
            setUsername(e.target.value);
            setDone(false);
          }}
        />
        <span className="field-hint" id="username-hint">
          {username.trim() && shapeProblem
            ? shapeProblem
            : "Other people see this name, never your real one. Lowercase letters, numbers and hyphens."}
        </span>
      </label>

      <div className="identity-actions">
        <button
          className="button button-primary"
          type="submit"
          disabled={busy || !changed || Boolean(shapeProblem)}
        >
          {busy ? "Saving…" : "Save identity"} <Icon name="arrow" size={15} />
        </button>
        {done && !changed && (
          <span className="form-status" role="status">
            <Icon name="check" size={14} /> Saved
          </span>
        )}
      </div>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
    </form>
  );
}

/** apiFetch throws `METHOD /path failed (409): {"detail":"…"}`; "that name
 * is taken" is the whole point of the message, so dig it back out. */
function detail(caught: unknown, fallback: string) {
  const message = caught instanceof Error ? caught.message : "";
  const body = message.slice(message.indexOf("): ") + 3);
  try {
    const parsed = JSON.parse(body);
    if (typeof parsed.detail === "string") return parsed.detail;
    if (Array.isArray(parsed.detail))
      return parsed.detail[0]?.msg?.replace(/^Value error, /, "") ?? fallback;
  } catch {
    // Not a JSON error body — a network failure, or the API being down.
  }
  return fallback;
}
