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
      40,
    );
    return (maxCoord + 40) * 2;
  }, [plots]);

  const focus = useMemo<[number, number, number]>(() => {
    const ownPlot = plots.find((plot) => plot.user_id === currentUserId);
    return [ownPlot?.origin_x ?? 0, 0, ownPlot?.origin_y ?? 0];
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
      <gridHelper args={[groundSize, groundSize / 4, "#D3D9E5", "#E1E5EE"]} />

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

function PlotMarker({ plot, isSelf }: { plot: Plot; isSelf: boolean }) {
  return (
    <group position={[plot.origin_x, 0, plot.origin_y]}>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.01, 0]}>
        <ringGeometry args={[13, 14, 32]} />
        <meshBasicMaterial
          color={isSelf ? "#5B4EE8" : "#A8B1C5"}
          transparent
          opacity={0.6}
        />
      </mesh>
      <Html center distanceFactor={40} position={[0, 0.5, -16]}>
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
