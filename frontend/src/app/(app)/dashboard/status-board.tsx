"use client";

import Link from "next/link";
import { useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { apiFetch } from "@/lib/api";
import { Icon } from "@/components/ui";
import type { Application, ApplicationStatus } from "@/lib/types";

const STATUSES: ApplicationStatus[] = [
  "saved",
  "applied",
  "pending",
  "interview",
  "offer",
  "rejected",
];
const LABELS: Record<ApplicationStatus, string> = {
  saved: "Saved",
  applied: "Applied",
  pending: "Pending",
  interview: "Interview",
  offer: "Offer",
  rejected: "Closed",
};
const NEXT: Partial<Record<ApplicationStatus, ApplicationStatus>> = {
  saved: "applied",
  applied: "pending",
  pending: "interview",
  interview: "offer",
};
interface Props {
  initialApplications: Application[];
}

export default function StatusBoard({ initialApplications }: Props) {
  const [applications, setApplications] = useState(initialApplications);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [view, setView] = useState<"board" | "list">("board");
  const count = (status: ApplicationStatus) =>
    applications.filter((a) => a.status === status).length;
  const active = applications.filter(
    (a) =>
      a.status !== "saved" && a.status !== "rejected" && a.status !== "offer",
  ).length;
  const search = query.trim().toLowerCase();
  const filtered = applications.filter(
    (a) =>
      !search ||
      [a.job?.title, a.job?.company, a.job?.location, LABELS[a.status]]
        .join(" ")
        .toLowerCase()
        .includes(search),
  );

  async function advance(app: Application) {
    const next = NEXT[app.status];
    if (!next) return;
    setBusyId(app.id);
    setError("");
    try {
      const {
        data: { session },
      } = await createClient().auth.getSession();
      if (!session)
        throw new Error("Please sign in again to update this application.");
      const updated = await apiFetch<Application>(
        `/applications/${app.id}`,
        session.access_token,
        { method: "PATCH", body: JSON.stringify({ status: next }) },
      );
      setApplications((prev) =>
        prev.map((a) => (a.id === updated.id ? updated : a)),
      );
    } catch {
      setError("We couldn’t move this application. Please try again.");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <>
      <div
        className="overview-grid"
        aria-label="Application summary"
        aria-live="polite"
      >
        <section className="card metric-card metric-wide">
          <div className="metric-top">
            <span>Total opportunities</span>
            <Icon name="briefcase" size={18} />
          </div>
          <div className="metric-bottom">
            <p className="metric-number">
              {applications.length.toString().padStart(2, "0")}
            </p>
            <span className="metric-caption">
              {active} in progress
              <br />
              {count("saved")} saved for later
            </span>
          </div>
          <div className="metric-bar" aria-hidden="true">
            {STATUSES.map((status) => (
              <span
                key={status}
                style={{ flex: Math.max(count(status), 0.2) }}
              />
            ))}
          </div>
          <p className="metric-note">Every next step, in one place</p>
        </section>
        <section className="card metric-card">
          <div className="metric-top">
            <span>Interviews</span>
            <Icon name="message" size={18} />
          </div>
          <p className="metric-number">
            {count("interview").toString().padStart(2, "0")}
          </p>
          <p className="metric-note">Conversations worth preparing for</p>
        </section>
        <section className="card metric-card">
          <div className="metric-top">
            <span>Offers</span>
            <Icon name="spark" size={18} />
          </div>
          <p className="metric-number">
            {count("offer").toString().padStart(2, "0")}
          </p>
          <p className="metric-note">New chapters on the horizon</p>
        </section>
      </div>
      <section aria-labelledby="pipeline-heading">
        <div className="section-title-row">
          <div>
            <h2 id="pipeline-heading">Your application pipeline</h2>
            <p>From a first possibility to your next chapter.</p>
          </div>
          <span className="pill">{applications.length} opportunities</span>
        </div>
        <div className="board-toolbar">
          <div className="segmented" aria-label="Pipeline view">
            <button
              className={view === "board" ? "selected" : ""}
              aria-pressed={view === "board"}
              onClick={() => setView("board")}
            >
              <Icon name="grid" size={14} /> Board view
            </button>
            <button
              className={view === "list" ? "selected" : ""}
              aria-pressed={view === "list"}
              onClick={() => setView("list")}
            >
              <Icon name="list" size={14} /> List view
            </button>
          </div>
          <label className="search-field">
            <Icon name="search" size={16} />
            <input
              type="search"
              aria-label="Search applications"
              placeholder="Search roles or companies…"
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
        {applications.length === 0 && (
          <div className="card action-card" style={{ marginBottom: 20 }}>
            <span className="icon-tile">
              <Icon name="briefcase" />
            </span>
            <div>
              <h3>Your next opportunity starts here.</h3>
              <p>
                Connect your assistant to find and save roles. Your applications
                will appear here as you go.
              </p>
              <Link href="/settings" className="text-action">
                Connect your assistant <Icon name="arrow" size={14} />
              </Link>
            </div>
          </div>
        )}
        {search && filtered.length === 0 && (
          <p className="form-status" role="status" style={{ marginBottom: 16 }}>
            No roles or companies match “{query}”. Try another search.
          </p>
        )}
        <div className={`kanban ${view === "list" ? "list-view" : ""}`}>
          {STATUSES.map((status) => {
            const items = filtered.filter((a) => a.status === status);
            return (
              <section
                key={status}
                className="kanban-column"
                aria-label={LABELS[status]}
              >
                <div className="column-heading">
                  <span className={`status-dot ${status}`} />
                  <h3>{LABELS[status]}</h3>
                  <span className="count-badge">{items.length}</span>
                </div>
                <div className="job-stack">
                  {items.map((a) => {
                    const job = a.job;
                    const next = NEXT[a.status];
                    return (
                      <article className="job-card" key={a.id}>
                        <div className="job-top">
                          <span className="company-mark">
                            {(job?.company ?? "Role").slice(0, 2).toUpperCase()}
                          </span>
                          <span className="job-company" title={job?.company}>
                            {job?.company ?? "Company unavailable"}
                          </span>
                        </div>
                        <h3>
                          {job?.url ? (
                            <a
                              className="job-title-link"
                              href={job.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              title={`Open this listing on ${sourceLabel(job.source)}`}
                            >
                              {job.title}
                              <Icon name="link" size={12} />
                            </a>
                          ) : (
                            (job?.title ?? "Role details unavailable")
                          )}
                        </h3>
                        <p className="job-meta">
                          <Icon name="location" size={12} />
                          {job?.remote
                            ? "Remote"
                            : job?.location || "Location not listed"}
                          {job?.source && <span>· {sourceLabel(job.source)}</span>}
                          {job?.posted_at && (
                            <span>· Posted {postedLabel(job.posted_at)}</span>
                          )}
                        </p>
                        <div className="job-footer">
                          <span className="pill">
                            {salaryLabel(job)}
                          </span>
                          <span className="job-actions">
                            {job?.url && (
                              <a
                                className="text-action"
                                href={job.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                aria-label={`Open the listing for ${job.title} in a new tab`}
                              >
                                Listing <Icon name="link" size={12} />
                              </a>
                            )}
                            {next && (
                              <button
                                onClick={() => advance(a)}
                                disabled={busyId === a.id}
                                className="text-action"
                                aria-label={`Move ${job?.title ?? "application"} to ${LABELS[next]}`}
                              >
                                {busyId === a.id ? "Moving…" : LABELS[next]}{" "}
                                <Icon name="arrow" size={12} />
                              </button>
                            )}
                          </span>
                        </div>
                      </article>
                    );
                  })}
                </div>
                {items.length === 0 && (
                  <div className="column-empty">
                    {search ? "No matches" : "No opportunities here yet"}
                  </div>
                )}
              </section>
            );
          })}
        </div>
      </section>
    </>
  );
}

/** "linkedin" is a brand; "careers.example.com" is already a label. The
 * fallback host for an unrecognized board reads better capitalized only on
 * the known names. */
const SOURCE_LABELS: Record<string, string> = {
  linkedin: "LinkedIn",
  greenhouse: "Greenhouse",
  lever: "Lever",
  hn: "Hacker News",
};
function sourceLabel(source: string | null) {
  if (!source) return "the listing";
  return SOURCE_LABELS[source] ?? source;
}

function salaryLabel(job: Application["job"]) {
  if (!job?.salary_min && !job?.salary_max) return "Tracked role";
  const k = (value: number) => "$" + Math.round(value / 1000) + "k";
  if (job.salary_min && job.salary_max && job.salary_min !== job.salary_max)
    return `${k(job.salary_min)}–${k(job.salary_max)}`;
  return k((job.salary_min ?? job.salary_max) as number) + "+";
}

function postedLabel(postedAt: string) {
  const days = Math.floor(
    (Date.now() - new Date(postedAt).getTime()) / 86_400_000,
  );
  if (days <= 0) return "today";
  if (days === 1) return "yesterday";
  if (days < 30) return `${days} days ago`;
  return new Date(postedAt).toISOString().slice(0, 10);
}
