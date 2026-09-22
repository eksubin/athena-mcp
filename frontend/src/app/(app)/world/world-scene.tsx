"use client";

import { useEffect, useMemo, useState } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Html } from "@react-three/drei";
import { createClient } from "@/lib/supabase/client";
import type { Plot, Structure, StructureType } from "@/lib/types";

interface Props {
  initialPlots: Plot[];
  initialStructures: Structure[];
  currentUserId: string;
}

export default function WorldScene({ initialPlots, initialStructures, currentUserId }: Props) {
  const [plots, setPlots] = useState(initialPlots);
  const [structures, setStructures] = useState(initialStructures);

  // Live updates: when anyone (including other users, in other tabs) saves,
  // applies, or signs up, their new plot/structure appears here without a
  // refetch — this is what makes "watch others build" actually work.
  useEffect(() => {
    const supabase = createClient();
    const channel = supabase
      .channel("world")
      .on(
        "postgres_changes",
        { event: "INSERT", schema: "public", table: "world_structures" },
        (payload) => {
          setStructures((prev) => [...prev, payload.new as Structure]);
        },
      )
      .on(
        "postgres_changes",
        { event: "INSERT", schema: "public", table: "world_plots" },
        (payload) => {
          const row = payload.new as { user_id: string; origin_x: number; origin_y: number };
          setPlots((prev) =>
            prev.some((p) => p.user_id === row.user_id)
              ? prev
              : [
                  ...prev,
                  { ...row, username: "new arrival", avatar_seed: row.user_id.slice(0, 8) },
                ],
          );
        },
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, []);

  const groundSize = useMemo(() => {
    const maxCoord = plots.reduce(
      (max, p) => Math.max(max, Math.abs(p.origin_x), Math.abs(p.origin_y)),
      40,
    );
    return (maxCoord + 40) * 2;
  }, [plots]);

  return (
    <Canvas camera={{ position: [30, 40, 60], fov: 45 }} shadows>
      <ambientLight intensity={0.7} />
      <directionalLight position={[40, 60, 20]} intensity={1.1} castShadow />
      <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
        <planeGeometry args={[groundSize, groundSize]} />
        <meshStandardMaterial color="#DCEFD9" />
      </mesh>
      <gridHelper args={[groundSize, groundSize / 4, "#B7CDB0", "#CFE3CB"]} />

      {plots.map((plot) => (
        <PlotMarker key={plot.user_id} plot={plot} isSelf={plot.user_id === currentUserId} />
      ))}
      {structures.map((structure) => (
        <StructureMesh key={structure.id} structure={structure} />
      ))}

      <OrbitControls
        maxPolarAngle={Math.PI / 2.1}
        minDistance={10}
        maxDistance={groundSize}
        target={[0, 0, 0]}
      />
    </Canvas>
  );
}

function PlotMarker({ plot, isSelf }: { plot: Plot; isSelf: boolean }) {
  return (
    <group position={[plot.origin_x, 0, plot.origin_y]}>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.01, 0]}>
        <ringGeometry args={[13, 14, 32]} />
        <meshBasicMaterial color={isSelf ? "#2E6B4C" : "#A8B99F"} transparent opacity={0.6} />
      </mesh>
      <Html center distanceFactor={40} position={[0, 0.5, -16]}>
        <div
          className={`rounded-full px-2 py-0.5 text-[10px] font-medium whitespace-nowrap shadow-sm ${
            isSelf ? "bg-emerald-700 text-white" : "bg-white/90 text-stone-700"
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
  const position: [number, number, number] = [structure.grid_x, 0, structure.grid_y];
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
            <meshStandardMaterial color="#8B7355" />
          </mesh>
          <mesh position={[0, 0.4, 0]} castShadow>
            <sphereGeometry args={[0.2, 8, 8]} />
            <meshStandardMaterial color="#7FB069" />
          </mesh>
        </>
      );
    case "tree":
      return (
        <>
          <mesh position={[0, 0.5, 0]} castShadow>
            <cylinderGeometry args={[0.12, 0.16, 1, 8]} />
            <meshStandardMaterial color="#8B7355" />
          </mesh>
          <mesh position={[0, 1.6, 0]} castShadow>
            <coneGeometry args={[0.9, 1.8, 8]} />
            <meshStandardMaterial color="#2E6B4C" />
          </mesh>
        </>
      );
    case "house":
      return (
        <>
          <mesh position={[0, 0.6, 0]} castShadow>
            <boxGeometry args={[1.4, 1.2, 1.4]} />
            <meshStandardMaterial color="#C9A987" />
          </mesh>
          <mesh position={[0, 1.5, 0]} rotation={[0, Math.PI / 4, 0]} castShadow>
            <coneGeometry args={[1.15, 0.9, 4]} />
            <meshStandardMaterial color="#7A4B32" />
          </mesh>
        </>
      );
    case "landmark":
      return (
        <>
          <mesh position={[0, 1.2, 0]} castShadow>
            <boxGeometry args={[0.8, 2.4, 0.8]} />
            <meshStandardMaterial color="#C9A227" metalness={0.3} roughness={0.4} />
          </mesh>
          <mesh position={[0, 2.6, 0]} castShadow>
            <coneGeometry args={[0.6, 0.8, 4]} />
            <meshStandardMaterial color="#8F6F14" metalness={0.3} roughness={0.4} />
          </mesh>
        </>
      );
    case "stump":
      return (
        <mesh position={[0, 0.15, 0]} castShadow>
          <cylinderGeometry args={[0.25, 0.3, 0.3, 10]} />
          <meshStandardMaterial color="#6B5B4A" />
        </mesh>
      );
  }
}
