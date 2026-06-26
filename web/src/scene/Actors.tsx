import { useRef, type ReactNode } from "react";
import { useFrame } from "@react-three/fiber";
import type { PedestrianState, VehicleState } from "../types/domain";

const SKIN_COLORS = [
  "#f3c7a6",
  "#e7ad7f",
  "#c98252",
  "#9f6042",
  "#70412f",
  "#4b2c22"
];

const CLOTHING_COLORS = [
  "#38bdf8",
  "#22c55e",
  "#ef4444",
  "#facc15",
  "#a855f7",
  "#f97316",
  "#14b8a6",
  "#e879f9",
  "#f8fafc",
  "#64748b"
];

const CAR_COLORS = [
  "#e5e7eb",
  "#94a3b8",
  "#ef4444",
  "#2563eb",
  "#16a34a",
  "#7c3aed",
  "#f97316",
  "#0f172a",
  "#f8fafc",
  "#0891b2",
  "#be123c"
];

const WINDOW_COLOR = "#bfdbfe";
const TIRE_COLOR = "#020617";
const RIM_COLOR = "#94a3b8";
const LIGHT_COLOR = "#f8fafc";
const TAIL_LIGHT_COLOR = "#ef4444";
const TAXI_YELLOW = "#facc15";
const BUS_BODY_COLOR = "#2563eb";

const TRAM_RED = "#dc2626";
const TRAM_DARK_RED = "#991b1b";

type VehicleActorProps = {
  vehicle: VehicleState;
  x: number;
  z: number;
  heading: number;
  yOffset?: number;
  simple?: boolean;
};

type PedestrianActorProps = {
  pedestrian: PedestrianState;
  x: number;
  z: number;
  heading: number;
  bob: number;
  simple?: boolean;
  yOffset?: number;
};

export function VehicleActor({ vehicle, x, z, heading, yOffset = 0, simple = false }: VehicleActorProps) {
  const kind = vehicle.kind.toLowerCase();
  const length = Math.max(2.8, vehicle.length_m);
  const width = Math.max(1.4, vehicle.width_m);
  const color = vehicle.color || pickCarColor(vehicle.id);

  if (simple) {
    return (
      <SmoothActorRoot x={x} y={0.92 + yOffset} z={z} heading={heading}>
        <SimpleVehicle
          length={length}
          width={width}
          color={simpleVehicleColor(vehicle, color)}
        />
      </SmoothActorRoot>
    );
  }

  if (kind.includes("bus")) {
    return (
      <SmoothActorRoot x={x} y={1.95 + yOffset} z={z} heading={heading}>
        <BusVehicle length={Math.max(length, 8.8)} width={Math.max(width, 2.35)} />
      </SmoothActorRoot>
    );
  }

  if (kind.includes("truck") || kind.includes("lorry")) {
    return (
      <SmoothActorRoot x={x} y={1.78 + yOffset} z={z} heading={heading}>
        <TruckVehicle
          length={Math.max(length, 7.6)}
          width={Math.max(width, 2.25)}
          bodyColor={color}
        />
      </SmoothActorRoot>
    );
  }

  if (kind.includes("tram")) {
    return (
      <SmoothActorRoot x={x} y={1.86 + yOffset} z={z} heading={heading}>
        <TramVehicle length={Math.max(length, 11.5)} width={Math.max(width, 2.35)} />
      </SmoothActorRoot>
    );
  }

  if (kind.includes("taxi")) {
    return (
      <SmoothActorRoot x={x} y={1.34 + yOffset} z={z} heading={heading}>
        <SedanVehicle
          length={Math.max(length, 4.35)}
          width={Math.max(width, 1.78)}
          bodyColor={TAXI_YELLOW}
          taxi
        />
      </SmoothActorRoot>
    );
  }

  if (kind.includes("suv") || kind.includes("jeep")) {
    return (
      <SmoothActorRoot x={x} y={1.52 + yOffset} z={z} heading={heading}>
        <SuvVehicle
          length={Math.max(length, 5.05)}
          width={Math.max(width, 2.0)}
          bodyColor={color}
        />
      </SmoothActorRoot>
    );
  }

  const variant = deterministicIndex(vehicle.id, 5);

  return (
    <SmoothActorRoot x={x} y={1.32 + yOffset} z={z} heading={heading}>
      {variant === 0 && (
        <SedanVehicle
          length={Math.max(length, 4.35)}
          width={Math.max(width, 1.76)}
          bodyColor={color}
        />
      )}

      {variant === 1 && (
        <CompactSedanVehicle
          length={Math.max(length, 4.0)}
          width={Math.max(width, 1.68)}
          bodyColor={color}
        />
      )}

      {variant === 2 && (
        <CoupeVehicle
          length={Math.max(length, 3.65)}
          width={Math.max(width, 1.62)}
          bodyColor={color}
        />
      )}

      {variant === 3 && (
        <HatchbackVehicle
          length={Math.max(length, 3.85)}
          width={Math.max(width, 1.68)}
          bodyColor={color}
        />
      )}

      {variant === 4 && (
        <SuvVehicle
          length={Math.max(length, 4.75)}
          width={Math.max(width, 1.92)}
          bodyColor={color}
          compact
        />
      )}
    </SmoothActorRoot>
  );
}

function SmoothActorRoot({
  x,
  y,
  z,
  heading,
  children
}: {
  x: number;
  y: number;
  z: number;
  heading: number;
  children: ReactNode;
}) {
  const groupRef = useRef<any>(null);
  const initializedRef = useRef(false);

  useFrame((_, delta) => {
    const group = groupRef.current;

    if (!group) {
      return;
    }

    const targetRotationY = -heading;

    if (!initializedRef.current) {
      group.position.set(x, y, z);
      group.rotation.y = targetRotationY;
      initializedRef.current = true;
      return;
    }

    const positionT = 1 - Math.exp(-delta * 12);
    const rotationT = 1 - Math.exp(-delta * 16);

    group.position.x += (x - group.position.x) * positionT;
    group.position.y += (y - group.position.y) * positionT;
    group.position.z += (z - group.position.z) * positionT;

    const angleDelta = shortestAngleDelta(group.rotation.y, targetRotationY);
    group.rotation.y += angleDelta * rotationT;
  });

  return <group ref={groupRef}>{children}</group>;
}

function shortestAngleDelta(current: number, target: number) {
  return Math.atan2(Math.sin(target - current), Math.cos(target - current));
}

function SedanVehicle({
  length,
  width,
  bodyColor,
  taxi = false
}: {
  length: number;
  width: number;
  bodyColor: string;
  taxi?: boolean;
}) {
  return (
    <group>
      <VehicleBase length={length} width={width} height={0.46} bodyColor={bodyColor} />

      <mesh position={[length * 0.3, 0.08, 0]} castShadow renderOrder={41}>
        <boxGeometry args={[length * 0.24, 0.32, width * 0.94]} />
        <meshStandardMaterial color={bodyColor} roughness={0.54} />
      </mesh>

      <mesh position={[-length * 0.34, 0.08, 0]} castShadow renderOrder={41}>
        <boxGeometry args={[length * 0.18, 0.28, width * 0.92]} />
        <meshStandardMaterial color={bodyColor} roughness={0.54} />
      </mesh>

      <mesh position={[-length * 0.04, 0.46, 0]} castShadow renderOrder={42}>
        <boxGeometry args={[length * 0.36, 0.58, width * 0.78]} />
        <meshStandardMaterial color={WINDOW_COLOR} roughness={0.3} />
      </mesh>

      <mesh position={[length * 0.16, 0.53, 0]} castShadow renderOrder={43}>
        <boxGeometry args={[length * 0.17, 0.42, width * 0.74]} />
        <meshStandardMaterial color={bodyColor} roughness={0.54} />
      </mesh>

      {taxi && <TaxiSign length={length} />}

      <InsetVehicleLights length={length} width={width} frontY={0.03} rearY={0.02} />
      <VehicleWheels length={length} width={width} wheelRadius={0.28} wheelY={-0.43} />
    </group>
  );
}

function CompactSedanVehicle({
  length,
  width,
  bodyColor
}: {
  length: number;
  width: number;
  bodyColor: string;
}) {
  return (
    <group>
      <VehicleBase length={length} width={width} height={0.44} bodyColor={bodyColor} />

      <mesh position={[length * 0.28, 0.08, 0]} castShadow renderOrder={41}>
        <boxGeometry args={[length * 0.22, 0.28, width * 0.92]} />
        <meshStandardMaterial color={bodyColor} roughness={0.54} />
      </mesh>

      <mesh position={[-length * 0.3, 0.06, 0]} castShadow renderOrder={41}>
        <boxGeometry args={[length * 0.14, 0.24, width * 0.9]} />
        <meshStandardMaterial color={bodyColor} roughness={0.54} />
      </mesh>

      <mesh position={[-length * 0.03, 0.44, 0]} castShadow renderOrder={42}>
        <boxGeometry args={[length * 0.34, 0.52, width * 0.76]} />
        <meshStandardMaterial color={WINDOW_COLOR} roughness={0.3} />
      </mesh>

      <InsetVehicleLights length={length} width={width} frontY={0.02} rearY={0.02} />
      <VehicleWheels length={length} width={width} wheelRadius={0.25} wheelY={-0.41} />
    </group>
  );
}

function CoupeVehicle({
  length,
  width,
  bodyColor
}: {
  length: number;
  width: number;
  bodyColor: string;
}) {
  return (
    <group>
      <VehicleBase length={length} width={width} height={0.4} bodyColor={bodyColor} />

      <mesh position={[length * 0.3, 0.06, 0]} castShadow renderOrder={41}>
        <boxGeometry args={[length * 0.28, 0.22, width * 0.9]} />
        <meshStandardMaterial color={bodyColor} roughness={0.5} />
      </mesh>

      <mesh position={[length * 0.02, 0.38, 0]} castShadow renderOrder={42}>
        <boxGeometry args={[length * 0.3, 0.46, width * 0.7]} />
        <meshStandardMaterial color={WINDOW_COLOR} roughness={0.28} />
      </mesh>

      <mesh position={[-length * 0.18, 0.34, 0]} castShadow renderOrder={43}>
        <boxGeometry args={[length * 0.14, 0.32, width * 0.68]} />
        <meshStandardMaterial color={bodyColor} roughness={0.5} />
      </mesh>

      <InsetVehicleLights length={length} width={width} frontY={0} rearY={0} />
      <VehicleWheels length={length} width={width} wheelRadius={0.24} wheelY={-0.39} />
    </group>
  );
}

function HatchbackVehicle({
  length,
  width,
  bodyColor
}: {
  length: number;
  width: number;
  bodyColor: string;
}) {
  return (
    <group>
      <VehicleBase length={length} width={width} height={0.48} bodyColor={bodyColor} />

      <mesh position={[length * 0.26, 0.07, 0]} castShadow renderOrder={41}>
        <boxGeometry args={[length * 0.18, 0.28, width * 0.92]} />
        <meshStandardMaterial color={bodyColor} roughness={0.54} />
      </mesh>

      <mesh position={[-length * 0.09, 0.46, 0]} castShadow renderOrder={42}>
        <boxGeometry args={[length * 0.38, 0.58, width * 0.78]} />
        <meshStandardMaterial color={WINDOW_COLOR} roughness={0.32} />
      </mesh>

      <mesh position={[-length * 0.29, 0.3, 0]} castShadow renderOrder={43}>
        <boxGeometry args={[length * 0.08, 0.42, width * 0.76]} />
        <meshStandardMaterial color={bodyColor} roughness={0.54} />
      </mesh>

      <InsetVehicleLights length={length} width={width} frontY={0.02} rearY={0.03} />
      <VehicleWheels length={length} width={width} wheelRadius={0.25} wheelY={-0.42} />
    </group>
  );
}

function SuvVehicle({
  length,
  width,
  bodyColor,
  compact = false
}: {
  length: number;
  width: number;
  bodyColor: string;
  compact?: boolean;
}) {
  const height = compact ? 0.64 : 0.76;
  const wheelRadius = compact ? 0.31 : 0.36;

  return (
    <group>
      <VehicleBase length={length} width={width} height={height} bodyColor={bodyColor} />

      <mesh position={[length * 0.3, 0.1, 0]} castShadow renderOrder={41}>
        <boxGeometry args={[length * 0.24, 0.36, width * 0.96]} />
        <meshStandardMaterial color={bodyColor} roughness={0.62} />
      </mesh>

      <mesh position={[-length * 0.06, 0.58, 0]} castShadow renderOrder={42}>
        <boxGeometry args={[length * 0.42, compact ? 0.62 : 0.72, width * 0.82]} />
        <meshStandardMaterial color={WINDOW_COLOR} roughness={0.34} />
      </mesh>

      <mesh position={[-length * 0.32, 0.42, 0]} castShadow renderOrder={43}>
        <boxGeometry args={[length * 0.14, compact ? 0.45 : 0.55, width * 0.8]} />
        <meshStandardMaterial color={bodyColor} roughness={0.62} />
      </mesh>

      <InsetVehicleLights length={length} width={width} frontY={0.06} rearY={0.06} />
      <VehicleWheels length={length} width={width} wheelRadius={wheelRadius} wheelY={-0.46} />
    </group>
  );
}

function TramVehicle({ length, width }: { length: number; width: number }) {
  const sectionLength = length / 3;

  return (
    <group>
      <mesh castShadow renderOrder={40}>
        <boxGeometry args={[length, 1.52, width]} />
        <meshStandardMaterial color={TRAM_RED} roughness={0.56} />
      </mesh>

      <mesh position={[0, 0.82, 0]} castShadow renderOrder={41}>
        <boxGeometry args={[length * 0.94, 0.16, width * 0.92]} />
        <meshStandardMaterial color={TRAM_DARK_RED} roughness={0.62} />
      </mesh>

      {[-1, 0, 1].map((section) => (
        <group key={section} position={[section * sectionLength * 0.92, 0, 0]}>
          <mesh position={[0, 0.36, width * 0.505]} castShadow renderOrder={42}>
            <boxGeometry args={[sectionLength * 0.55, 0.5, 0.075]} />
            <meshStandardMaterial color={WINDOW_COLOR} roughness={0.3} />
          </mesh>

          <mesh position={[0, 0.36, -width * 0.505]} castShadow renderOrder={42}>
            <boxGeometry args={[sectionLength * 0.55, 0.5, 0.075]} />
            <meshStandardMaterial color={WINDOW_COLOR} roughness={0.3} />
          </mesh>
        </group>
      ))}

      <mesh position={[length * 0.47, 0.18, 0]} castShadow renderOrder={43}>
        <boxGeometry args={[0.12, 0.78, width * 0.82]} />
        <meshStandardMaterial color={WINDOW_COLOR} roughness={0.3} />
      </mesh>

      <mesh position={[-length * 0.47, 0.18, 0]} castShadow renderOrder={43}>
        <boxGeometry args={[0.12, 0.78, width * 0.82]} />
        <meshStandardMaterial color={WINDOW_COLOR} roughness={0.3} />
      </mesh>

      <mesh position={[0, -0.78, 0]} castShadow renderOrder={39}>
        <boxGeometry args={[length * 0.92, 0.24, width * 0.72]} />
        <meshStandardMaterial color="#1e293b" roughness={0.78} />
      </mesh>

      <InsetVehicleLights length={length} width={width} frontY={-0.28} rearY={-0.28} />
      <VehicleWheels length={length} width={width} wheelRadius={0.36} wheelY={-0.92} sixWheels />
    </group>
  );
}

function BusVehicle({ length, width }: { length: number; width: number }) {
  return (
    <group>
      <mesh castShadow renderOrder={40}>
        <boxGeometry args={[length, 1.68, width]} />
        <meshStandardMaterial color={BUS_BODY_COLOR} roughness={0.58} />
      </mesh>

      <mesh position={[length * 0.43, 0.12, 0]} castShadow renderOrder={41}>
        <boxGeometry args={[length * 0.1, 1.1, width * 0.92]} />
        <meshStandardMaterial color={WINDOW_COLOR} roughness={0.32} />
      </mesh>

      {[-0.34, -0.16, 0.02, 0.2].map((offset, index) => (
        <mesh key={`bus-window-left:${index}`} position={[length * offset, 0.38, width * 0.505]} castShadow renderOrder={42}>
          <boxGeometry args={[length * 0.12, 0.5, 0.075]} />
          <meshStandardMaterial color={WINDOW_COLOR} roughness={0.32} />
        </mesh>
      ))}

      {[-0.34, -0.16, 0.02, 0.2].map((offset, index) => (
        <mesh key={`bus-window-right:${index}`} position={[length * offset, 0.38, -width * 0.505]} castShadow renderOrder={42}>
          <boxGeometry args={[length * 0.12, 0.5, 0.075]} />
          <meshStandardMaterial color={WINDOW_COLOR} roughness={0.32} />
        </mesh>
      ))}

      <mesh position={[-length * 0.14, -0.24, width * 0.51]} castShadow renderOrder={43}>
        <boxGeometry args={[length * 0.14, 0.74, 0.08]} />
        <meshStandardMaterial color="#854d0e" roughness={0.5} />
      </mesh>

      <InsetVehicleLights length={length} width={width} frontY={-0.28} rearY={-0.28} />
      <VehicleWheels length={length} width={width} wheelRadius={0.42} wheelY={-0.88} />
    </group>
  );
}

function TruckVehicle({
  length,
  width,
  bodyColor
}: {
  length: number;
  width: number;
  bodyColor: string;
}) {
  const cargoColor = pickCargoColor(bodyColor);

  return (
    <group>
      <mesh position={[0, -0.54, 0]} castShadow renderOrder={39}>
        <boxGeometry args={[length * 0.95, 0.22, width * 0.9]} />
        <meshStandardMaterial color="#1e293b" roughness={0.78} />
      </mesh>

      <mesh position={[length * 0.13, 0.08, 0]} castShadow renderOrder={40}>
        <boxGeometry args={[length * 0.66, 1.42, width]} />
        <meshStandardMaterial color={cargoColor} roughness={0.76} />
      </mesh>

      <mesh position={[-length * 0.35, -0.03, 0]} castShadow renderOrder={41}>
        <boxGeometry args={[length * 0.28, 1.2, width * 0.98]} />
        <meshStandardMaterial color={bodyColor} roughness={0.58} />
      </mesh>

      <mesh position={[-length * 0.42, 0.34, 0]} castShadow renderOrder={42}>
        <boxGeometry args={[length * 0.1, 0.44, width * 0.76]} />
        <meshStandardMaterial color={WINDOW_COLOR} roughness={0.32} />
      </mesh>

      <mesh position={[-length * 0.24, -0.22, 0]} castShadow renderOrder={42}>
        <boxGeometry args={[length * 0.08, 0.56, width * 0.92]} />
        <meshStandardMaterial color="#334155" roughness={0.7} />
      </mesh>

      <mesh position={[length * 0.13, 0.85, 0]} castShadow renderOrder={42}>
        <boxGeometry args={[length * 0.62, 0.1, width * 0.94]} />
        <meshStandardMaterial color="#cbd5e1" roughness={0.72} />
      </mesh>

      <InsetVehicleLights length={length} width={width} frontY={-0.34} rearY={-0.28} />
      <VehicleWheels length={length} width={width} wheelRadius={0.42} wheelY={-0.9} sixWheels />
    </group>
  );
}

function VehicleBase({
  length,
  width,
  height,
  bodyColor
}: {
  length: number;
  width: number;
  height: number;
  bodyColor: string;
}) {
  return (
    <mesh castShadow renderOrder={40}>
      <boxGeometry args={[length * 0.82, height, width]} />
      <meshStandardMaterial color={bodyColor} roughness={0.54} />
    </mesh>
  );
}

function TaxiSign({ length }: { length: number }) {
  return (
    <mesh position={[-length * 0.02, 0.84, 0]} castShadow renderOrder={44}>
      <boxGeometry args={[0.66, 0.2, 0.54]} />
      <meshStandardMaterial color="#fef3c7" emissive="#facc15" emissiveIntensity={0.35} roughness={0.45} />
    </mesh>
  );
}

function InsetVehicleLights({
  length,
  width,
  frontY,
  rearY
}: {
  length: number;
  width: number;
  frontY: number;
  rearY: number;
}) {
  return (
    <group>
      <mesh position={[length * 0.412, frontY, width * 0.27]} renderOrder={45}>
        <boxGeometry args={[0.04, 0.12, width * 0.16]} />
        <meshStandardMaterial color={LIGHT_COLOR} emissive={LIGHT_COLOR} emissiveIntensity={0.42} />
      </mesh>

      <mesh position={[length * 0.412, frontY, -width * 0.27]} renderOrder={45}>
        <boxGeometry args={[0.04, 0.12, width * 0.16]} />
        <meshStandardMaterial color={LIGHT_COLOR} emissive={LIGHT_COLOR} emissiveIntensity={0.42} />
      </mesh>

      <mesh position={[-length * 0.412, rearY, width * 0.29]} renderOrder={45}>
        <boxGeometry args={[0.04, 0.12, width * 0.14]} />
        <meshStandardMaterial color={TAIL_LIGHT_COLOR} emissive={TAIL_LIGHT_COLOR} emissiveIntensity={0.36} />
      </mesh>

      <mesh position={[-length * 0.412, rearY, -width * 0.29]} renderOrder={45}>
        <boxGeometry args={[0.04, 0.12, width * 0.14]} />
        <meshStandardMaterial color={TAIL_LIGHT_COLOR} emissive={TAIL_LIGHT_COLOR} emissiveIntensity={0.36} />
      </mesh>
    </group>
  );
}

function VehicleWheels({
  length,
  width,
  wheelRadius,
  wheelY,
  sixWheels = false
}: {
  length: number;
  width: number;
  wheelRadius: number;
  wheelY: number;
  sixWheels?: boolean;
}) {
  const wheelX = sixWheels
    ? [-length * 0.34, length * 0.08, length * 0.34]
    : [-length * 0.31, length * 0.31];

  return (
    <group>
      {wheelX.flatMap((x) => [
        <group key={`${x}:left`} position={[x, wheelY, width * 0.515]} rotation={[Math.PI / 2, 0, 0]}>
          <mesh castShadow renderOrder={46}>
            <cylinderGeometry args={[wheelRadius, wheelRadius, 0.2, 14]} />
            <meshStandardMaterial color={TIRE_COLOR} roughness={0.88} />
          </mesh>
          <mesh position={[0, 0, 0.105]} renderOrder={47}>
            <cylinderGeometry args={[wheelRadius * 0.48, wheelRadius * 0.48, 0.025, 12]} />
            <meshStandardMaterial color={RIM_COLOR} roughness={0.62} />
          </mesh>
        </group>,
        <group key={`${x}:right`} position={[x, wheelY, -width * 0.515]} rotation={[Math.PI / 2, 0, 0]}>
          <mesh castShadow renderOrder={46}>
            <cylinderGeometry args={[wheelRadius, wheelRadius, 0.2, 14]} />
            <meshStandardMaterial color={TIRE_COLOR} roughness={0.88} />
          </mesh>
          <mesh position={[0, 0, -0.105]} renderOrder={47}>
            <cylinderGeometry args={[wheelRadius * 0.48, wheelRadius * 0.48, 0.025, 12]} />
            <meshStandardMaterial color={RIM_COLOR} roughness={0.62} />
          </mesh>
        </group>
      ])}
    </group>
  );
}

function SimpleVehicle({
  length,
  width,
  color
}: {
  length: number;
  width: number;
  color: string;
}) {
  return (
    <group>
      <mesh castShadow renderOrder={48}>
        <boxGeometry args={[length, 0.5, width]} />
        <meshStandardMaterial color={color} roughness={0.72} />
      </mesh>

      <mesh position={[length * 0.42, 0.03, 0]} renderOrder={49}>
        <boxGeometry args={[0.18, 0.56, width * 0.72]} />
        <meshStandardMaterial color="#f8fafc" emissive="#f8fafc" emissiveIntensity={0.18} roughness={0.45} />
      </mesh>
    </group>
  );
}

function SimplePedestrian({ color }: { color: string }) {
  return (
    <mesh castShadow renderOrder={50} rotation={[-Math.PI / 2, 0, 0]}>
      <circleGeometry args={[0.34, 16]} />
      <meshStandardMaterial color={color} roughness={0.66} />
    </mesh>
  );
}

function simpleVehicleColor(vehicle: VehicleState, fallbackColor: string) {
  const kind = vehicle.kind.toLowerCase();

  if (kind.includes("tram")) return "#dc2626";
  if (kind.includes("bus")) return "#2563eb";
  if (kind.includes("truck")) return "#64748b";
  if (kind.includes("taxi")) return TAXI_YELLOW;

  return fallbackColor;
}

export function PedestrianActor({ pedestrian, x, z, heading, bob, simple = false, yOffset = 0 }: PedestrianActorProps) {
  const skinColor = SKIN_COLORS[deterministicIndex(pedestrian.id, SKIN_COLORS.length)];
  const clothingColor = CLOTHING_COLORS[deterministicIndex(`${pedestrian.id}:clothes`, CLOTHING_COLORS.length)];

  if (simple) {
    return (
      <SmoothActorRoot x={x} y={0.42 + yOffset} z={z} heading={heading}>
        <SimplePedestrian color={skinColor} />
      </SmoothActorRoot>
    );
  }

  return (
    <SmoothActorRoot x={x} y={0.92 + yOffset + bob} z={z} heading={heading}>
      <mesh castShadow position={[0, 0.36, 0]} renderOrder={42}>
        <coneGeometry args={[0.32, 0.86, 12]} />
        <meshStandardMaterial color={clothingColor} roughness={0.64} />
      </mesh>

      <mesh castShadow position={[0, 0.98, 0]} renderOrder={43}>
        <sphereGeometry args={[0.24, 12, 12]} />
        <meshStandardMaterial color={skinColor} roughness={0.72} />
      </mesh>
    </SmoothActorRoot>
  );
}

function pickCarColor(id: string) {
  return CAR_COLORS[deterministicIndex(id, CAR_COLORS.length)];
}

function pickCargoColor(bodyColor: string) {
  if (bodyColor === "#0f172a") return "#64748b";
  if (bodyColor === "#e5e7eb" || bodyColor === "#f8fafc") return "#475569";
  if (bodyColor === "#94a3b8") return "#334155";

  return "#cbd5e1";
}

function deterministicIndex(value: string, length: number) {
  let hash = 0;

  for (let index = 0; index < value.length; index += 1) {
    hash = (hash * 31 + value.charCodeAt(index)) | 0;
  }

  return Math.abs(hash) % length;
}