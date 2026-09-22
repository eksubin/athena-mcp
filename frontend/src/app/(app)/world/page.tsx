import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { apiFetch } from "@/lib/api";
import type { Plot, Structure } from "@/lib/types";
import WorldScene from "./world-scene";

export default async function WorldPage() {
  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session) redirect("/login");

  const [plots, structures] = await Promise.all([
    apiFetch<Plot[]>("/world/plots", session.access_token),
    apiFetch<Structure[]>("/world/structures", session.access_token),
  ]);

  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col">
      <div className="mb-3">
        <h1 className="text-xl font-semibold text-stone-900">World</h1>
        <p className="mt-1 text-sm text-stone-500">
          Every signed-in user has a plot. Saving a job plants a sapling, applying grows it into
          a tree, an interview builds a house, an offer raises a landmark — drag to look around.
        </p>
      </div>
      <div className="flex-1 overflow-hidden rounded-lg border border-stone-200 bg-gradient-to-b from-sky-100 to-stone-100">
        <WorldScene
          initialPlots={plots}
          initialStructures={structures}
          currentUserId={session.user.id}
        />
      </div>
    </div>
  );
}
