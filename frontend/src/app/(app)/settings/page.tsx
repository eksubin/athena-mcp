import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { apiFetch } from "@/lib/api";
import type { AccessToken } from "@/lib/types";
import TokenManager from "./token-manager";

export default async function SettingsPage() {
  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session) redirect("/login");

  const tokens = await apiFetch<AccessToken[]>("/tokens", session.access_token);

  return (
    <div>
      <h1 className="text-xl font-semibold text-stone-900">Settings</h1>
      <p className="mt-1 max-w-xl text-sm text-stone-500">
        MCP personal access tokens — paste one into <code className="rounded bg-stone-200 px-1 py-0.5 text-xs">ATHENA_TOKEN</code> in
        the MCP server&apos;s config so Claude Code can act as you. Each token is shown in full
        exactly once, at creation.
      </p>
      <div className="mt-6">
        <TokenManager initialTokens={tokens} />
      </div>
    </div>
  );
}
