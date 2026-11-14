import Link from "next/link";
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { apiFetch } from "@/lib/api";
import type { AccessToken } from "@/lib/types";
import { Icon, PageHeading, SectionHeading } from "@/components/ui";
import TokenManager from "./token-manager";

export default async function SettingsPage() {
  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session) redirect("/login");
  const tokens = await apiFetch<AccessToken[]>("/tokens", session.access_token);
  return (
    <>
      <PageHeading
        eyebrow="Your workspace, connected"
        title="A little help goes a long way."
        description="Connect your assistant to search for roles, organize applications, and keep your progress up to date."
      />
      <div className="settings-grid">
        <section className="card card-pad">
          <SectionHeading
            icon="key"
            title="Personal access tokens"
            description="A private key for your assistant. Create one for each connection and revoke it whenever you need."
          />
          <TokenManager initialTokens={tokens} />
        </section>
        <aside className="card card-pad">
          <SectionHeading
            icon="spark"
            title="Make the connection"
            description="Three small steps to a more organized search."
          />
          <ol className="guide-steps">
            <li>
              <span className="step-number">01</span>
              <div>
                <h3>Name your connection</h3>
                <p>
                  Use a label you’ll recognize, such as “Claude on my laptop”.
                </p>
              </div>
            </li>
            <li>
              <span className="step-number">02</span>
              <div>
                <h3>Save your private token</h3>
                <p>
                  It’s shown only once. Set it as{" "}
                  <code className="inline-code">ATHENA_TOKEN</code> in your
                  Athena MCP configuration.
                </p>
              </div>
            </li>
            <li>
              <span className="step-number">03</span>
              <div>
                <h3>Start a conversation</h3>
                <p>
                  Ask your connected assistant to find matching jobs, save a
                  role, or update an application.
                </p>
              </div>
            </li>
          </ol>
          <Link
            href="/setup"
            className="text-action"
            style={{ marginTop: 24 }}
          >
            <Icon name="arrow" size={14} />
            Full setup instructions
          </Link>
        </aside>
      </div>
    </>
  );
}
