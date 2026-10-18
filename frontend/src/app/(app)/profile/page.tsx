import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { apiFetch } from "@/lib/api";
import type { Answer, Invite, Profile, ProfileFact } from "@/lib/types";
import { PageHeading, SectionHeading } from "@/components/ui";
import PreferencesForm from "./preferences-form";
import ResumeUpload from "./resume-upload";
import ExtractedFacts from "./extracted-facts";
import AnswerBank from "./answer-bank";
import InvitePanel from "./invite-panel";
import IdentityForm from "./identity-form";

export default async function ProfilePage() {
  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session) redirect("/login");
  const [profile, answers, facts, invites] = await Promise.all([
    apiFetch<Profile>("/profile", session.access_token),
    apiFetch<Answer[]>("/answers", session.access_token),
    apiFetch<ProfileFact[]>("/profile/facts", session.access_token),
    apiFetch<Invite[]>("/invites", session.access_token),
  ]);
  return (
    <>
      <PageHeading
        eyebrow="Your story, ready for what’s next"
        title="A profile that’s all you."
        description="Your experience, your preferences, your words. Give every application a stronger starting point."
      />
      <div className="profile-grid">
        <section className="card card-pad full-width">
          <SectionHeading
            icon="user"
            title="How you appear"
            description="Pick a name and a face for the shared world. Your real name, resume and answers stay private."
          />
          <IdentityForm profile={profile} />
        </section>
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
            icon="mail"
            title="Invite someone in"
            description="Athena is invite-only. Add an address and that person can create their own account."
          />
          <InvitePanel
            initialInvites={invites}
            inviteLimit={profile.invite_limit}
            unlimited={profile.role === "admin"}
          />
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
