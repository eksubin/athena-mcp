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

// The lane of open ground left between neighbouring parcels, so two plots
// never share an edge and it stays obvious where one person's land ends
// and the next begins.
const PLOT_MARGIN = 1.5;
const PARCEL = PLOT_SPACING - PLOT_MARGIN * 2;

// Each plot is a slab of land rather than a painted square, so its edge
// reads as a boundary from any angle and casts a shadow onto the ground
// below. Everything standing on a plot is raised by its thickness.
const SLAB_HEIGHT = 1.6;

// structure_position() fills rightwards and upwards *from* the origin
// rather than around it, so the parcel is centred on that block of
// structures, not on the origin itself. Centred on the origin, a plot's
// own buildings would sit in its corner and spill over the edge.
const PARCEL_OFFSET_X = ((STRUCTURES_PER_ROW - 1) * STRUCTURE_SPACING) / 2;
const PARCEL_OFFSET_Z = -PARCEL_OFFSET_X;

// The kerb sits entirely outside the slab's footprint, as [x, z, w, d].
const KERB_T = 0.4;
const KERB_AT = PARCEL / 2 + KERB_T / 2;
const KERB_LEN = PARCEL + KERB_T * 2;
const KERB: [number, number, number, number][] = [
  [0, -KERB_AT, KERB_LEN, KERB_T],
  [0, KERB_AT, KERB_LEN, KERB_T],
  [-KERB_AT, 0, KERB_T, KERB_LEN],
  [KERB_AT, 0, KERB_T, KERB_LEN],
];

// Structures are spaced STRUCTURE_SPACING apart, which leaves room for
// each to be noticeably bigger than its own footprint.
const STRUCTURE_SCALE = 1.55;

// A house's windows, as [x, z, width, depth] on its four walls.
const WINDOWS: [number, number, number, number][] = [
  [-0.46, 0.72, 0.3, 0.06],
  [0.46, 0.72, 0.3, 0.06],
  [-0.4, -0.72, 0.3, 0.06],
  [0.4, -0.72, 0.3, 0.06],
  [0.82, 0.32, 0.06, 0.3],
  [0.82, -0.32, 0.06, 0.3],
  [-0.82, 0.32, 0.06, 0.3],
  [-0.82, -0.32, 0.06, 0.3],
];

const POST = PARCEL / 2 - 1.1;
const CORNERS: [number, number][] = [
  [-POST, -POST],
  [POST, -POST],
  [-POST, POST],
  [POST, POST],
];

const PALETTE = {
  sky: "#eef1f8",
  ground: "#e3e8f1",
  soil: "#c8a681",
  soilDeep: "#b08f6b",
  grass: ["#8ec489", "#85bd84", "#97cb90", "#82b881"],
  grassSelf: "#8ac98a",
  bark: "#8a6a4b",
  barkDark: "#75573c",
  leafDark: "#4f9a5c",
  leafMid: "#5cab66",
  leafLight: "#74c077",
  sprout: "#8ed48a",
  wall: "#f6efe3",
  wallShade: "#e7dccb",
  roof: "#c97059",
  roofDark: "#b25f49",
  door: "#8a6a4b",
  window: "#9fc4e8",
  stone: "#dfe3ec",
  stoneDark: "#c3cad8",
  gold: "#e3b964",
  brand: "#5b4ee8",
  brandSoft: "#8f86f0",
};

/** Stable pseudo-randomness from a row's id.
 *
 * A field where every tree is the same height and faces the same way
 * reads as a spreadsheet, not a place — but the variation has to be the
 * same on every render and every client, so it comes from the id rather
 * than Math.random(). */
function hash(seed: string): number {
  let h = 2166136261;
  for (let i = 0; i < seed.length; i++) {
    h ^= seed.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return (h >>> 0) / 4294967296;
}

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

  // One shadow map has to cover every plot, so its orthographic camera is
  // sized from the world rather than left at the default few units — at
  // that size the shadows simply stop part-way across the ground.
  const shadowExtent = groundSize * 0.6;

  return (
    <Canvas
      camera={{ position: [focus[0] + 26, 34, focus[2] + 52], fov: 42 }}
      shadows
      dpr={[1, 2]}
    >
      <color attach="background" args={[PALETTE.sky]} />
      {/* Distant plots fade into the background instead of ending at a
          hard edge, which is what made the ground read as a flat sheet. */}
      <fog attach="fog" args={[PALETTE.sky, groundSize * 0.28, groundSize * 0.72]} />

      <hemisphereLight args={["#ffffff", "#cfd9c6", 1.1]} />
      <ambientLight intensity={0.35} />
      <directionalLight
        position={[groundSize * 0.3, groundSize * 0.45, groundSize * 0.22]}
        intensity={1.5}
        castShadow
        shadow-mapSize={[2048, 2048]}
        shadow-bias={-0.0008}
        shadow-camera-near={1}
        shadow-camera-far={groundSize * 2}
        shadow-camera-left={-shadowExtent}
        shadow-camera-right={shadowExtent}
        shadow-camera-top={shadowExtent}
        shadow-camera-bottom={-shadowExtent}
      />

      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.02, 0]} receiveShadow>
        <planeGeometry args={[groundSize, groundSize]} />
        <meshStandardMaterial color={PALETTE.ground} />
      </mesh>

      {plots.map((plot) => (
        <PlotLand
          key={plot.user_id}
          plot={plot}
          isSelf={plot.user_id === currentUserId}
        />
      ))}
      {structures.map((structure) => (
        <StructureMesh key={structure.id} structure={structure} />
      ))}

      <OrbitControls
        maxPolarAngle={Math.PI / 2.3}
        minDistance={12}
        maxDistance={groundSize}
        enableDamping
        target={[focus[0], SLAB_HEIGHT, focus[2]]}
      />
    </Canvas>
  );
}

/** One user's land: a slab of soil with a grass top, a rim marking the
 * boundary, and corner posts. */
function PlotLand({ plot, isSelf }: { plot: Plot; isSelf: boolean }) {
  const seed = hash(plot.user_id);
  const grass = isSelf
    ? PALETTE.grassSelf
    : PALETTE.grass[Math.floor(seed * PALETTE.grass.length)];
  const rim = isSelf ? PALETTE.brand : PALETTE.stoneDark;

  // A handful of tufts, placed from the plot's own id so they land in the
  // same spots on every render — and away from the middle, where the
  // structures go.
  const tufts = useMemo(() => {
    const half = PARCEL / 2 - 2.5;
    return Array.from({ length: 7 }, (_, i) => {
      const a = hash(`${plot.user_id}-tuft-${i}`);
      const b = hash(`${plot.user_id}-tuft-${i}-b`);
      return {
        x: (a * 2 - 1) * half,
        z: (b * 2 - 1) * half,
        s: 0.7 + a * 0.6,
        r: b * Math.PI,
      };
    });
  }, [plot.user_id]);

  return (
    <group
      position={[
        plot.origin_x + PARCEL_OFFSET_X,
        0,
        plot.origin_y + PARCEL_OFFSET_Z,
      ]}
    >
      {/* Six materials on one box: grass on top, soil on the sides. A
          single-material slab would be a green cube with no edge to it. */}
      <mesh position={[0, SLAB_HEIGHT / 2, 0]} castShadow receiveShadow>
        <boxGeometry args={[PARCEL, SLAB_HEIGHT, PARCEL]} />
        <meshStandardMaterial attach="material-0" color={PALETTE.soil} />
        <meshStandardMaterial attach="material-1" color={PALETTE.soil} />
        <meshStandardMaterial attach="material-2" color={grass} />
        <meshStandardMaterial attach="material-3" color={PALETTE.soilDeep} />
        <meshStandardMaterial attach="material-4" color={PALETTE.soil} />
        <meshStandardMaterial attach="material-5" color={PALETTE.soil} />
      </mesh>

      {/* A kerb around the lawn: the boundary, and the one place the
          plot's owner is marked. Four bars rather than one box — a box
          this size would simply lie on top of the grass and hide it. */}
      {KERB.map(([x, z, w, d], i) => (
        <mesh key={i} position={[x, SLAB_HEIGHT - 0.02, z]} castShadow>
          <boxGeometry args={[w, 0.34, d]} />
          <meshStandardMaterial color={rim} />
        </mesh>
      ))}

      {CORNERS.map(([x, z]) => (
        <group key={`${x},${z}`} position={[x, SLAB_HEIGHT, z]}>
          <mesh position={[0, 0.5, 0]} castShadow>
            <cylinderGeometry args={[0.16, 0.19, 1, 6]} />
            <meshStandardMaterial color={PALETTE.bark} flatShading />
          </mesh>
          <mesh position={[0, 1.07, 0]} castShadow>
            <sphereGeometry args={[0.21, 8, 6]} />
            <meshStandardMaterial
              color={isSelf ? PALETTE.brand : PALETTE.stone}
              flatShading
            />
          </mesh>
        </group>
      ))}

      {tufts.map((t, i) => (
        <mesh
          key={i}
          position={[t.x, SLAB_HEIGHT + 0.24 * t.s, t.z]}
          rotation={[0, t.r, 0]}
          scale={t.s}
          castShadow
        >
          <coneGeometry args={[0.3, 0.42, 4]} />
          <meshStandardMaterial color={PALETTE.leafLight} flatShading />
        </mesh>
      ))}

      <Html center distanceFactor={38} position={[0, SLAB_HEIGHT + 0.8, PARCEL / 2 + 2]}>
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
  // The only thing added here is the height of the land it stands on.
  const seed = hash(structure.id);
  return (
    <group
      position={[structure.grid_x, SLAB_HEIGHT, structure.grid_y]}
      rotation={[0, seed * Math.PI * 2, 0]}
      scale={STRUCTURE_SCALE * (0.92 + seed * 0.18)}
    >
      <StructureGeometry type={structure.type} seed={seed} />
    </group>
  );
}

function StructureGeometry({
  type,
  seed,
}: {
  type: StructureType;
  seed: number;
}) {
  switch (type) {
    // A saved role: barely out of the ground, but it is something.
    case "sapling":
      return (
        <>
          <mesh position={[0, 0.22, 0]} castShadow>
            <cylinderGeometry args={[0.055, 0.075, 0.44, 5]} />
            <meshStandardMaterial color={PALETTE.bark} flatShading />
          </mesh>
          <mesh position={[0, 0.58, 0]} castShadow>
            <icosahedronGeometry args={[0.3, 0]} />
            <meshStandardMaterial color={PALETTE.sprout} flatShading />
          </mesh>
          <mesh position={[0.16, 0.42, 0.05]} castShadow>
            <icosahedronGeometry args={[0.17, 0]} />
            <meshStandardMaterial color={PALETTE.leafLight} flatShading />
          </mesh>
        </>
      );

    // Applied, or followed up: a tree that has taken hold.
    case "tree":
      return (
        <>
          <mesh position={[0, 0.5, 0]} castShadow>
            <cylinderGeometry args={[0.13, 0.19, 1, 6]} />
            <meshStandardMaterial color={PALETTE.bark} flatShading />
          </mesh>
          <mesh position={[0, 1.25, 0]} castShadow receiveShadow>
            <icosahedronGeometry args={[0.92, 0]} />
            <meshStandardMaterial color={PALETTE.leafDark} flatShading />
          </mesh>
          <mesh
            position={[0.22, 1.72, -0.12]}
            rotation={[0.3, seed * 3, 0]}
            castShadow
          >
            <icosahedronGeometry args={[0.64, 0]} />
            <meshStandardMaterial color={PALETTE.leafMid} flatShading />
          </mesh>
          <mesh position={[-0.18, 2.06, 0.1]} castShadow>
            <icosahedronGeometry args={[0.38, 0]} />
            <meshStandardMaterial color={PALETTE.leafLight} flatShading />
          </mesh>
        </>
      );

    // An interview: somewhere to actually live.
    case "house":
      return (
        <>
          <mesh position={[0, 0.06, 0]} receiveShadow>
            <boxGeometry args={[1.9, 0.12, 1.7]} />
            <meshStandardMaterial color={PALETTE.stoneDark} />
          </mesh>
          <mesh position={[0, 0.62, 0]} castShadow receiveShadow>
            <boxGeometry args={[1.6, 1, 1.4]} />
            <meshStandardMaterial color={PALETTE.wall} />
          </mesh>
          {/* A pyramid roof, turned so its ridges meet the walls square. */}
          <mesh position={[0, 1.48, 0]} rotation={[0, Math.PI / 4, 0]} castShadow>
            <coneGeometry args={[1.42, 0.86, 4]} />
            <meshStandardMaterial color={PALETTE.roof} flatShading />
          </mesh>
          <mesh position={[0, 0.42, 0.72]} castShadow>
            <boxGeometry args={[0.38, 0.6, 0.06]} />
            <meshStandardMaterial color={PALETTE.door} />
          </mesh>
          {/* Every wall gets a window. Each house is turned a different
              way, so with windows on one face only, most of them would
              show the viewer a blank side. */}
          {WINDOWS.map(([x, z, w, d], i) => (
            <mesh key={i} position={[x, 0.78, z]}>
              <boxGeometry args={[w, 0.32, d]} />
              <meshStandardMaterial
                color={PALETTE.window}
                emissive={PALETTE.window}
                emissiveIntensity={0.25}
              />
            </mesh>
          ))}
          <mesh position={[0.5, 1.68, -0.3]} castShadow>
            <boxGeometry args={[0.24, 0.5, 0.24]} />
            <meshStandardMaterial color={PALETTE.roofDark} />
          </mesh>
        </>
      );

    // An offer: the thing worth putting up a monument for.
    case "landmark":
      return (
        <>
          <mesh position={[0, 0.1, 0]} castShadow receiveShadow>
            <boxGeometry args={[1.5, 0.2, 1.5]} />
            <meshStandardMaterial color={PALETTE.stone} />
          </mesh>
          <mesh position={[0, 0.32, 0]} castShadow>
            <boxGeometry args={[1.1, 0.26, 1.1]} />
            <meshStandardMaterial color={PALETTE.stoneDark} />
          </mesh>
          <mesh position={[0, 1.2, 0]} castShadow>
            <cylinderGeometry args={[0.34, 0.5, 1.52, 6]} />
            <meshStandardMaterial color={PALETTE.brand} flatShading />
          </mesh>
          <mesh position={[0, 1.42, 0]} castShadow>
            <cylinderGeometry args={[0.42, 0.42, 0.22, 6]} />
            <meshStandardMaterial
              color={PALETTE.gold}
              metalness={0.5}
              roughness={0.3}
            />
          </mesh>
          <mesh position={[0, 2.06, 0]} castShadow>
            <cylinderGeometry args={[0.5, 0.36, 0.26, 6]} />
            <meshStandardMaterial
              color={PALETTE.gold}
              metalness={0.5}
              roughness={0.3}
            />
          </mesh>
          <mesh position={[0, 2.66, 0]} rotation={[0, 0, 0.26]} castShadow>
            <octahedronGeometry args={[0.52, 0]} />
            <meshStandardMaterial
              color={PALETTE.brandSoft}
              emissive={PALETTE.brand}
              emissiveIntensity={0.9}
              flatShading
            />
          </mesh>
        </>
      );

    // A closed application: cut back, but the ground is still yours, and
    // something is already growing out of it again.
    case "stump":
      return (
        <>
          <mesh position={[0, 0.17, 0]} castShadow receiveShadow>
            <cylinderGeometry args={[0.32, 0.38, 0.34, 9]} />
            <meshStandardMaterial color={PALETTE.barkDark} flatShading />
          </mesh>
          <mesh position={[0, 0.35, 0]}>
            <cylinderGeometry args={[0.3, 0.3, 0.03, 9]} />
            <meshStandardMaterial color={PALETTE.soil} />
          </mesh>
          <mesh position={[0.3, 0.28, 0.12]} rotation={[0, 0, -0.5]} castShadow>
            <icosahedronGeometry args={[0.15, 0]} />
            <meshStandardMaterial color={PALETTE.sprout} flatShading />
          </mesh>
        </>
      );
  }
}
