import { OrbitControls } from "@react-three/drei";
import { Canvas } from "@react-three/fiber";
import { useMemo } from "react";
import type {
  Building,
  CityMap,
  Coordinate,
  Crossing,
  Infrastructure,
  Road,
  RoadLoad,
  SimulationState
} from "../types/domain";
import { clamp } from "../utils/format";

type Props = {
  cityMap: CityMap | null;
  state: SimulationState | null;
};

export function CityScene({ cityMap, state }: Props) {
  return (
    <div className="city-scene">
      <Canvas camera={{ position: [0, 190, 190], fov: 45 }} shadows>
        <color attach="background" args={["#070b12"]} />
        <ambientLight intensity={0.65} />
        <directionalLight position={[80, 160, 80]} intensity={1.45} castShadow />
        <fog attach="fog" args={["#070b12", 180, 950]} />

        <Ground />

        {cityMap && (
          <group>
            <Roads roads={cityMap.roads} roadLoad={state?.road_load ?? []} />
            <Buildings buildings={cityMap.buildings} />
            <Crossings crossings={cityMap.crossings} />
            <InfrastructureLayer infrastructure={cityMap.infrastructure} />
            <Intersections cityMap={cityMap} />
          </group>
        )}

        {state && cityMap && (
          <group>
            <Vehicles cityMap={cityMap} state={state} />
            <Pedestrians state={state} />
            <Signals cityMap={cityMap} state={state} />
          </group>
        )}

        <OrbitControls
          enableDamping
          dampingFactor={0.08}
          maxPolarAngle={Math.PI / 2.15}
          minDistance={60}
          maxDistance={760}
        />
      </Canvas>
    </div>
  );
}

function Ground() {
  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
      <planeGeometry args={[2400, 2400]} />
      <meshStandardMaterial color="#101827" roughness={1} />
    </mesh>
  );
}

function Roads({ roads, roadLoad }: { roads: Road[]; roadLoad: RoadLoad[] }) {
  const loadByRoad = new Map(roadLoad.map((load) => [load.road_id, load]));

  return (
    <group>
      {roads.map((road) =>
        road.coordinates.slice(1).map((point, index) => {
          const previous = road.coordinates[index];
          const load = loadByRoad.get(road.id);

          return (
            <RoadSegment
              key={`${road.id}:${index}`}
              road={road}
              start={previous}
              end={point}
              congestion={load?.congestion_score ?? 0}
            />
          );
        })
      )}
    </group>
  );
}

function RoadSegment({
  road,
  start,
  end,
  congestion
}: {
  road: Road;
  start: Coordinate;
  end: Coordinate;
  congestion: number;
}) {
  const dx = end.x - start.x;
  const dz = end.z - start.z;
  const length = Math.sqrt(dx * dx + dz * dz);
  const angle = Math.atan2(dz, dx);
  const width = road.kind === "primary" ? 12 : road.kind === "secondary" ? 9 : 6;
  const color = congestion > 0.6 ? "#ef4444" : congestion > 0.3 ? "#f97316" : "#263244";

  return (
    <group position={[(start.x + end.x) / 2, 0.18, (start.z + end.z) / 2]} rotation={[0, -angle, 0]}>
      <mesh receiveShadow>
        <boxGeometry args={[length, 0.28, width]} />
        <meshStandardMaterial color={color} roughness={0.85} />
      </mesh>

      <mesh position={[0, 0.22, 0]}>
        <boxGeometry args={[length * 0.92, 0.06, 0.24]} />
        <meshStandardMaterial color="#cbd5e1" />
      </mesh>
    </group>
  );
}

function Buildings({ buildings }: { buildings: Building[] }) {
  return (
    <group>
      {buildings.map((building) => (
        <BuildingMesh key={building.id} building={building} />
      ))}
    </group>
  );
}

function BuildingMesh({ building }: { building: Building }) {
  const box = useMemo(() => {
    const xs = building.coordinates.map((point) => point.x);
    const zs = building.coordinates.map((point) => point.z);
    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    const minZ = Math.min(...zs);
    const maxZ = Math.max(...zs);

    return {
      x: (minX + maxX) / 2,
      z: (minZ + maxZ) / 2,
      width: Math.max(4, maxX - minX),
      depth: Math.max(4, maxZ - minZ)
    };
  }, [building]);

  const height = clamp(building.height, 4, 95);
  const color = building.kind === "apartments" ? "#9ca3af" : building.kind === "commercial" ? "#64748b" : "#7d8da8";

  return (
    <group position={[box.x, height / 2, box.z]}>
      <mesh castShadow receiveShadow>
        <boxGeometry args={[box.width, height, box.depth]} />
        <meshStandardMaterial color={color} roughness={0.9} />
      </mesh>
      <WindowGrid width={box.width} height={height} depth={box.depth} />
    </group>
  );
}

function WindowGrid({ width, height, depth }: { width: number; height: number; depth: number }) {
  const rows = Math.max(1, Math.floor(height / 6));
  const cols = Math.max(1, Math.floor(width / 5));
  const windows = [];

  for (let row = 0; row < rows; row += 1) {
    for (let col = 0; col < cols; col += 1) {
      windows.push(
        <mesh
          key={`${row}:${col}:front`}
          position={[
            -width / 2 + 3 + col * 5,
            -height / 2 + 4 + row * 6,
            depth / 2 + 0.05
          ]}
        >
          <boxGeometry args={[1.5, 1.7, 0.08]} />
          <meshStandardMaterial color="#dbeafe" emissive="#1d4ed8" emissiveIntensity={0.07} />
        </mesh>
      );
    }
  }

  return <group>{windows}</group>;
}

function Vehicles({ cityMap, state }: { cityMap: CityMap; state: SimulationState }) {
  return (
    <group>
      {state.vehicles.map((vehicle) => {
        const road = cityMap.roads.find((item) => item.id === vehicle.road_id);
        const heading = road ? estimateRoadHeading(road, vehicle.x, vehicle.z) : 0;
        const scale =
          vehicle.kind === "bus"
            ? [5.8, 2.4, 2.2]
            : vehicle.kind === "truck"
              ? [5, 2.4, 2.1]
              : [3.4, 1.5, 1.8];

        return (
          <group key={vehicle.id} position={[vehicle.x, 1.2, vehicle.z]} rotation={[0, -heading, 0]}>
            <mesh castShadow>
              <boxGeometry args={scale as [number, number, number]} />
              <meshStandardMaterial color={vehicle.color} roughness={0.55} />
            </mesh>
            <mesh position={[0.8, 0.35, 0]}>
              <boxGeometry args={[0.9, 0.42, 1.75]} />
              <meshStandardMaterial color="#bfdbfe" />
            </mesh>
          </group>
        );
      })}
    </group>
  );
}

function Pedestrians({ state }: { state: SimulationState }) {
  return (
    <group>
      {state.pedestrians.map((pedestrian, index) => (
        <group
          key={pedestrian.id}
          position={[pedestrian.x, 1.1 + Math.sin(state.tick * 0.35 + index) * 0.08, pedestrian.z]}
        >
          <mesh castShadow position={[0, 0.55, 0]}>
            <capsuleGeometry args={[0.32, 0.9, 6, 10]} />
            <meshStandardMaterial color={pedestrian.color} />
          </mesh>
          <mesh castShadow position={[0, 1.35, 0]}>
            <sphereGeometry args={[0.34, 12, 12]} />
            <meshStandardMaterial color="#f5c7a9" />
          </mesh>
        </group>
      ))}
    </group>
  );
}

function Signals({ cityMap, state }: { cityMap: CityMap; state: SimulationState }) {
  return (
    <group>
      {state.signals.map((signal) => {
        const intersection = cityMap.intersections.find((item) => item.id === signal.intersection_id);
        if (!intersection) return null;

        const color = signal.phase.includes("pedestrian")
          ? "#38bdf8"
          : signal.phase.includes("green") || signal.phase.includes("ai")
            ? "#22c55e"
            : "#f97316";

        return (
          <group key={signal.id} position={[intersection.x, 3, intersection.z]}>
            <mesh castShadow>
              <cylinderGeometry args={[0.25, 0.25, 6, 10]} />
              <meshStandardMaterial color="#111827" />
            </mesh>
            <mesh position={[0, 3.2, 0]} castShadow>
              <boxGeometry args={[1.4, 1.4, 1.4]} />
              <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.35} />
            </mesh>
          </group>
        );
      })}
    </group>
  );
}

function Crossings({ crossings }: { crossings: Crossing[] }) {
  return (
    <group>
      {crossings.map((crossing) => (
        <group key={crossing.id} position={[crossing.x, 0.42, crossing.z]}>
          {Array.from({ length: 5 }).map((_, index) => (
            <mesh key={index} position={[index * 1.4 - 2.8, 0, 0]}>
              <boxGeometry args={[0.7, 0.08, 5]} />
              <meshStandardMaterial color="#f8fafc" />
            </mesh>
          ))}
        </group>
      ))}
    </group>
  );
}

function InfrastructureLayer({ infrastructure }: { infrastructure: Infrastructure[] }) {
  return (
    <group>
      {infrastructure.map((item) => (
        <group key={item.id} position={[item.x, 1.5, item.z]}>
          <mesh castShadow>
            <cylinderGeometry args={[1.2, 1.2, 3, 6]} />
            <meshStandardMaterial color={infrastructureColor(item.kind)} />
          </mesh>
        </group>
      ))}
    </group>
  );
}

function Intersections({ cityMap }: { cityMap: CityMap }) {
  return (
    <group>
      {cityMap.intersections.map((intersection) => (
        <mesh key={intersection.id} position={[intersection.x, 0.5, intersection.z]}>
          <cylinderGeometry args={[2.8, 2.8, 0.25, 24]} />
          <meshStandardMaterial color={intersection.has_signal ? "#22c55e" : "#64748b"} />
        </mesh>
      ))}
    </group>
  );
}

function infrastructureColor(kind: string) {
  if (kind.includes("school")) return "#facc15";
  if (kind.includes("hospital")) return "#ef4444";
  if (kind.includes("shop")) return "#a855f7";
  if (kind.includes("public_transport")) return "#38bdf8";
  if (kind.includes("park")) return "#22c55e";
  return "#94a3b8";
}

function estimateRoadHeading(road: Road, x: number, z: number): number {
  let bestStart = road.coordinates[0];
  let bestEnd = road.coordinates[road.coordinates.length - 1];
  let bestDistance = Number.POSITIVE_INFINITY;

  for (let index = 1; index < road.coordinates.length; index += 1) {
    const start = road.coordinates[index - 1];
    const end = road.coordinates[index];
    const midX = (start.x + end.x) / 2;
    const midZ = (start.z + end.z) / 2;
    const distance = Math.hypot(x - midX, z - midZ);

    if (distance < bestDistance) {
      bestDistance = distance;
      bestStart = start;
      bestEnd = end;
    }
  }

  return Math.atan2(bestEnd.z - bestStart.z, bestEnd.x - bestStart.x);
}