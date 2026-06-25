import { useEffect, useMemo, useRef, useState } from "react";
import {
  applyEditorPatch,
  createSimulation,
  importOsmArea,
  resetSimulation,
  setSimulationMode,
  stepSimulation,
  updateSimulationSettings
} from "./api/client";
import { AIPanel } from "./components/AIPanel";
import {
  buildClearEventPatch,
  buildEditorPatch,
  EditorPanel,
  type EditorAutomationSettings,
  type EditorTool
} from "./components/EditorPanel";
import { Header } from "./components/Header";
import { MapSelector } from "./components/MapSelector";
import { MetricsPanel } from "./components/MetricsPanel";
import { SideTab } from "./components/SideTab";
import { SimulationControls } from "./components/SimulationControls";
import { CityScene } from "./scene/CityScene";
import { SceneSettingsPanel } from "./components/SceneSettingsPanel";
import type { SceneSettings } from "./types/scene";
import type {
  BoundingBox,
  CityMap,
  Road,
  SimulationMode,
  SimulationSession,
  SimulationState
} from "./types/domain";

export function App() {
  const [bbox, setBbox] = useState<BoundingBox | null>(null);
  const [cityMap, setCityMap] = useState<CityMap | null>(null);
  const [session, setSession] = useState<SimulationSession | null>(null);
  const [state, setState] = useState<SimulationState | null>(null);
  const [mode, setMode] = useState<SimulationMode>("fixed");
  const [isRunning, setIsRunning] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [vehiclesCount, setVehiclesCount] = useState(160);
  const [pedestriansCount, setPedestriansCount] = useState(220);
  const [signalsOnAllIntersections, setSignalsOnAllIntersections] = useState(false);
  const [status, setStatus] = useState("Open Map, search a place and import real OSM data.");
  const [mapOpen, setMapOpen] = useState(false);
  const [mapMounted, setMapMounted] = useState(false);
  const [mapCenter, setMapCenter] = useState<[number, number]>([55.751244, 37.618423]);
  const [mapSelectedCenter, setMapSelectedCenter] = useState<[number, number]>([55.751244, 37.618423]);
  const [mapZoom, setMapZoom] = useState(15);
  const [mapQuery, setMapQuery] = useState("");
  const [mapAreaSizeText, setMapAreaSizeText] = useState("1000");
  const [isImporting, setIsImporting] = useState(false);
  const [mapError, setMapError] = useState<string | null>(null);
  const [simulationPanelOpen, setSimulationPanelOpen] = useState(false);
  const [editorPanelOpen, setEditorPanelOpen] = useState(false);
  const [settingsPanelOpen, setSettingsPanelOpen] = useState(false);
  const [sceneSettings, setSceneSettings] = useState<SceneSettings>({
    showBuildings: false,
    showSpecialZones: false,
    highlightRoadAccess: false,
    highlightRoadCongestion: false,
    showGroundZones: false
  });
  const [editorTool, setEditorTool] = useState<EditorTool>(null);
  const [editorSelectedRoad, setEditorSelectedRoad] = useState<Road | null>(null);
  const [editorAutomation, setEditorAutomation] = useState<EditorAutomationSettings>({
    closeRoads: {
      enabled: false,
      durationSeconds: 30,
      frequencySeconds: 60
    },
    accidents: {
      enabled: false,
      durationSeconds: 25,
      frequencySeconds: 45
    },
    roadworks: {
      enabled: false,
      durationSeconds: 60,
      frequencySeconds: 90
    }
  });
  const [rightPanelOpen, setRightPanelOpen] = useState(false);
  const [rightPanelMounted, setRightPanelMounted] = useState(false);

  const timerRef = useRef<number | null>(null);
  const drawerUnmountTimerRef = useRef<number | null>(null);
  const mapUnmountTimerRef = useRef<number | null>(null);
  const closeRoadAutomationRef = useRef<number | null>(null);
  const accidentAutomationRef = useRef<number | null>(null);
  const roadworkAutomationRef = useRef<number | null>(null);
  const delayedOpenRoadRefs = useRef<number[]>([]);
  const sessionId = session?.session_id ?? null;
  const selectedMap = useMemo(() => session?.city_map ?? cityMap, [cityMap, session]);

  function openMap() {
    if (mapUnmountTimerRef.current) {
      window.clearTimeout(mapUnmountTimerRef.current);
      mapUnmountTimerRef.current = null;
    }

    setMapError(null);
    setMapMounted(true);
    window.requestAnimationFrame(() => setMapOpen(true));
  }

  function closeMap() {
    if (isImporting) return;

    setMapOpen(false);

    if (mapUnmountTimerRef.current) {
      window.clearTimeout(mapUnmountTimerRef.current);
    }

    mapUnmountTimerRef.current = window.setTimeout(() => {
      setMapMounted(false);
      mapUnmountTimerRef.current = null;
    }, 300);
  }

  function openRightPanel() {
    if (drawerUnmountTimerRef.current) {
      window.clearTimeout(drawerUnmountTimerRef.current);
      drawerUnmountTimerRef.current = null;
    }

    setRightPanelMounted(true);
    window.requestAnimationFrame(() => setRightPanelOpen(true));
  }

  function closeRightPanel() {
    setRightPanelOpen(false);

    if (drawerUnmountTimerRef.current) {
      window.clearTimeout(drawerUnmountTimerRef.current);
    }

    drawerUnmountTimerRef.current = window.setTimeout(() => {
      setRightPanelMounted(false);
      drawerUnmountTimerRef.current = null;
    }, 280);
  }

  function toggleRightPanel() {
    if (rightPanelOpen) {
      closeRightPanel();
    } else {
      openRightPanel();
    }
  }

  async function handleImportOsm(selectedBbox: BoundingBox) {
    if (isImporting) return;

    setIsImporting(true);
    setMapError(null);
    setBbox(selectedBbox);
    setStatus("Importing selected OSM area...");

    try {
      const map = await importOsmArea(selectedBbox);

      setCityMap(map);
      setSession(null);
      setState(null);

      setStatus(
        `Imported from OSM: ${map.roads.length} roads, ${map.buildings.length} buildings, ${(map.surfaces ?? []).length} surfaces. Creating simulation...`
      );

      const created = await createSimulation({
        cityMap: map,
        mode,
        vehiclesCount,
        pedestriansCount,
        randomEventsEnabled: true,
        seed: 42,
        signalsOnAllIntersections
      });

      setSession(created);
      setState(created.state);
      setStatus("Selected OSM area generated and simulation created.");
      closeMap();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown OSM import error";

      setMapError(`Failed to generate selected area: ${message}`);
      setStatus(`OSM import failed: ${message}`);
    } finally {
      setIsImporting(false);
    }
  }

  async function handleStep(steps = speed) {
    if (!sessionId) return;
    const next = await stepSimulation(sessionId, steps);
    setState(next);
  }

  async function handleReset() {
    if (!sessionId) return;
    const next = await resetSimulation(sessionId);
    setState(next);
    setIsRunning(false);
  }

  async function handleModeChange(nextMode: SimulationMode) {
    setMode(nextMode);
    if (!sessionId) return;
    const next = await setSimulationMode(sessionId, nextMode);
    setState(next);
  }

  useEffect(() => {
    if (!isRunning || !sessionId) {
      if (timerRef.current) window.clearInterval(timerRef.current);
      timerRef.current = null;
      return;
    }

    timerRef.current = window.setInterval(() => {
      void handleStep(speed);
    }, 250);

    return () => {
      if (timerRef.current) window.clearInterval(timerRef.current);
    };
  }, [isRunning, sessionId, speed]);

  useEffect(() => {
    if (closeRoadAutomationRef.current) {
      window.clearInterval(closeRoadAutomationRef.current);
      closeRoadAutomationRef.current = null;
    }

    if (accidentAutomationRef.current) {
      window.clearInterval(accidentAutomationRef.current);
      accidentAutomationRef.current = null;
    }

    if (roadworkAutomationRef.current) {
      window.clearInterval(roadworkAutomationRef.current);
      roadworkAutomationRef.current = null;
    }

    if (sessionId && selectedMap && editorAutomation.closeRoads.enabled) {
      closeRoadAutomationRef.current = window.setInterval(() => {
        void applyRandomEditorPatch("close_road", editorAutomation.closeRoads.durationSeconds);
      }, editorAutomation.closeRoads.frequencySeconds * 1000);
    }

    if (sessionId && selectedMap && editorAutomation.accidents.enabled) {
      accidentAutomationRef.current = window.setInterval(() => {
        void applyRandomEditorPatch("accident", editorAutomation.accidents.durationSeconds);
      }, editorAutomation.accidents.frequencySeconds * 1000);
    }

    if (sessionId && selectedMap && editorAutomation.roadworks.enabled) {
      roadworkAutomationRef.current = window.setInterval(() => {
        void applyRandomEditorPatch("roadwork", editorAutomation.roadworks.durationSeconds);
      }, editorAutomation.roadworks.frequencySeconds * 1000);
    }

    return () => {
      if (closeRoadAutomationRef.current) {
        window.clearInterval(closeRoadAutomationRef.current);
        closeRoadAutomationRef.current = null;
      }

      if (accidentAutomationRef.current) {
        window.clearInterval(accidentAutomationRef.current);
        accidentAutomationRef.current = null;
      }

      if (roadworkAutomationRef.current) {
        window.clearInterval(roadworkAutomationRef.current);
        roadworkAutomationRef.current = null;
      }
    };
  }, [sessionId, selectedMap, editorAutomation]);

  useEffect(() => {
    return () => {
      if (drawerUnmountTimerRef.current) {
        window.clearTimeout(drawerUnmountTimerRef.current);
      }

      if (mapUnmountTimerRef.current) {
        window.clearTimeout(mapUnmountTimerRef.current);
      }
      for (const timer of delayedOpenRoadRefs.current) {
        window.clearTimeout(timer);
      }

      delayedOpenRoadRefs.current = [];
    };
  }, []);

  return (
    <div
      className={[
        "app-shell",
        rightPanelOpen ? "metrics-open" : "",
        rightPanelMounted ? "metrics-mounted" : "",
        mapOpen ? "map-open" : "",
        mapMounted ? "map-mounted map-mode" : ""
      ].join(" ")}
    >
      <Header />

      <main className="scene-panel">
        <CityScene
          cityMap={selectedMap}
          state={state}
          settings={sceneSettings}
          editorTool={editorTool}
          onRoadPick={(road, point) => void handleEditorRoadPick(road, point)}
          onRoadHover={setEditorSelectedRoad}
        />

        {!selectedMap && !mapMounted && (
          <div className="empty-scene-card">
            <img src="/logo.png" alt="UrbanFlow AI" />
            <h1>Select real OSM area</h1>
            <p>Open Map, search a place, select a square and import real OpenStreetMap data.</p>
          </div>
        )}
      </main>

      {!mapMounted && (
        <>
          <aside className="left-dock">
            <div className="dock-section dock-section-map">
              <SideTab
                label="Map"
                icon="map"
                active={mapOpen}
                expanded={false}
                onClick={openMap}
              />
            </div>

            <div className={["dock-section", simulationPanelOpen ? "dock-section-open" : ""].join(" ")}>
              <SideTab
                label="Simulation"
                icon="simulation"
                active={simulationPanelOpen}
                expanded={simulationPanelOpen}
                onClick={() => setSimulationPanelOpen((value) => !value)}
              />

              <div className="dock-panel-clip" aria-hidden={!simulationPanelOpen}>
                <div className="dock-panel">
                  <button
                    className="round-close round-close-right"
                    type="button"
                    onClick={() => setSimulationPanelOpen(false)}
                    aria-label="Close simulation panel"
                  >
                    ‹
                  </button>

                  <SimulationControls
                    isRunning={isRunning}
                    speed={speed}
                    mode={mode}
                    hasSession={Boolean(sessionId)}
                    vehiclesCount={vehiclesCount}
                    pedestriansCount={pedestriansCount}
                    signalsOnAllIntersections={signalsOnAllIntersections}
                    onSpeedChange={setSpeed}
                    onPlayPause={() => setIsRunning((value) => Boolean(sessionId) && !value)}
                    onReset={() => void handleReset()}
                    onModeChange={(nextMode) => void handleModeChange(nextMode)}
                    onVehiclesCountChange={setVehiclesCount}
                    onPedestriansCountChange={setPedestriansCount}
                    onSignalsOnAllIntersectionsChange={setSignalsOnAllIntersections}
                    onApplySimulationSettings={() => void handleApplySimulationSettings()}
                  />
                </div>
              </div>
            </div>

            <div className={["dock-section", editorPanelOpen ? "dock-section-open" : ""].join(" ")}>
              <SideTab
                label="Editor"
                icon="editor"
                active={editorPanelOpen}
                expanded={editorPanelOpen}
                onClick={() => setEditorPanelOpen((value) => !value)}
              />

              <div className="dock-panel-clip" aria-hidden={!editorPanelOpen}>
                <div className="dock-panel">
                  <button
                    className="round-close round-close-right"
                    type="button"
                    onClick={() => setEditorPanelOpen(false)}
                    aria-label="Close editor panel"
                  >
                    ‹
                  </button>

                  <EditorPanel
                    sessionId={sessionId}
                    cityMap={selectedMap}
                    selectedTool={editorTool}
                    selectedRoad={editorSelectedRoad}
                    automation={editorAutomation}
                    activeEvents={state?.events ?? []}
                    onToolChange={setEditorTool}
                    onAutomationChange={setEditorAutomation}
                    onClearEvent={(eventId) => void handleClearEditorEvent(eventId)}
                  />
                </div>
              </div>
            </div>

            <div className={["dock-section", settingsPanelOpen ? "dock-section-open" : ""].join(" ")}>
              <SideTab
                label="View"
                icon="settings"
                active={settingsPanelOpen}
                expanded={settingsPanelOpen}
                onClick={() => setSettingsPanelOpen((value) => !value)}
              />

              <div className="dock-panel-clip" aria-hidden={!settingsPanelOpen}>
                <div className="dock-panel">
                  <button
                    className="round-close round-close-right"
                    type="button"
                    onClick={() => setSettingsPanelOpen(false)}
                    aria-label="Close view settings panel"
                  >
                    ‹
                  </button>

                  <SceneSettingsPanel
                    settings={sceneSettings}
                    onChange={setSceneSettings}
                  />
                </div>
              </div>
            </div>
          </aside>

          <div className="right-dock-tab-wrap">
            <SideTab
              label="Metrics / AI"
              icon="metrics"
              side="right"
              active={rightPanelOpen}
              expanded={rightPanelOpen}
              onClick={toggleRightPanel}
            />
          </div>
        </>
      )}

      {mapMounted && (
        <div className="map-overlay">
          <MapSelector
            bbox={bbox}
            center={mapCenter}
            selectedCenter={mapSelectedCenter}
            zoom={mapZoom}
            query={mapQuery}
            areaSizeText={mapAreaSizeText}
            isImporting={isImporting}
            error={mapError}
            onBboxChange={setBbox}
            onCenterChange={setMapCenter}
            onSelectedCenterChange={setMapSelectedCenter}
            onZoomChange={setMapZoom}
            onQueryChange={setMapQuery}
            onAreaSizeTextChange={setMapAreaSizeText}
            onImportOsm={(selectedBbox) => void handleImportOsm(selectedBbox)}
            onClose={closeMap}
          />
        </div>
      )}

      {!mapMounted && rightPanelMounted && (
        <aside className="metrics-drawer">
          <button
            className="round-close round-close-left"
            type="button"
            onClick={closeRightPanel}
            aria-label="Close metrics panel"
          >
            ›
          </button>

          <div className="metrics-drawer-content">
            <MetricsPanel state={state} cityMap={selectedMap} />
            <AIPanel state={state} />
          </div>
        </aside>
      )}
    </div>
  );

  async function handleApplySimulationSettings() {
    if (!sessionId) {
      setStatus("Generate OSM area first.");
      return;
    }

    setStatus("Updating simulation objects and traffic lights...");

    try {
      const next = await updateSimulationSettings(sessionId, {
        vehiclesCount,
        pedestriansCount,
        signalsOnAllIntersections
      });

      setState(next);
      setStatus(
        `Simulation updated: ${vehiclesCount} vehicles, ${pedestriansCount} pedestrians, ${
          signalsOnAllIntersections ? "signals on all intersections" : "OSM signals only"
        }.`
      );
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown simulation settings error";
      setStatus(`Simulation settings failed: ${message}`);
    }
  }

  async function handleEditorRoadPick(
    road: Road,
    point: {
      progress: number;
      x: number;
      z: number;
    }
  ) {
    if (!sessionId || !editorTool) return;

    setSceneSettings((current) => ({
      ...current,
      highlightRoadAccess: true
    }));

    const durationSeconds =
      editorTool === "roadwork"
        ? editorAutomation.roadworks.durationSeconds
        : editorTool === "accident"
          ? editorAutomation.accidents.durationSeconds
          : editorAutomation.closeRoads.durationSeconds;

    const patch = buildEditorPatch(editorTool, road, durationSeconds, point);

    await applyEditorPatch(sessionId, patch);

    if (editorTool === "close_road") {
      const openTimer = window.setTimeout(() => {
        void applyEditorPatch(sessionId, buildEditorPatch("open_road", road, durationSeconds));
      }, durationSeconds * 1000);

      delayedOpenRoadRefs.current.push(openTimer);
    }

    const next = await stepSimulation(sessionId, 1);
    setState(next);
  }

  async function handleClearEditorEvent(eventId: string) {
    if (!sessionId) return;

    await applyEditorPatch(sessionId, buildClearEventPatch(eventId));

    const next = await stepSimulation(sessionId, 1);
    setState(next);
    setStatus("Editor event removed.");
  }

  async function applyRandomEditorPatch(kind: "close_road" | "accident" | "roadwork", durationSeconds: number) {
    if (!sessionId || !selectedMap) return;
    
    setSceneSettings((current) => ({
      ...current,
      highlightRoadAccess: true
    }));

    const roads = selectedMap.roads.filter((road) => road.is_driveable && road.coordinates.length >= 2);
    if (!roads.length) return;

    const road = roads[Math.floor(Math.random() * roads.length)];
    const progress = Math.random() * 0.75 + 0.125;
    const point = pointOnRoad(road, progress);
    const patch = buildEditorPatch(kind, road, durationSeconds, point);

    await applyEditorPatch(sessionId, patch);

    if (kind === "close_road") {
      const openTimer = window.setTimeout(() => {
        void applyEditorPatch(sessionId, buildEditorPatch("open_road", road, durationSeconds));
      }, durationSeconds * 1000);

      delayedOpenRoadRefs.current.push(openTimer);
    }

    const next = await stepSimulation(sessionId, 1);
    setState(next);
  }

  function pointOnRoad(road: Road, progress: number) {
    if (road.coordinates.length < 2) {
      return {
        progress,
        x: 0,
        z: 0
      };
    }

    const segmentIndex = Math.min(
      road.coordinates.length - 2,
      Math.max(0, Math.floor(progress * (road.coordinates.length - 1)))
    );

    const segmentProgress = progress * (road.coordinates.length - 1) - segmentIndex;
    const start = road.coordinates[segmentIndex];
    const end = road.coordinates[segmentIndex + 1];

    return {
      progress,
      x: start.x + (end.x - start.x) * segmentProgress,
      z: start.z + (end.z - start.z) * segmentProgress
    };
  }

}