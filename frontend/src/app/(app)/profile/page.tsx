import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { apiFetch } from "@/lib/api";
import type { Answer, Profile, ProfileFact } from "@/lib/types";
import PreferencesForm from "./preferences-form";
import ResumeUpload from "./resume-upload";
import ExtractedFacts from "./extracted-facts";
import AnswerBank from "./answer-bank";

export default async function ProfilePage() {
  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session) redirect("/login");

  const [profile, answers, facts] = await Promise.all([
    apiFetch<Profile>("/profile", session.access_token),
    apiFetch<Answer[]>("/answers", session.access_token),
    apiFetch<ProfileFact[]>("/profile/facts", session.access_token),
  ]);

  return (
    <div className="flex flex-col gap-10">
      <div>
        <h1 className="text-xl font-semibold text-stone-900">Profile</h1>
        <p className="mt-1 text-sm text-stone-500">
          Signed in as <span className="font-medium text-stone-700">{profile.username}</span> —
          this is what other users see on the map, never your real name.
        </p>
      </div>

      <section>
        <h2 className="text-sm font-semibold text-stone-900">Resume</h2>
        <p className="mt-1 text-sm text-stone-500">
          Contact info and a skills line get pulled out automatically — a best-effort read, not
          a full parse, so double-check anything marked{" "}
          <span className="text-stone-400">guess</span>.
        </p>
        <div className="mt-3 flex flex-col gap-3">
          <ResumeUpload />
          <ExtractedFacts facts={facts} />
        </div>
      </section>

      <section>
        <h2 className="text-sm font-semibold text-stone-900">Search preferences</h2>
        <p className="mt-1 text-sm text-stone-500">
          What <code className="rounded bg-stone-200 px-1 py-0.5 text-xs">search_jobs</code> scores
          against.
        </p>
        <div className="mt-3">
          <PreferencesForm initialPreferences={profile.preferences} />
        </div>
      </section>

      <section>
        <h2 className="text-sm font-semibold text-stone-900">Answer bank</h2>
        <p className="mt-1 text-sm text-stone-500">
          Reusable answers for application questions. Sensitive ones (salary, visa status) still
          get confirmed each time rather than reused silently.
        </p>
        <div className="mt-3">
          <AnswerBank initialAnswers={answers} />
        </div>
      </section>
    </div>
  );
}
