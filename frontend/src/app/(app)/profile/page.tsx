import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { apiFetch } from "@/lib/api";
import type { Answer, Profile, ProfileFact } from "@/lib/types";
import { Icon, PageHeading, SectionHeading } from "@/components/ui";
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
    <>
      <PageHeading
        eyebrow="Your story, ready for what’s next"
        title="A profile that’s all you."
        description="Your experience, your preferences, your words. Give every application a stronger starting point."
      />
      <div className="card profile-summary">
        <span className="avatar">
          {profile.username.slice(0, 2).toUpperCase()}
        </span>
        <div>
          <h2>{profile.username}</h2>
          <p>Your public identity in the shared world</p>
        </div>
        <span className="privacy-note">
          <Icon name="shield" size={15} /> Your resume and answers stay private
        </span>
      </div>
      <div className="profile-grid">
        <section className="card card-pad">
          <SectionHeading
            icon="file"
            title="Your resume"
            description="Upload your experience once. We’ll pull out contact details and recognizable skills."
          />
          <ResumeUpload />
          <ExtractedFacts facts={facts} />
        </section>
        <section className="card card-pad">
          <SectionHeading
            icon="settings"
            title="The right fit"
            description="Tell us what matters. These preferences help rank the opportunities you discover."
          />
          <PreferencesForm initialPreferences={profile.preferences} />
        </section>
        <section className="card card-pad full-width">
          <SectionHeading
            icon="message"
            title="Your answer library"
            description="Thoughtful answers, ready to reuse. Keep sensitive details marked for confirmation."
          />
          <AnswerBank initialAnswers={answers} />
        </section>
      </div>
    </>
  );
}
