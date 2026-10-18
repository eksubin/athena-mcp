"use client";

import { useEffect, useMemo, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Html } from "@react-three/drei";
import type { Plot, Structure, StructureType } from "@/lib/types";

interface Props {
  initialPlots: Plot[];
  initialStructures: Structure[];
  currentUserId: string;
}

// These mirror backend/app/services/world.py. The backend decides where a
// plot sits and where each structure lands inside it; this file only has
// to draw the parcel those numbers imply, so the two must agree.
const PLOT_SPACING = 40; // distance between neighbouring plot origins
const STRUCTURE_SPACING = 4;
const STRUCTURES_PER_ROW = 6;

// The lane of untouched ground left between neighbouring parcels, so two
// boundaries never share an edge and it stays obvious where one person's
// land ends and the next begins.
const PLOT_MARGIN = 1.5;
const PARCEL = PLOT_SPACING - PLOT_MARGIN * 2;
const BORDER = 1.1;

// structure_position() fills rightwards and upwards *from* the origin
// rather than around it, so the parcel is centred on that block of
// structures, not on the origin itself. Centred on the origin, a plot's
// own buildings would sit in its corner and spill over the edge.
const PARCEL_OFFSET_X = ((STRUCTURES_PER_ROW - 1) * STRUCTURE_SPACING) / 2;
const PARCEL_OFFSET_Z = -PARCEL_OFFSET_X;

// Corner posts, inset so they read as markers standing on the land.
const POST = PARCEL / 2 - 1.4;
const CORNERS: [number, number][] = [
  [-POST, -POST],
  [POST, -POST],
  [-POST, POST],
  [POST, POST],
];

export default function WorldScene({
  initialPlots,
  initialStructures,
  currentUserId,
}: Props) {
  const plots = initialPlots;
  const structures = initialStructures;
  const router = useRouter();
  const [isPending, startTransition] = useTransition();

  // The local stack has PostgREST but no Realtime service. Refresh the
  // server data while visible, preserving the canvas and camera state.
  useEffect(() => {
    const refresh = () => {
      if (document.visibilityState === "visible" && !isPending) {
        startTransition(() => router.refresh());
      }
    };
    const timer = window.setInterval(refresh, 15000);
    document.addEventListener("visibilitychange", refresh);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", refresh);
    };
  }, [router, isPending]);

  const groundSize = useMemo(() => {
    const maxCoord = plots.reduce(
      (max, p) => Math.max(max, Math.abs(p.origin_x), Math.abs(p.origin_y)),
      PLOT_SPACING,
    );
    // + a full plot so the outermost parcel has ground under all of it,
    // including the half that sits past its own origin.
    return (maxCoord + PLOT_SPACING * 1.5) * 2;
  }, [plots]);

  const focus = useMemo<[number, number, number]>(() => {
    const ownPlot = plots.find((plot) => plot.user_id === currentUserId);
    return [
      (ownPlot?.origin_x ?? 0) + PARCEL_OFFSET_X,
      0,
      (ownPlot?.origin_y ?? 0) + PARCEL_OFFSET_Z,
    ];
  }, [plots, currentUserId]);

  return (
    <Canvas
      camera={{ position: [focus[0] + 30, 40, focus[2] + 60], fov: 45 }}
      shadows
    >
      <ambientLight intensity={0.7} />
      <directionalLight position={[40, 60, 20]} intensity={1.1} castShadow />
      <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
        <planeGeometry args={[groundSize, groundSize]} />
        <meshStandardMaterial color="#ECEFF5" />
      </mesh>
      {/* One line per plot, so the only grid on the ground is the one the
          parcels actually sit on. */}
      <gridHelper
        args={[groundSize, groundSize / PLOT_SPACING, "#DDE2EC", "#E5E9F1"]}
        position={[PARCEL_OFFSET_X, 0, PARCEL_OFFSET_Z]}
      />

      {plots.map((plot) => (
        <PlotMarker
          key={plot.user_id}
          plot={plot}
          isSelf={plot.user_id === currentUserId}
        />
      ))}
      {structures.map((structure) => (
        <StructureMesh key={structure.id} structure={structure} />
      ))}

      <OrbitControls
        maxPolarAngle={Math.PI / 2.1}
        minDistance={10}
        maxDistance={groundSize}
        target={focus}
      />
    </Canvas>
  );
}

/** One user's land: a bordered parcel with a post at each corner.
 *
 * Drawn as two stacked planes rather than an outlined shape — the larger
 * one in the border colour shows only as a frame around the smaller fill
 * on top of it. A line primitive would be a pixel wide whatever the
 * camera distance, and these plots are usually seen from far away. */
function PlotMarker({ plot, isSelf }: { plot: Plot; isSelf: boolean }) {
  const border = isSelf ? "#5B4EE8" : "#C2CAD9";
  const fill = isSelf ? "#EFEDFD" : "#F6F8FC";
  return (
    <group
      position={[
        plot.origin_x + PARCEL_OFFSET_X,
        0,
        plot.origin_y + PARCEL_OFFSET_Z,
      ]}
    >
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.01, 0]}>
        <planeGeometry args={[PARCEL, PARCEL]} />
        <meshBasicMaterial color={border} transparent opacity={isSelf ? 0.9 : 0.7} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.02, 0]} receiveShadow>
        <planeGeometry args={[PARCEL - BORDER * 2, PARCEL - BORDER * 2]} />
        <meshStandardMaterial color={fill} />
      </mesh>
      {CORNERS.map(([x, z]) => (
        <mesh key={`${x},${z}`} position={[x, 0.45, z]} castShadow>
          <cylinderGeometry args={[0.22, 0.26, 0.9, 6]} />
          <meshStandardMaterial color={isSelf ? "#5B4EE8" : "#AEB7C8"} />
        </mesh>
      ))}
      <Html center distanceFactor={40} position={[0, 0.6, PARCEL / 2 + 1.6]}>
        <div
          className={`rounded-full px-2 py-0.5 text-[10px] font-medium whitespace-nowrap shadow-sm ${
            isSelf ? "bg-[#5b4ee8] text-white" : "bg-white/90 text-slate-600"
          }`}
        >
          {plot.username}
          {isSelf ? " (you)" : ""}
        </div>
      </Html>
    </group>
  );
}

function StructureMesh({ structure }: { structure: Structure }) {
  // grid_x/grid_y are absolute world coordinates already offset by the
  // owner's plot origin — see backend/app/services/world.py:structure_position.
  const position: [number, number, number] = [
    structure.grid_x,
    0,
    structure.grid_y,
  ];
  return (
    <group position={position}>
      <StructureGeometry type={structure.type} />
    </group>
  );
}

function StructureGeometry({ type }: { type: StructureType }) {
  switch (type) {
    case "sapling":
      return (
        <>
          <mesh position={[0, 0.15, 0]} castShadow>
            <cylinderGeometry args={[0.05, 0.06, 0.3, 6]} />
            <meshStandardMaterial color="#7B8498" />
          </mesh>
          <mesh position={[0, 0.4, 0]} castShadow>
            <sphereGeometry args={[0.2, 8, 8]} />
            <meshStandardMaterial color="#A7B0C5" />
          </mesh>
        </>
      );
    case "tree":
      return (
        <>
          <mesh position={[0, 0.5, 0]} castShadow>
            <cylinderGeometry args={[0.12, 0.16, 1, 8]} />
            <meshStandardMaterial color="#7B8498" />
          </mesh>
          <mesh position={[0, 1.6, 0]} castShadow>
            <coneGeometry args={[0.9, 1.8, 8]} />
            <meshStandardMaterial color="#5B4EE8" />
          </mesh>
        </>
      );
    case "house":
      return (
        <>
          <mesh position={[0, 0.6, 0]} castShadow>
            <boxGeometry args={[1.4, 1.2, 1.4]} />
            <meshStandardMaterial color="#BAC2D3" />
          </mesh>
          <mesh
            position={[0, 1.5, 0]}
            rotation={[0, Math.PI / 4, 0]}
            castShadow
          >
            <coneGeometry args={[1.15, 0.9, 4]} />
            <meshStandardMaterial color="#68738B" />
          </mesh>
        </>
      );
    case "landmark":
      return (
        <>
          <mesh position={[0, 1.2, 0]} castShadow>
            <boxGeometry args={[0.8, 2.4, 0.8]} />
            <meshStandardMaterial
              color="#8994AC"
              metalness={0.3}
              roughness={0.4}
            />
          </mesh>
          <mesh position={[0, 2.6, 0]} castShadow>
            <coneGeometry args={[0.6, 0.8, 4]} />
            <meshStandardMaterial
              color="#56627E"
              metalness={0.3}
              roughness={0.4}
            />
          </mesh>
        </>
      );
    case "stump":
      return (
        <mesh position={[0, 0.15, 0]} castShadow>
          <cylinderGeometry args={[0.25, 0.3, 0.3, 10]} />
          <meshStandardMaterial color="#798399" />
        </mesh>
      );
  }
}
