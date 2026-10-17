import type { ProfileFact } from "@/lib/types";
const LABELS: Record<string, string> = {
  name: "Name",
  email: "Email",
  phone: "Phone",
  linkedin_url: "LinkedIn",
  github_url: "GitHub",
  skills: "Skills",
};

export default function ExtractedFacts({ facts }: { facts: ProfileFact[] }) {
  if (!facts.length)
    return (
      <p className="empty-note">
        Your extracted details will appear here after an upload.
      </p>
    );
  return (
    <dl className="facts">
      {facts.map((fact) => (
        <div className="fact-row" key={fact.key}>
          <dt>{LABELS[fact.key] ?? fact.key}</dt>
          <dd>{fact.value}</dd>
          {fact.confidence < 0.6 && (
            <span
              className="pill"
              title="This is a best-effort guess. Please double-check it."
            >
              Review
            </span>
          )}
        </div>
      ))}
    </dl>
  );
}
