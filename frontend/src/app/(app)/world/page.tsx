import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { apiFetch } from "@/lib/api";
import type { Plot, Structure } from "@/lib/types";
import { Icon, PageHeading } from "@/components/ui";
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
  const ownStructures = structures.filter((s) => s.user_id === session.user.id);
  return (
    <>
      <PageHeading
        eyebrow="Every step leaves a little something"
        title="Look how far you’ve grown."
        description="A shared world built one opportunity at a time. Your applications become a place that’s uniquely yours."
      />
      <div className="world-grid">
        <div
          className="world-viewport"
          aria-label="Interactive three-dimensional world"
        >
          <WorldScene
            initialPlots={plots}
            initialStructures={structures}
            currentUserId={session.user.id}
          />
          <div className="world-caption">
            Drag to explore · Scroll to zoom · Updates automatically
          </div>
        </div>
        <div className="world-stats">
          <section className="card world-stat">
            <div className="metric-top">
              <span>Your contributions</span>
              <Icon name="spark" size={17} />
            </div>
            <p className="metric-number">
              {ownStructures.length.toString().padStart(2, "0")}
            </p>
            <p className="metric-note">Little reminders of your progress</p>
          </section>
          <section className="card world-stat">
            <div className="metric-top">
              <span>Neighbors</span>
              <Icon name="world" size={17} />
            </div>
            <p className="metric-number">
              {Math.max(plots.length - 1, 0)
                .toString()
                .padStart(2, "0")}
            </p>
            <p className="metric-note">Growing alongside you</p>
          </section>
          <section className="card world-stat">
            <h2 style={{ fontSize: 13, fontWeight: 600 }}>
              How your world grows
            </h2>
            <div className="legend">
              <div className="legend-row">
                <span>Save a role</span>
                <strong>A sapling</strong>
              </div>
              <div className="legend-row">
                <span>Apply or follow up</span>
                <strong>A tree</strong>
              </div>
              <div className="legend-row">
                <span>Get an interview</span>
                <strong>A house</strong>
              </div>
              <div className="legend-row">
                <span>Receive an offer</span>
                <strong>A landmark</strong>
              </div>
            </div>
          </section>
        </div>
      </div>
    </>
  );
}
