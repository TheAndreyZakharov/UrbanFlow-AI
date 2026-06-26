import { OrbitControls } from "@react-three/drei";
import { Canvas, type ThreeEvent, useFrame, useThree } from "@react-three/fiber";
import { useEffect, useMemo, useRef } from "react";
import * as THREE from "three";
import type {
  Building,
  CityMap,
  Coordinate,
  Crossing,
  Road,
  RailLine,
  RoadLoad,
  SimulationState,
  Surface,
  TrafficEvent,
  TransitStop
} from "../types/domain";
import { PedestrianActor, VehicleActor } from "./Actors";
import { clamp } from "../utils/format";
import type { SceneSettings } from "../types/scene";

type EditorTool = "close_road" | "open_road" | "roadwork" | "accident" | null;

type RoadPickPoint = {
  progress: number;
  x: number;
  z: number;
};

type Props = {
  cityMap: CityMap | null;
  state: SimulationState | null;
  settings?: SceneSettings;
  editorTool?: EditorTool;
  onRoadPick?: (road: Road, point: RoadPickPoint) => void;
  onRoadHover?: (road: Road | null) => void;
};

const DEFAULT_SCENE_SETTINGS: SceneSettings = {
  showBuildings: false,
  showSpecialZones: false,
  highlightRoadAccess: false,
  highlightRoadCongestion: false,
  showGroundZones: false,
  enableShadows: false,
  highDpr: false,
  logarithmicDepthBuffer: false,
  fineGeometryDetails: false,
  simpleActors: true
};

const GROUND_Y = -0.28;
const WATER_Y = 0.12;
const LAND_ZONE_Y = 0.16;
const SPECIAL_ZONE_Y = 0.2;
const ROAD_Y = 0.34;
const ROAD_MARKING_Y = 0.53;
const VEHICLE_SURFACE_LIFT = 0.72;
const PEDESTRIAN_SURFACE_LIFT = 0.38;
const CROSSING_Y = 0.66;
const INTERSECTION_Y = 0.62;
const BUILDING_BASE_Y = 0.26;
const LAYER_HEIGHT_M = 7.0;
const TUNNEL_VISUAL_DEPTH_M = 3.4;
const RAIL_SLEEPER_SPACING_M = 2.2;
const ROAD_JOINT_HEIGHT = 0.3;
const RAIL_JOINT_HEIGHT = 0.12;

type SceneStats = {
  maxExtent: number;
  groundSize: number;
  cameraHeight: number;
  cameraDistance: number;
  maxCameraDistance: number;
  cameraFar: number;
  fogNear: number;
  fogFar: number;
  minX: number;
  maxX: number;
  minZ: number;
  maxZ: number;
  panPadding: number;
};

export function CityScene({
  cityMap,
  state,
  settings = DEFAULT_SCENE_SETTINGS,
  editorTool = null,
  onRoadPick,
  onRoadHover
}: Props) {
  const sceneStats = useMemo(() => getSceneStats(cityMap), [cityMap]);

  return (
    <div className={["city-scene", editorTool ? "editor-pick-active" : ""].join(" ")}>
      <Canvas
        key={`scene:${settings.logarithmicDepthBuffer ? "log-depth" : "normal-depth"}`}
        shadows={settings.enableShadows}
        dpr={settings.highDpr ? [1, 2] : 1}
        camera={{
          position: [0, sceneStats.cameraHeight, sceneStats.cameraDistance],
          fov: 45,
          near: 0.1,
          far: sceneStats.cameraFar
        }}
        gl={{
          antialias: true,
          powerPreference: "high-performance",
          logarithmicDepthBuffer: settings.logarithmicDepthBuffer
        }}
      >
        <SceneCamera stats={sceneStats} settings={settings} />

        <color attach="background" args={["#070b12"]} />
        <ambientLight intensity={0.78} />

        <directionalLight
          position={[-sceneStats.maxExtent * 0.55, sceneStats.maxExtent * 1.45, sceneStats.maxExtent * 0.55]}
          intensity={1.6}
          castShadow={settings.enableShadows}
          shadow-mapSize={settings.enableShadows ? [2048, 2048] : [256, 256]}
          shadow-camera-left={-sceneStats.maxExtent * 1.4}
          shadow-camera-right={sceneStats.maxExtent * 1.4}
          shadow-camera-top={sceneStats.maxExtent * 1.4}
          shadow-camera-bottom={-sceneStats.maxExtent * 1.4}
          shadow-camera-near={1}
          shadow-camera-far={sceneStats.maxExtent * 4}
        />

        <fog attach="fog" args={["#070b12", sceneStats.fogNear, sceneStats.fogFar]} />

        <Ground size={sceneStats.groundSize} enableShadows={settings.enableShadows} />

        {cityMap && (
          <group>
            <Surfaces surfaces={cityMap.surfaces ?? []} settings={settings} />
            <Roads
              roads={cityMap.roads}
              roadLoad={state?.road_load ?? []}
              settings={settings}
              events={state?.events ?? []}
              closedRoadIds={state?.closed_road_ids ?? []}
              forcedOpenRoadIds={state?.forced_open_road_ids ?? []}
              editorTool={editorTool}
              onRoadPick={onRoadPick}
              onRoadHover={onRoadHover}
            />
            {settings.showBuildings && <Buildings buildings={cityMap.buildings} />}
            <Crossings crossings={cityMap.crossings} roads={cityMap.roads} settings={settings} />
            <Intersections cityMap={cityMap} state={state} />
            <RailLines railLines={cityMap.rail_lines ?? []} settings={settings} />
            <TransitStops stops={cityMap.transit_stops ?? []} />
            <EventMarkers events={state?.events ?? []} roads={cityMap.roads} />
          </group>
        )}

        {state && cityMap && (
          <group>
            <Vehicles state={state} simpleActors={settings.simpleActors} />
            <Pedestrians state={state} simpleActors={settings.simpleActors} />
            <Signals cityMap={cityMap} state={state} />
          </group>
        )}

        <BoundedOrbitControls stats={sceneStats} />
      </Canvas>
    </div>
  );
}

function SceneCamera({ stats, settings }: { stats: SceneStats; settings: SceneSettings }) {
  const { camera, gl } = useThree();

  useEffect(() => {
    camera.near = 0.1;
    camera.far = stats.cameraFar;
    camera.position.set(0, stats.cameraHeight, stats.cameraDistance);
    camera.lookAt(0, 0, 0);
    camera.updateProjectionMatrix();

    gl.setPixelRatio(settings.highDpr ? Math.min(window.devicePixelRatio, 2) : 1);
  }, [camera, gl, stats, settings.highDpr]);

  return null;
}

function BoundedOrbitControls({ stats }: { stats: SceneStats }) {
  const controlsRef = useRef<any>(null);
  const isClampingRef = useRef(false);
  const pressedKeysRef = useRef<Set<string>>(new Set());
  const { camera } = useThree();

  function clampControls() {
    const controls = controlsRef.current;

    if (!controls || isClampingRef.current) {
      return;
    }

    isClampingRef.current = true;

    const minX = stats.minX - stats.panPadding;
    const maxX = stats.maxX + stats.panPadding;
    const minZ = stats.minZ - stats.panPadding;
    const maxZ = stats.maxZ + stats.panPadding;

    const previousCameraX = camera.position.x;
    const previousCameraZ = camera.position.z;
    const previousTargetX = controls.target.x;
    const previousTargetZ = controls.target.z;

    camera.position.x = clampNumber(camera.position.x, minX, maxX);
    camera.position.z = clampNumber(camera.position.z, minZ, maxZ);

    const cameraDeltaX = camera.position.x - previousCameraX;
    const cameraDeltaZ = camera.position.z - previousCameraZ;

    controls.target.x = clampNumber(previousTargetX + cameraDeltaX, minX, maxX);
    controls.target.z = clampNumber(previousTargetZ + cameraDeltaZ, minZ, maxZ);

    camera.position.y = clampNumber(camera.position.y, 6, stats.maxCameraDistance);
    controls.target.y = clampNumber(controls.target.y, -120, stats.maxCameraDistance);

    controls.update();

    isClampingRef.current = false;
  }

  useEffect(() => {
    function shouldIgnoreKeyboardEvent(event: KeyboardEvent) {
      const target = event.target;

      if (!(target instanceof HTMLElement)) {
        return false;
      }

      return (
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.tagName === "SELECT" ||
        target.isContentEditable
      );
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (shouldIgnoreKeyboardEvent(event)) {
        return;
      }

      if (isFlightKey(event.code)) {
        event.preventDefault();
        pressedKeysRef.current.add(event.code);
      }
    }

    function handleKeyUp(event: KeyboardEvent) {
      if (isFlightKey(event.code)) {
        event.preventDefault();
        pressedKeysRef.current.delete(event.code);
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("keyup", handleKeyUp);
    window.addEventListener("blur", clearFlightKeys);

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("keyup", handleKeyUp);
      window.removeEventListener("blur", clearFlightKeys);
    };
  }, []);

  function clearFlightKeys() {
    pressedKeysRef.current.clear();
  }

  useFrame((_, delta) => {
    const controls = controlsRef.current;

    if (!controls) {
      return;
    }

    const pressedKeys = pressedKeysRef.current;

    if (pressedKeys.size === 0) {
      return;
    }

    const forwardAmount =
      (pressedKeys.has("KeyW") ? 1 : 0) -
      (pressedKeys.has("KeyS") ? 1 : 0);

    const rightAmount =
      (pressedKeys.has("KeyD") ? 1 : 0) -
      (pressedKeys.has("KeyA") ? 1 : 0);

    const verticalAmount =
      (pressedKeys.has("Space") ? 1 : 0) -
      (pressedKeys.has("ShiftLeft") || pressedKeys.has("ShiftRight") ? 1 : 0);

    if (forwardAmount === 0 && rightAmount === 0 && verticalAmount === 0) {
      return;
    }

    const forward = new THREE.Vector3();
    camera.getWorldDirection(forward);
    forward.normalize();

    const right = new THREE.Vector3();
    right.crossVectors(forward, camera.up).normalize();

    const movement = new THREE.Vector3();

    movement.addScaledVector(forward, forwardAmount);
    movement.addScaledVector(right, rightAmount);
    movement.y += verticalAmount;

    if (movement.lengthSq() <= 0.0001) {
      return;
    }

    movement.normalize();

    const speed = keyboardFlightSpeed(stats);
    const distance = speed * delta;

    movement.multiplyScalar(distance);

    camera.position.add(movement);
    controls.target.add(movement);

    clampControls();
  });

  useEffect(() => {
    clampControls();
  }, [stats]);

  return (
    <OrbitControls
      ref={controlsRef}
      enableDamping
      dampingFactor={0.08}
      maxPolarAngle={Math.PI / 2.08}
      minDistance={35}
      maxDistance={stats.maxCameraDistance}
      onChange={clampControls}
    />
  );
}

function isFlightKey(code: string) {
  return [
    "KeyW",
    "KeyA",
    "KeyS",
    "KeyD",
    "Space",
    "ShiftLeft",
    "ShiftRight"
  ].includes(code);
}

function keyboardFlightSpeed(stats: SceneStats) {
  return clampNumber(stats.maxExtent * 0.42, 180, 900);
}

function Ground({ size, enableShadows }: { size: number; enableShadows: boolean }) {
  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, GROUND_Y, 0]} receiveShadow={enableShadows} renderOrder={0}>
      <planeGeometry args={[size, size]} />
      <meshStandardMaterial color="#101827" roughness={1} depthWrite />
    </mesh>
  );
}

function Surfaces({ surfaces, settings }: { surfaces: Surface[]; settings: SceneSettings }) {
  const visibleSurfaces = useMemo(
    () =>
      surfaces
        .filter((surface) => shouldRenderSurface(surface, settings))
        .sort((a, b) => surfaceRenderPriority(a.kind) - surfaceRenderPriority(b.kind)),
    [surfaces, settings]
  );

  return (
    <group>
      {visibleSurfaces.map((surface) => (
        <SurfaceMesh key={surface.id} surface={surface} settings={settings} />
      ))}
    </group>
  );
}

function SurfaceMesh({ surface, settings }: { surface: Surface; settings: SceneSettings }) {
  const shape = useMemo(() => buildShape(surface.coordinates), [surface.coordinates]);

  if (!shape) return null;

  const isWater = surface.kind.includes("water");
  const y = surfaceY(surface.kind);
  const renderOrder = isWater ? 1 : surfaceRenderPriority(surface.kind);

  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, y, 0]} receiveShadow renderOrder={renderOrder}>
      <shapeGeometry args={[shape]} />
      <meshStandardMaterial
        color={surfaceColor(surface.kind, settings)}
        roughness={0.96}
        side={THREE.DoubleSide}
        depthWrite={false}
        depthTest
        polygonOffset
        polygonOffsetFactor={-20 - renderOrder}
        polygonOffsetUnits={-20 - renderOrder}
      />
    </mesh>
  );
}

function Roads({
  roads,
  roadLoad,
  settings,
  events,
  closedRoadIds,
  forcedOpenRoadIds,
  editorTool,
  onRoadPick,
  onRoadHover
}: {
  roads: Road[];
  roadLoad: RoadLoad[];
  settings: SceneSettings;
  events: TrafficEvent[];
  closedRoadIds: string[];
  forcedOpenRoadIds: string[];
  editorTool: EditorTool;
  onRoadPick?: (road: Road, point: RoadPickPoint) => void;
  onRoadHover?: (road: Road | null) => void;
}) {
  const loadByRoad = new Map(roadLoad.map((load) => [load.road_id, load]));
  const activeRoadState = useMemo(
    () => buildActiveRoadState(events, closedRoadIds, forcedOpenRoadIds),
    [events, closedRoadIds, forcedOpenRoadIds]
  );

  return (
    <group>
      {roads.map((road) => {
        const load = loadByRoad.get(road.id);
        const state = activeRoadState.get(road.id) ?? null;
        const segmentCount = Math.max(1, road.coordinates.length - 1);

        return (
          <group key={road.id}>
            {road.coordinates.slice(1).map((point, index) => {
              const previous = road.coordinates[index];

              return (
                <RoadSegment
                  key={`${road.id}:${index}`}
                  road={road}
                  start={previous}
                  end={point}
                  congestion={load?.congestion_score ?? 0}
                  settings={settings}
                  segmentIndex={index}
                  segmentCount={segmentCount}
                  activeState={state}
                  editorTool={editorTool}
                  onRoadPick={onRoadPick}
                  onRoadHover={onRoadHover}
                />
              );
            })}

            {settings.fineGeometryDetails && (
              <RoadJoints
                road={road}
                congestion={load?.congestion_score ?? 0}
                settings={settings}
                segmentCount={segmentCount}
                activeState={state}
                editorTool={editorTool}
              />
            )}
          </group>
        );
      })}
    </group>
  );
}

function RoadSegment({
  road,
  start,
  end,
  congestion,
  settings,
  segmentIndex,
  segmentCount,
  activeState,
  editorTool,
  onRoadPick,
  onRoadHover
}: {
  road: Road;
  start: Coordinate;
  end: Coordinate;
  congestion: number;
  settings: SceneSettings;
  segmentIndex: number;
  segmentCount: number;
  activeState: "closed" | "roadwork" | "forced_open" | null;
  editorTool: EditorTool;
  onRoadPick?: (road: Road, point: RoadPickPoint) => void;
  onRoadHover?: (road: Road | null) => void;
}) {
  const startX = toSceneX(start.x);
  const endX = toSceneX(end.x);
  const startZ = start.z;
  const endZ = end.z;

  const dx = endX - startX;
  const dz = endZ - startZ;
  const length = Math.sqrt(dx * dx + dz * dz);

  if (length < 0.5) return null;

  const angle = Math.atan2(dz, dx);
  const width = roadWidth(road);
  const startVerticalOffset = featureVerticalOffsetAtIndex(road, segmentIndex, segmentCount);
  const endVerticalOffset = featureVerticalOffsetAtIndex(road, segmentIndex + 1, segmentCount);
  const startY = ROAD_Y + startVerticalOffset;
  const endY = ROAD_Y + endVerticalOffset;
  const roadY = (startY + endY) / 2;
  const slopeAngle = Math.atan2(endY - startY, length);
  const isElevated = Math.max(startVerticalOffset, endVerticalOffset) > 1.2;
  const isTunnel = Math.min(startVerticalOffset, endVerticalOffset) < -0.1;
  const color = roadColor(road, settings);
  const congestionColor = roadCongestionColor(road, congestion, settings);
  const editorGlow = settings.highlightRoadAccess && editorTool ? editorGlowColor(editorTool) : null;
  const stateGlow = settings.highlightRoadAccess && activeState ? activeRoadGlowColor(activeState) : null;
  const glowColor = editorGlow ?? stateGlow;

  function handleClick(event: ThreeEvent<MouseEvent>) {
    if (!editorTool || !onRoadPick) return;

    event.stopPropagation();

    const pickedProgress = progressOnSegment(
      event.point.x,
      event.point.z,
      startX,
      startZ,
      endX,
      endZ
    );

    const originalX = start.x + (end.x - start.x) * pickedProgress;
    const originalZ = start.z + (end.z - start.z) * pickedProgress;

    onRoadPick(road, {
      progress: pickedProgress,
      x: originalX,
      z: originalZ
    });
  }

  return (
    <group
      position={[(startX + endX) / 2, roadY, (startZ + endZ) / 2]}
      rotation={[0, -angle, 0]}
      onPointerEnter={(event) => {
        if (!editorTool) return;
        event.stopPropagation();
        onRoadHover?.(road);
      }}
      onPointerLeave={(event) => {
        if (!editorTool) return;
        event.stopPropagation();
        onRoadHover?.(null);
      }}
      onClick={handleClick}
    >
      <group rotation={[0, 0, slopeAngle]}>
        {isElevated && <BridgeSupports length={length} width={width} deckY={roadY} />}

        {isTunnel && (
          <mesh position={[0, 0, 0]} renderOrder={80}>
            <boxGeometry args={[length + 1.4, 0.22, width + 1.6]} />
            <meshStandardMaterial
              color="#38bdf8"
              emissive="#38bdf8"
              emissiveIntensity={0.42}
              transparent
              opacity={0.16}
              depthTest={false}
              depthWrite={false}
            />
          </mesh>
        )}

        {glowColor && (
          <mesh position={[0, 0.01, 0]} renderOrder={19}>
            <boxGeometry args={[length + 2.4, 0.12, width + 2.6]} />
            <meshStandardMaterial
              color={glowColor}
              emissive={glowColor}
              emissiveIntensity={0.75}
              transparent
              opacity={0.42}
              depthWrite={false}
            />
          </mesh>
        )}

        <mesh receiveShadow={!isTunnel} renderOrder={isTunnel ? 81 : 20}>
          <boxGeometry args={[length, 0.28, width]} />
          <meshStandardMaterial
            color={glowColor ?? color}
            emissive={isTunnel ? glowColor ?? color : glowColor ?? "#000000"}
            emissiveIntensity={isTunnel ? 0.34 : glowColor ? 0.34 : 0}
            roughness={0.86}
            transparent={isTunnel}
            opacity={isTunnel ? 0.72 : 1}
            depthTest={!isTunnel}
            depthWrite={!isTunnel}
            polygonOffset
            polygonOffsetFactor={-40}
            polygonOffsetUnits={-40}
          />
        </mesh>

        {congestionColor && !glowColor && (
          <mesh position={[0, 0.18, 0]} renderOrder={isTunnel ? 86 : 23}>
            <boxGeometry args={[length * 0.96, 0.05, width * 0.82]} />
            <meshStandardMaterial
              color={congestionColor}
              emissive={congestionColor}
              emissiveIntensity={isTunnel ? 0.72 : 0.18}
              roughness={0.82}
              transparent={isTunnel}
              opacity={isTunnel ? 0.46 : 1}
              depthTest={!isTunnel}
              depthWrite={!isTunnel}
              polygonOffset
              polygonOffsetFactor={-90}
              polygonOffsetUnits={-90}
            />
          </mesh>
        )}

        {road.is_driveable && settings.fineGeometryDetails && <LaneMarkings length={length} width={width} road={road} />}

        {!road.is_driveable && settings.highlightRoadAccess && (
          <mesh position={[0, 0.22, 0]} renderOrder={isTunnel ? 87 : 22}>
            <boxGeometry args={[length * 0.92, 0.07, Math.min(1.2, width * 0.35)]} />
            <meshStandardMaterial
              color="#fecaca"
              emissive="#ef4444"
              emissiveIntensity={isTunnel ? 0.95 : 0.18}
              transparent={isTunnel}
              opacity={isTunnel ? 0.58 : 1}
              depthTest={!isTunnel}
              depthWrite={!isTunnel}
            />
          </mesh>
        )}
      </group>
    </group>
  );
}

function RoadJoints({
  road,
  congestion,
  settings,
  segmentCount,
  activeState,
  editorTool
}: {
  road: Road;
  congestion: number;
  settings: SceneSettings;
  segmentCount: number;
  activeState: "closed" | "roadwork" | "forced_open" | null;
  editorTool: EditorTool;
}) {
  if (road.coordinates.length < 2) {
    return null;
  }

  const width = roadWidth(road);
  const radius = width * 0.52;
  const color = roadColor(road, settings);
  const congestionColor = roadCongestionColor(road, congestion, settings);
  const editorGlow = settings.highlightRoadAccess && editorTool ? editorGlowColor(editorTool) : null;
  const stateGlow = settings.highlightRoadAccess && activeState ? activeRoadGlowColor(activeState) : null;
  const glowColor = editorGlow ?? stateGlow;

  return (
    <group>
      {road.coordinates.map((point, index) => {
        const verticalOffset = featureVerticalOffsetAtIndex(road, index, segmentCount);
        const isTunnel = verticalOffset < -0.1;
        const y = ROAD_Y + verticalOffset + 0.02;

        return (
          <group key={`${road.id}:joint:${index}`} position={[toSceneX(point.x), y, point.z]}>
            <mesh renderOrder={isTunnel ? 82 : 21}>
              <cylinderGeometry args={[radius, radius, ROAD_JOINT_HEIGHT, 32]} />
              <meshStandardMaterial
                color={glowColor ?? color}
                emissive={isTunnel ? glowColor ?? color : glowColor ?? "#000000"}
                emissiveIntensity={isTunnel ? 0.34 : glowColor ? 0.34 : 0}
                roughness={0.86}
                transparent={isTunnel}
                opacity={isTunnel ? 0.7 : 1}
                depthTest={!isTunnel}
                depthWrite={!isTunnel}
                polygonOffset
                polygonOffsetFactor={-45}
                polygonOffsetUnits={-45}
              />
            </mesh>

            {congestionColor && !glowColor && (
              <mesh position={[0, 0.18, 0]} renderOrder={isTunnel ? 88 : 24}>
                <cylinderGeometry args={[radius * 0.72, radius * 0.72, 0.06, 32]} />
                <meshStandardMaterial
                  color={congestionColor}
                  emissive={congestionColor}
                  emissiveIntensity={isTunnel ? 0.72 : 0.18}
                  roughness={0.82}
                  transparent={isTunnel}
                  opacity={isTunnel ? 0.44 : 1}
                  depthTest={!isTunnel}
                  depthWrite={!isTunnel}
                  polygonOffset
                  polygonOffsetFactor={-92}
                  polygonOffsetUnits={-92}
                />
              </mesh>
            )}

            {!road.is_driveable && settings.highlightRoadAccess && (
              <mesh position={[0, 0.22, 0]} renderOrder={isTunnel ? 89 : 25}>
                <cylinderGeometry args={[Math.min(1.6, radius * 0.42), Math.min(1.6, radius * 0.42), 0.08, 24]} />
                <meshStandardMaterial
                  color="#fecaca"
                  emissive="#ef4444"
                  emissiveIntensity={isTunnel ? 0.95 : 0.18}
                  transparent={isTunnel}
                  opacity={isTunnel ? 0.58 : 1}
                  depthTest={!isTunnel}
                  depthWrite={!isTunnel}
                />
              </mesh>
            )}
          </group>
        );
      })}
    </group>
  );
}

function LaneMarkings({ length, width, road }: { length: number; width: number; road: Road }) {
  const laneCount = visualLaneCount(road);

  if (laneCount <= 1) {
    return null;
  }

  const laneWidth = width / laneCount;
  const markings = [];

  for (let index = 1; index < laneCount; index += 1) {
    const z = -width / 2 + laneWidth * index;
    const isDirectionDivider = isTwoWayDirectionDivider(road, index);

    markings.push(
      <mesh key={`lane:${index}`} position={[0, ROAD_MARKING_Y - ROAD_Y + 0.025, z]} renderOrder={24}>
        <boxGeometry args={[length * 0.96, 0.045, isDirectionDivider ? 0.2 : 0.12]} />
        <meshStandardMaterial
          color={isDirectionDivider ? "#e5e7eb" : "#94a3b8"}
          roughness={0.72}
          polygonOffset
          polygonOffsetFactor={-60}
          polygonOffsetUnits={-60}
        />
      </mesh>
    );
  }

  return <group>{markings}</group>;
}

function visualLaneCount(road: Road) {
  const directionalLaneSum = (road.lanes_forward ?? 0) + (road.lanes_backward ?? 0);

  if (directionalLaneSum > 0) {
    return clampNumber(directionalLaneSum, 1, 12);
  }

  return clampNumber(road.lanes, 1, 12);
}

function isTwoWayDirectionDivider(road: Road, dividerIndex: number) {
  if (road.one_way) {
    return false;
  }

  if (road.lanes_backward !== null && road.lanes_backward > 0) {
    return dividerIndex === road.lanes_backward;
  }

  const laneCount = visualLaneCount(road);

  if (laneCount < 2 || laneCount % 2 !== 0) {
    return false;
  }

  return dividerIndex === laneCount / 2;
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
  const shape = useMemo(
    () => buildShape(building.coordinates, building.holes ?? []),
    [building.coordinates, building.holes]
  );
  const height = clamp(building.height, 3.5, 110);

  if (!shape) return null;

  return (
    <group>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, BUILDING_BASE_Y, 0]} castShadow receiveShadow renderOrder={30}>
        <extrudeGeometry
          args={[
            shape,
            {
              depth: height,
              bevelEnabled: false
            }
          ]}
        />
        <meshStandardMaterial color="#8b95a5" roughness={0.88} />
      </mesh>

      <BuildingRoof building={building} height={height} />
    </group>
  );
}

function BuildingRoof({ building, height }: { building: Building; height: number }) {
  const shape = useMemo(
    () => buildShape(building.coordinates, building.holes ?? []),
    [building.coordinates, building.holes]
  );

  if (!shape) return null;

  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, height + BUILDING_BASE_Y + 0.08, 0]} renderOrder={31}>
      <shapeGeometry args={[shape]} />
      <meshStandardMaterial
        color="#6b7280"
        roughness={0.92}
        side={THREE.DoubleSide}
        polygonOffset
        polygonOffsetFactor={-70}
        polygonOffsetUnits={-70}
      />
    </mesh>
  );
}

function Vehicles({ state, simpleActors }: { state: SimulationState; simpleActors: boolean }) {
  return (
    <group>
      {state.vehicles.map((vehicle) => {
        const x = toSceneX(vehicle.x);
        const z = vehicle.z;
        const heading = toSceneHeading(vehicle.heading_rad);
        const isTunnelVehicle = vehicle.elevation_m < -0.1;

        return (
          <group key={vehicle.id}>
            <VehicleActor
              vehicle={vehicle}
              x={x}
              z={z}
              heading={heading}
              yOffset={vehicle.elevation_m + VEHICLE_SURFACE_LIFT}
              simple={simpleActors}
            />

            {isTunnelVehicle && !simpleActors && (
              <TunnelVehicleGhost
                x={x}
                z={z}
                y={1.32 + vehicle.elevation_m + VEHICLE_SURFACE_LIFT}
                heading={heading}
                length={vehicle.length_m}
                width={vehicle.width_m}
              />
            )}
          </group>
        );
      })}
    </group>
  );
}

function TunnelVehicleGhost({
  x,
  y,
  z,
  heading,
  length,
  width
}: {
  x: number;
  y: number;
  z: number;
  heading: number;
  length: number;
  width: number;
}) {
  return (
    <group position={[x, y, z]} rotation={[0, -heading, 0]}>
      <mesh renderOrder={95}>
        <boxGeometry args={[Math.max(3.6, length), 1.05, Math.max(1.7, width)]} />
        <meshStandardMaterial
          color="#38bdf8"
          emissive="#38bdf8"
          emissiveIntensity={0.8}
          transparent
          opacity={0.24}
          depthTest={false}
          depthWrite={false}
          roughness={0.35}
        />
      </mesh>

      <mesh renderOrder={94}>
        <boxGeometry args={[Math.max(4.2, length + 0.8), 1.35, Math.max(2.1, width + 0.5)]} />
        <meshStandardMaterial
          color="#38bdf8"
          emissive="#38bdf8"
          emissiveIntensity={0.55}
          transparent
          opacity={0.12}
          depthTest={false}
          depthWrite={false}
          roughness={0.35}
        />
      </mesh>
    </group>
  );
}

function Pedestrians({ state, simpleActors }: { state: SimulationState; simpleActors: boolean }) {
  return (
    <group>
      {state.pedestrians.map((pedestrian, index) => (
        <PedestrianActor
          key={pedestrian.id}
          pedestrian={pedestrian}
          x={toSceneX(pedestrian.x)}
          z={pedestrian.z}
          heading={toSceneHeading(pedestrian.heading_rad)}
          bob={Math.sin(state.tick * 0.35 + index) * 0.05}
          simple={simpleActors}
          yOffset={PEDESTRIAN_SURFACE_LIFT}
        />
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

        const phase = signal.phase.toLowerCase();

        const color = phase.includes("pedestrian")
          ? "#38bdf8"
          : phase.includes("green") || phase.includes("g")
            ? "#22c55e"
            : phase.includes("yellow") || phase.includes("y")
              ? "#facc15"
              : "#ef4444";

        return (
          <group key={signal.id} position={[toSceneX(intersection.x), 3, intersection.z]}>
            <mesh castShadow renderOrder={44}>
              <cylinderGeometry args={[0.25, 0.25, 6, 10]} />
              <meshStandardMaterial color="#111827" />
            </mesh>

            <mesh position={[0, 3.2, 0]} castShadow renderOrder={45}>
              <boxGeometry args={[1.4, 1.4, 1.4]} />
              <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.4} />
            </mesh>
          </group>
        );
      })}
    </group>
  );
}


function intersectionSignalColor(phase: string | undefined, hasRealSignal: boolean) {
  if (!phase) {
    return hasRealSignal ? "#22c55e" : "#64748b";
  }

  const lowered = phase.toLowerCase();

  if (lowered.includes("green") || lowered.includes("g")) {
    return "#22c55e";
  }

  if (lowered.includes("yellow") || lowered.includes("y")) {
    return "#facc15";
  }

  if (lowered.includes("red") || lowered.includes("r")) {
    return "#ef4444";
  }

  return "#38bdf8";
}

function Crossings({ crossings, roads, settings }: { crossings: Crossing[]; roads: Road[]; settings: SceneSettings }) {
  return (
    <group>
      {crossings.map((crossing) => {
        const angle = nearestRoadAngle(crossing, roads);
        const crossingRoadWidth = nearestRoadWidth(crossing, roads);
        const stripeCount = settings.fineGeometryDetails
          ? Math.max(5, Math.min(14, Math.floor(crossingRoadWidth / 1.15)))
          : Math.max(3, Math.min(7, Math.floor(crossingRoadWidth / 2.2)));
        const stripeStep = settings.fineGeometryDetails ? 1.15 : 2.2;
        const stripeStart = -((stripeCount - 1) * stripeStep) / 2;
        const stripeDepth = clampNumber(crossingRoadWidth * 0.92, 5.2, 16);

        return (
          <group
            key={crossing.id}
            position={[toSceneX(crossing.x), CROSSING_Y, crossing.z]}
            rotation={[0, -angle + Math.PI / 2, 0]}
          >
            {Array.from({ length: stripeCount }).map((_, index) => (
              <mesh key={index} position={[stripeStart + index * stripeStep, 0, 0]} renderOrder={25}>
                <boxGeometry args={[0.66, 0.08, stripeDepth]} />
                <meshStandardMaterial
                  color="#f8fafc"
                  polygonOffset
                  polygonOffsetFactor={-80}
                  polygonOffsetUnits={-80}
                />
              </mesh>
            ))}
          </group>
        );
      })}
    </group>
  );
}

function Intersections({ cityMap, state }: { cityMap: CityMap; state: SimulationState | null }) {
  const signalByIntersectionId = new Map(
    (state?.signals ?? []).map((signal) => [signal.intersection_id, signal])
  );

  return (
    <group>
      {cityMap.intersections.map((intersection) => {
        const signal = signalByIntersectionId.get(intersection.id);
        const color = intersectionSignalColor(signal?.phase, intersection.has_signal);

        return (
          <mesh key={intersection.id} position={[toSceneX(intersection.x), INTERSECTION_Y, intersection.z]} renderOrder={23}>
            <cylinderGeometry args={[3.1, 3.1, 0.26, 24]} />
            <meshStandardMaterial
              color={color}
              emissive={signal ? color : "#000000"}
              emissiveIntensity={signal ? 0.18 : 0}
              roughness={0.78}
              polygonOffset
              polygonOffsetFactor={-50}
              polygonOffsetUnits={-50}
            />
          </mesh>
        );
      })}
    </group>
  );
}

function RailLines({ railLines, settings }: { railLines: RailLine[]; settings: SceneSettings }) {
  return (
    <group>
      {railLines.map((rail) => {
        const segmentCount = Math.max(1, rail.coordinates.length - 1);

        return (
          <group key={rail.id}>
            {rail.coordinates.slice(1).map((point, index) => {
              const previous = rail.coordinates[index];

              return (
                <RailSegment
                  key={`${rail.id}:${index}`}
                  rail={rail}
                  start={previous}
                  end={point}
                  segmentIndex={index}
                  segmentCount={segmentCount}
                  settings={settings}
                />
              );
            })}

            {settings.fineGeometryDetails && <RailJoints rail={rail} segmentCount={segmentCount} />}
          </group>
        );
      })}
    </group>
  );
}

function RailSegment({
  rail,
  start,
  end,
  segmentIndex,
  segmentCount,
  settings
}: {
  rail: RailLine;
  start: Coordinate;
  end: Coordinate;
  segmentIndex: number;
  segmentCount: number;
  settings: SceneSettings;
}) {
  const startX = toSceneX(start.x);
  const endX = toSceneX(end.x);
  const startZ = start.z;
  const endZ = end.z;

  const dx = endX - startX;
  const dz = endZ - startZ;
  const length = Math.sqrt(dx * dx + dz * dz);

  if (length < 0.5) return null;

  const angle = Math.atan2(dz, dx);
  const startVerticalOffset = featureVerticalOffsetAtIndex(rail, segmentIndex, segmentCount);
  const endVerticalOffset = featureVerticalOffsetAtIndex(rail, segmentIndex + 1, segmentCount);
  const startY = ROAD_Y + 0.38 + startVerticalOffset;
  const endY = ROAD_Y + 0.38 + endVerticalOffset;
  const railY = (startY + endY) / 2;
  const slopeAngle = Math.atan2(endY - startY, length);
  const isElevated = Math.max(startVerticalOffset, endVerticalOffset) > 1.2;
  const isTunnel = Math.min(startVerticalOffset, endVerticalOffset) < -0.1;
  const isTram = rail.kind === "tram" || rail.kind === "light_rail";
  const baseWidth = isTram ? 2.6 : 3.2;
  const railBedColor = isTunnel ? "#111827" : isElevated ? "#374151" : "#2b3545";
  const railColor = "#748094";
  const sleeperColor = "#3f4a5c";

  return (
    <group
      position={[(startX + endX) / 2, railY, (startZ + endZ) / 2]}
      rotation={[0, -angle, 0]}
    >
      <group rotation={[0, 0, slopeAngle]}>
        {isElevated && <BridgeSupports length={length} width={baseWidth} deckY={railY} />}

        {isTunnel && (
          <mesh position={[0, 0, 0]} renderOrder={82}>
            <boxGeometry args={[length + 1, 0.16, baseWidth + 1.2]} />
            <meshStandardMaterial
              color="#38bdf8"
              emissive="#38bdf8"
              emissiveIntensity={0.42}
              transparent
              opacity={0.14}
              depthTest={false}
              depthWrite={false}
            />
          </mesh>
        )}

        <mesh renderOrder={isTunnel ? 83 : 27}>
          <boxGeometry args={[length, 0.08, baseWidth]} />
          <meshStandardMaterial
            color={railBedColor}
            emissive={isTunnel ? "#38bdf8" : "#000000"}
            emissiveIntensity={isTunnel ? 0.2 : 0}
            roughness={0.82}
            transparent={isTunnel}
            opacity={isTunnel ? 0.68 : 1}
            depthTest={!isTunnel}
            depthWrite={!isTunnel}
            polygonOffset
            polygonOffsetFactor={-95}
            polygonOffsetUnits={-95}
          />
        </mesh>

        <mesh position={[0, 0.08, baseWidth * 0.26]} renderOrder={isTunnel ? 84 : 28}>
          <boxGeometry args={[length * 0.96, 0.08, 0.16]} />
          <meshStandardMaterial
            color={railColor}
            emissive={isTunnel ? railColor : "#000000"}
            emissiveIntensity={isTunnel ? 0.18 : 0}
            roughness={0.55}
            transparent={isTunnel}
            opacity={isTunnel ? 0.78 : 1}
            depthTest={!isTunnel}
            depthWrite={!isTunnel}
          />
        </mesh>

        <mesh position={[0, 0.08, -baseWidth * 0.26]} renderOrder={isTunnel ? 84 : 28}>
          <boxGeometry args={[length * 0.96, 0.08, 0.16]} />
          <meshStandardMaterial
            color={railColor}
            emissive={isTunnel ? railColor : "#000000"}
            emissiveIntensity={isTunnel ? 0.18 : 0}
            roughness={0.55}
            transparent={isTunnel}
            opacity={isTunnel ? 0.78 : 1}
            depthTest={!isTunnel}
            depthWrite={!isTunnel}
          />
        </mesh>

        {settings.fineGeometryDetails && Array.from({ length: Math.max(3, Math.floor(length / RAIL_SLEEPER_SPACING_M)) }).map((_, index, items) => {
          const x = -length * 0.48 + (length * 0.96 * index) / Math.max(1, items.length - 1);

          return (
            <mesh key={index} position={[x, 0.045, 0]} renderOrder={isTunnel ? 83 : 27}>
              <boxGeometry args={[0.16, 0.055, baseWidth * 0.86]} />
              <meshStandardMaterial
                color={sleeperColor}
                roughness={0.72}
                transparent={isTunnel}
                opacity={isTunnel ? 0.72 : 1}
                depthTest={!isTunnel}
                depthWrite={!isTunnel}
              />
            </mesh>
          );
        })}
      </group>
    </group>
  );
}

function RailJoints({
  rail,
  segmentCount
}: {
  rail: RailLine;
  segmentCount: number;
}) {
  if (rail.coordinates.length < 2) {
    return null;
  }

  const isTram = rail.kind === "tram" || rail.kind === "light_rail";
  const baseWidth = isTram ? 2.6 : 3.2;
  const railColor = "#748094";
  const sleeperColor = "#3f4a5c";

  return (
    <group>
      {rail.coordinates.map((point, index) => {
        const verticalOffset = featureVerticalOffsetAtIndex(rail, index, segmentCount);
        const isElevated = verticalOffset > 1.2;
        const isTunnel = verticalOffset < -0.1;
        const y = ROAD_Y + 0.38 + verticalOffset;
        const railBedColor = isTunnel ? "#111827" : isElevated ? "#374151" : "#2b3545";

        return (
          <group key={`${rail.id}:joint:${index}`} position={[toSceneX(point.x), y, point.z]}>
            <mesh renderOrder={isTunnel ? 83 : 27}>
              <cylinderGeometry args={[baseWidth * 0.52, baseWidth * 0.52, RAIL_JOINT_HEIGHT, 32]} />
              <meshStandardMaterial
                color={railBedColor}
                emissive={isTunnel ? "#38bdf8" : "#000000"}
                emissiveIntensity={isTunnel ? 0.2 : 0}
                roughness={0.82}
                transparent={isTunnel}
                opacity={isTunnel ? 0.68 : 1}
                depthTest={!isTunnel}
                depthWrite={!isTunnel}
                polygonOffset
                polygonOffsetFactor={-96}
                polygonOffsetUnits={-96}
              />
            </mesh>

            <mesh position={[0, 0.09, baseWidth * 0.26]} renderOrder={isTunnel ? 84 : 28}>
              <cylinderGeometry args={[0.22, 0.22, 0.09, 18]} />
              <meshStandardMaterial
                color={railColor}
                emissive={isTunnel ? railColor : "#000000"}
                emissiveIntensity={isTunnel ? 0.18 : 0}
                roughness={0.55}
                transparent={isTunnel}
                opacity={isTunnel ? 0.78 : 1}
                depthTest={!isTunnel}
                depthWrite={!isTunnel}
              />
            </mesh>

            <mesh position={[0, 0.09, -baseWidth * 0.26]} renderOrder={isTunnel ? 84 : 28}>
              <cylinderGeometry args={[0.22, 0.22, 0.09, 18]} />
              <meshStandardMaterial
                color={railColor}
                emissive={isTunnel ? railColor : "#000000"}
                emissiveIntensity={isTunnel ? 0.18 : 0}
                roughness={0.55}
                transparent={isTunnel}
                opacity={isTunnel ? 0.78 : 1}
                depthTest={!isTunnel}
                depthWrite={!isTunnel}
              />
            </mesh>

            <mesh position={[0, 0.05, 0]} renderOrder={isTunnel ? 83 : 27}>
              <boxGeometry args={[0.26, 0.055, baseWidth * 0.86]} />
              <meshStandardMaterial
                color={sleeperColor}
                roughness={0.72}
                transparent={isTunnel}
                opacity={isTunnel ? 0.72 : 1}
                depthTest={!isTunnel}
                depthWrite={!isTunnel}
              />
            </mesh>
          </group>
        );
      })}
    </group>
  );
}

function TransitStops({ stops }: { stops: TransitStop[] }) {
  return (
    <group>
      {stops.map((stop) => {
        const isTram = stop.kind.includes("tram") || stop.kind.includes("rail");
        const color = isTram ? "#facc15" : "#fde68a";

        return (
          <group key={stop.id} position={[toSceneX(stop.x), ROAD_Y + 0.9, stop.z]}>
            <mesh renderOrder={32}>
              <boxGeometry args={[4.2, 0.22, 4.2]} />
              <meshStandardMaterial
                color={color}
                emissive={color}
                emissiveIntensity={0.18}
                roughness={0.62}
              />
            </mesh>

            <mesh position={[0, 1.1, 0]} castShadow renderOrder={33}>
              <boxGeometry args={[0.38, 2.2, 0.38]} />
              <meshStandardMaterial color="#111827" roughness={0.66} />
            </mesh>

            <mesh position={[0, 2.35, 0]} castShadow renderOrder={34}>
              <boxGeometry args={[1.25, 0.8, 0.16]} />
              <meshStandardMaterial
                color={isTram ? "#dc2626" : "#2563eb"}
                emissive={isTram ? "#dc2626" : "#2563eb"}
                emissiveIntensity={0.16}
                roughness={0.52}
              />
            </mesh>
          </group>
        );
      })}
    </group>
  );
}

function nearestRoadAngle(crossing: Crossing, roads: Road[]) {
  let bestDistance = Number.POSITIVE_INFINITY;
  let bestAngle = 0;

  for (const road of roads) {
    if (!road.is_driveable) {
      continue;
    }

    for (let index = 1; index < road.coordinates.length; index += 1) {
      const start = road.coordinates[index - 1];
      const end = road.coordinates[index];

      const startX = toSceneX(start.x);
      const endX = toSceneX(end.x);
      const crossingX = toSceneX(crossing.x);

      const distance = distanceToSegment(
        crossingX,
        crossing.z,
        startX,
        start.z,
        endX,
        end.z,
      );

      if (distance < bestDistance) {
        bestDistance = distance;
        bestAngle = Math.atan2(end.z - start.z, endX - startX);
      }
    }
  }

  return bestAngle;
}

function nearestRoadWidth(crossing: Crossing, roads: Road[]) {
  let bestDistance = Number.POSITIVE_INFINITY;
  let bestWidth = 6.5;

  for (const road of roads) {
    if (!road.is_driveable) {
      continue;
    }

    for (let index = 1; index < road.coordinates.length; index += 1) {
      const start = road.coordinates[index - 1];
      const end = road.coordinates[index];

      const startX = toSceneX(start.x);
      const endX = toSceneX(end.x);
      const crossingX = toSceneX(crossing.x);

      const distance = distanceToSegment(
        crossingX,
        crossing.z,
        startX,
        start.z,
        endX,
        end.z,
      );

      if (distance < bestDistance) {
        bestDistance = distance;
        bestWidth = roadWidth(road);
      }
    }
  }

  return bestWidth;
}

function distanceToSegment(
  px: number,
  pz: number,
  ax: number,
  az: number,
  bx: number,
  bz: number,
) {
  const dx = bx - ax;
  const dz = bz - az;
  const lengthSquared = dx * dx + dz * dz;

  if (lengthSquared <= 0.0001) {
    return Math.hypot(px - ax, pz - az);
  }

  const t = Math.max(0, Math.min(1, ((px - ax) * dx + (pz - az) * dz) / lengthSquared));
  const x = ax + dx * t;
  const z = az + dz * t;

  return Math.hypot(px - x, pz - z);
}

function EventMarkers({ events, roads }: { events: TrafficEvent[]; roads: Road[] }) {
  return (
    <group>
      {events.map((event) => {
        if (event.kind !== "accident" && event.kind !== "roadwork") {
          return null;
        }

        const point = eventPoint(event, roads);
        if (!point) return null;

        const color = event.kind === "accident" ? "#fb923c" : "#facc15";

        return (
          <group key={event.id} position={[toSceneX(point.x), ROAD_Y + 2.4, point.z]}>
            <mesh renderOrder={70}>
              <sphereGeometry args={[2.4, 24, 24]} />
              <meshStandardMaterial
                color={color}
                emissive={color}
                emissiveIntensity={1.35}
                roughness={0.3}
              />
            </mesh>

            <mesh renderOrder={69}>
              <sphereGeometry args={[4.8, 24, 24]} />
              <meshStandardMaterial
                color={color}
                emissive={color}
                emissiveIntensity={0.9}
                transparent
                opacity={0.24}
                depthWrite={false}
              />
            </mesh>

            <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -2.18, 0]} renderOrder={68}>
              <ringGeometry args={[4.2, 6.4, 48]} />
              <meshStandardMaterial
                color={color}
                emissive={color}
                emissiveIntensity={1}
                transparent
                opacity={0.78}
                side={THREE.DoubleSide}
                depthWrite={false}
              />
            </mesh>
          </group>
        );
      })}
    </group>
  );
}

function eventPoint(event: TrafficEvent, roads: Road[]) {
  const x = event.payload.x;
  const z = event.payload.z;

  if (typeof x === "number" && typeof z === "number") {
    return { x, z };
  }

  const road = roads.find((item) => item.id === event.target_id);
  if (!road || road.coordinates.length < 2) return null;

  const start = road.coordinates[0];
  const end = road.coordinates[road.coordinates.length - 1];

  return {
    x: (start.x + end.x) / 2,
    z: (start.z + end.z) / 2
  };
}

function buildActiveRoadState(
  events: TrafficEvent[],
  closedRoadIds: string[],
  forcedOpenRoadIds: string[]
) {
  const result = new Map<string, "closed" | "roadwork" | "forced_open">();

  for (const roadId of forcedOpenRoadIds) {
    result.set(roadId, "forced_open");
  }

  for (const event of events) {
    if (!event.target_id) continue;

    if (event.kind === "roadwork") {
      result.set(event.target_id, "roadwork");
    }
  }

  for (const roadId of closedRoadIds) {
    result.set(roadId, "closed");
  }

  return result;
}

function editorGlowColor(tool: EditorTool) {
  if (tool === "close_road") return "#ef4444";
  if (tool === "open_road") return "#22c55e";
  if (tool === "roadwork") return "#facc15";
  if (tool === "accident") return "#f97316";

  return null;
}

function activeRoadGlowColor(state: "closed" | "roadwork" | "forced_open") {
  if (state === "closed") return "#ef4444";
  if (state === "forced_open") return "#22c55e";
  return "#facc15";
}

function progressOnSegment(
  px: number,
  pz: number,
  ax: number,
  az: number,
  bx: number,
  bz: number
) {
  const dx = bx - ax;
  const dz = bz - az;
  const lengthSquared = dx * dx + dz * dz;

  if (lengthSquared <= 0.0001) {
    return 0;
  }

  return Math.max(0, Math.min(1, ((px - ax) * dx + (pz - az) * dz) / lengthSquared));
}

function buildShape(coordinates: Coordinate[], holes: Coordinate[][] = []) {
  if (coordinates.length < 3) return null;

  const shape = new THREE.Shape();

  shape.moveTo(toSceneX(coordinates[0].x), -coordinates[0].z);

  for (const point of coordinates.slice(1)) {
    shape.lineTo(toSceneX(point.x), -point.z);
  }

  for (const hole of holes) {
    if (hole.length < 3) continue;

    const path = new THREE.Path();

    path.moveTo(toSceneX(hole[0].x), -hole[0].z);

    for (const point of hole.slice(1)) {
      path.lineTo(toSceneX(point.x), -point.z);
    }

    shape.holes.push(path);
  }

  return shape;
}

function toSceneX(x: number): number {
  return -x;
}

function toSceneHeading(heading: number): number {
  return Math.atan2(Math.sin(heading), -Math.cos(heading));
}

function getSceneStats(cityMap: CityMap | null): SceneStats {
  const points: Coordinate[] = [];

  if (cityMap) {
    for (const road of cityMap.roads) points.push(...road.coordinates);
    for (const building of cityMap.buildings) points.push(...building.coordinates);
    for (const surface of cityMap.surfaces ?? []) points.push(...surface.coordinates);
    for (const rail of cityMap.rail_lines ?? []) points.push(...rail.coordinates);
    for (const crossing of cityMap.crossings) {
      points.push({ lat: crossing.lat, lon: crossing.lon, x: crossing.x, z: crossing.z });
    }
    for (const item of cityMap.infrastructure) {
      points.push({ lat: item.lat, lon: item.lon, x: item.x, z: item.z });
    }
    for (const stop of cityMap.transit_stops ?? []) {
      points.push({ lat: stop.lat, lon: stop.lon, x: stop.x, z: stop.z });
    }
  }

  let maxExtent = 1200;
  let minX = -600;
  let maxX = 600;
  let minZ = -600;
  let maxZ = 600;

  if (points.length) {
    minX = Number.POSITIVE_INFINITY;
    maxX = Number.NEGATIVE_INFINITY;
    minZ = Number.POSITIVE_INFINITY;
    maxZ = Number.NEGATIVE_INFINITY;
  }

  for (const point of points) {
    const sceneX = toSceneX(point.x);

    minX = Math.min(minX, sceneX);
    maxX = Math.max(maxX, sceneX);
    minZ = Math.min(minZ, point.z);
    maxZ = Math.max(maxZ, point.z);

    maxExtent = Math.max(maxExtent, Math.abs(sceneX), Math.abs(point.z));
  }

  const generatedWidth = Math.max(1, maxX - minX);
  const generatedDepth = Math.max(1, maxZ - minZ);
  const generatedSize = Math.max(generatedWidth, generatedDepth);
  const panPadding = clampNumber(generatedSize * 0.38, 140, 1200);

  const groundSize = Math.max(12_000, maxExtent * 2.8 + 1600);
  const cameraHeight = Math.max(650, maxExtent * 1.12);
  const cameraDistance = Math.max(680, maxExtent * 1.12);
  const maxCameraDistance = Math.max(4_000, maxExtent * 4.2);
  const cameraFar = Math.max(24_000, maxExtent * 9);
  const fogNear = Math.max(4_500, maxExtent * 2.2);
  const fogFar = Math.max(22_000, maxExtent * 7.5);

  return {
    maxExtent,
    groundSize,
    cameraHeight,
    cameraDistance,
    maxCameraDistance,
    cameraFar,
    fogNear,
    fogFar,
    minX,
    maxX,
    minZ,
    maxZ,
    panPadding
  };
}

function shouldRenderSurface(_surface: Surface, settings: SceneSettings) {
  return settings.showGroundZones;
}

function surfaceY(kind: string) {
  if (kind.includes("water")) return WATER_Y;
  if (isSpecialLandZone(kind)) return SPECIAL_ZONE_Y;
  return LAND_ZONE_Y;
}

function surfaceRenderPriority(kind: string) {
  if (kind.includes("water")) return 1;
  if (kind.includes("sand") || kind.includes("beach") || kind.includes("shingle")) return 2;
  if (kind.includes("residential") || kind.includes("commercial") || kind.includes("industrial")) return 3;
  if (kind.includes("park") || kind.includes("forest") || kind.includes("wood")) return 4;
  if (kind.includes("grass") || kind.includes("meadow") || kind.includes("recreation_ground")) return 5;
  if (isSpecialLandZone(kind)) return 6;
  return 3;
}

function isSpecialLandZone(kind: string) {
  return (
    kind.includes("parking") ||
    kind.includes("hospital") ||
    kind.includes("school") ||
    kind.includes("commercial") ||
    kind.includes("retail") ||
    kind.includes("industrial")
  );
}

function BridgeSupports({
  length,
  width,
  deckY
}: {
  length: number;
  width: number;
  deckY: number;
}) {
  const supportHeight = Math.max(0.8, deckY - GROUND_Y - 0.22);
  const supportCount = Math.max(1, Math.min(5, Math.floor(length / 140)));
  const positions = Array.from({ length: supportCount }).map((_, index) => {
    if (supportCount === 1) return 0;
    return -length * 0.42 + (length * 0.84 * index) / (supportCount - 1);
  });

  return (
    <group>
      {positions.flatMap((x, index) => [
        <mesh key={`support-left:${index}`} position={[x, -supportHeight / 2, width * 0.42]} renderOrder={17}>
          <cylinderGeometry args={[0.32, 0.42, supportHeight, 10]} />
          <meshStandardMaterial color="#475569" roughness={0.86} />
        </mesh>,
        <mesh key={`support-right:${index}`} position={[x, -supportHeight / 2, -width * 0.42]} renderOrder={17}>
          <cylinderGeometry args={[0.32, 0.42, supportHeight, 10]} />
          <meshStandardMaterial color="#475569" roughness={0.86} />
        </mesh>
      ])}
    </group>
  );
}

function featureVerticalOffsetAtIndex(
  feature: {
    bridge: string | null;
    tunnel: string | null;
    layer: number | null;
  },
  index: number,
  segmentCount: number
) {
  const target = featureTargetVerticalOffset(feature);

  if (target === 0) {
    return 0;
  }

  const fraction = index / Math.max(1, segmentCount);
  const ramp = rampProfile(fraction);

  return target * ramp;
}

function featureTargetVerticalOffset(feature: {
  bridge: string | null;
  tunnel: string | null;
  layer: number | null;
}) {
  const layer = feature.layer ?? 0;

  if (isTunnelFeature(feature)) {
    return -Math.min(3, Math.max(1, Math.abs(layer) || 1)) * TUNNEL_VISUAL_DEPTH_M;
  }

  if (isBridgeFeature(feature) || layer > 0) {
    return Math.max(1, layer) * LAYER_HEIGHT_M;
  }

  if (layer < 0) {
    return -Math.min(3, Math.abs(layer)) * TUNNEL_VISUAL_DEPTH_M;
  }

  return 0;
}

function rampProfile(fraction: number) {
  const value = clampNumber(fraction, 0, 1);
  const rampSize = 0.22;

  if (value <= rampSize) {
    return smoothstep(value / rampSize);
  }

  if (value >= 1 - rampSize) {
    return smoothstep((1 - value) / rampSize);
  }

  return 1;
}

function smoothstep(value: number) {
  const x = clampNumber(value, 0, 1);
  return x * x * (3 - 2 * x);
}

function isBridgeFeature(feature: { bridge: string | null; layer: number | null }) {
  return truthyOsmText(feature.bridge) || (feature.layer ?? 0) > 0;
}

function isTunnelFeature(feature: { tunnel: string | null; layer: number | null }) {
  return truthyOsmText(feature.tunnel) || (feature.layer ?? 0) < 0;
}

function truthyOsmText(value: string | null) {
  if (value === null) {
    return false;
  }

  const normalized = value.trim().toLowerCase();

  if (!normalized) {
    return false;
  }

  return !["no", "false", "0"].includes(normalized);
}

function roadWidth(road: Road) {
  if (!road.is_driveable) {
    return road.kind === "pedestrian" ? 5 : 3.2;
  }

  const laneWidth = 3.35;
  const base = Math.max(1, road.lanes) * laneWidth;

  if (road.kind === "motorway" || road.kind === "trunk") return Math.max(base, 16);
  if (road.kind === "primary") return Math.max(base, 13);
  if (road.kind === "secondary") return Math.max(base, 10);
  if (road.kind === "tertiary") return Math.max(base, 8.5);
  if (road.kind === "service") return Math.max(base, 5.5);

  return Math.max(base, 6.5);
}

function roadColor(road: Road, settings: SceneSettings) {
  if (settings.highlightRoadAccess && !road.is_driveable) {
    return "#b91c1c";
  }

  if (isTunnelFeature(road)) {
    return "#172033";
  }

  if (isBridgeFeature(road)) {
    return "#334155";
  }

  return "#263244";
}

function roadCongestionColor(road: Road, congestion: number, settings: SceneSettings) {
  if (!settings.highlightRoadCongestion || !road.is_driveable) {
    return null;
  }

  if (congestion > 0.72) return "#dc2626";
  if (congestion > 0.42) return "#f97316";
  if (congestion > 0.22) return "#ca8a04";

  return "#16a34a";
}

function clampNumber(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}

function surfaceColor(kind: string, settings: SceneSettings) {
  if (kind.includes("water")) return "#0e7490";

  if (kind.includes("sand") || kind.includes("beach")) return "#c9a45c";
  if (kind.includes("shingle")) return "#9ca3af";
  if (kind.includes("bare_rock")) return "#78716c";

  if (!settings.showSpecialZones) {
    if (kind.includes("residential")) return "#172033";
    if (kind.includes("commercial") || kind.includes("retail")) return "#172033";
    if (kind.includes("industrial")) return "#1f2937";
    if (kind.includes("parking")) return "#15803d";
    if (kind.includes("hospital")) return "#15803d";
    if (kind.includes("school")) return "#15803d";
    if (kind.includes("park")) return "#166534";
    if (kind.includes("forest") || kind.includes("wood")) return "#14532d";
    if (kind.includes("grass") || kind.includes("meadow") || kind.includes("recreation_ground")) return "#15803d";
    if (kind.includes("farmland") || kind.includes("orchard")) return "#4d7c0f";
    if (kind.includes("wetland")) return "#365314";
    return "#1f2937";
  }

  if (kind.includes("park")) return "#166534";
  if (kind.includes("forest") || kind.includes("wood")) return "#14532d";
  if (kind.includes("grass") || kind.includes("meadow") || kind.includes("recreation_ground")) return "#15803d";
  if (kind.includes("farmland") || kind.includes("orchard")) return "#4d7c0f";
  if (kind.includes("wetland")) return "#365314";
  if (kind.includes("parking")) return "#334155";
  if (kind.includes("hospital")) return "#7f1d1d";
  if (kind.includes("school")) return "#854d0e";
  if (kind.includes("commercial") || kind.includes("retail")) return "#312e81";
  if (kind.includes("industrial")) return "#3f3f46";
  if (kind.includes("residential")) return "#172033";
  if (kind.includes("aeroway")) return "#475569";
  if (kind.includes("area_highway")) return "#334155";

  return "#1f2937";
}
