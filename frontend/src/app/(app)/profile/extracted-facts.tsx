import type { ProfileFact } from "@/lib/types";

const FACT_LABELS: Record<string, string> = {
  name: "Name",
  email: "Email",
  phone: "Phone",
  linkedin_url: "LinkedIn",
  github_url: "GitHub",
  skills: "Skills",
};

export default function ExtractedFacts({ facts }: { facts: ProfileFact[] }) {
  if (facts.length === 0) {
    return (
      <p className="text-sm text-stone-400">
        Nothing extracted yet — upload a resume above.
      </p>
    );
  }

  return (
    <div className="flex max-w-lg flex-col gap-2 rounded-lg border border-stone-200 bg-white p-4">
      {facts.map((fact) => (
        <div key={fact.key} className="flex items-start justify-between gap-3 text-sm">
          <span className="w-24 shrink-0 font-medium text-stone-500">
            {FACT_LABELS[fact.key] ?? fact.key}
          </span>
          <span className="flex-1 text-stone-900">{fact.value}</span>
          {fact.confidence < 0.6 && (
            <span
              className="shrink-0 text-[10px] text-stone-400"
              title="Best-effort guess — worth double-checking"
            >
              guess
            </span>
          )}
        </div>
      ))}
    </div>
  );
}
