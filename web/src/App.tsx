import { useEffect, useMemo, useRef, useState } from "react";
import {
  applyEditorPatch,
  createSimulation,
  getSimulationState,
  importOsmArea,
  resetSimulation,
  setSimulationMode,
  stepSimulation,
  updateSimulationSettings,
  setTrafficLightOverride,
  startTraining,
  stopTraining,
  getTrainingJob,
  saveTrainingModel,
  exportTrainingModel,
  listTrainingModels,
  deleteTrainingModel,
  type TrafficLightOverride
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
import { TrainingPanel } from "./components/TrainingPanel";
import { ModelRegistryPanel } from "./components/ModelRegistryPanel";
import { CityScene } from "./scene/CityScene";
import { SceneSettingsPanel } from "./components/SceneSettingsPanel";
import type { SceneSettings } from "./types/scene";
import type {
  BoundingBox,
  CityMap,
  Road,
  SimulationMode,
  SimulationSession,
  SavedTrainingModel,
  SimulationState,
  TrainingCurriculum,
  TrainingJob,
  TrainingMetricPoint,
  TrainingModelFormat,
  TrainingSignalScope
} from "./types/domain";

export function App() {
  const [bbox, setBbox] = useState<BoundingBox | null>(null);
  const [cityMap, setCityMap] = useState<CityMap | null>(null);
  const [session, setSession] = useState<SimulationSession | null>(null);
  const [state, setState] = useState<SimulationState | null>(null);
  const [mode, setMode] = useState<SimulationMode>("rule_based");
  const [isRunning, setIsRunning] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [vehiclesCount, setVehiclesCount] = useState(160);
  const [pedestriansCount, setPedestriansCount] = useState(220);
  const [signalsOnAllIntersections, setSignalsOnAllIntersections] = useState(false);
  const [trafficLightOverride, setTrafficLightOverrideState] = useState<TrafficLightOverride>("sumo");
  const [status, setStatus] = useState("Open Map, search a place and import real OSM data.");
  const [mapOpen, setMapOpen] = useState(false);
  const [mapMounted, setMapMounted] = useState(false);
  const [mapCenter, setMapCenter] = useState<[number, number]>([20.0, 0.0]);
  const [mapSelectedCenter, setMapSelectedCenter] = useState<[number, number]>([20.0, 0.0]);
  const [mapZoom, setMapZoom] = useState(2);
  const [mapQuery, setMapQuery] = useState("");
  const [mapAreaSizeText, setMapAreaSizeText] = useState("1000");
  const [isImporting, setIsImporting] = useState(false);
  const [mapError, setMapError] = useState<string | null>(null);
  const [simulationPanelOpen, setSimulationPanelOpen] = useState(false);
  const [editorPanelOpen, setEditorPanelOpen] = useState(false);
  const [settingsPanelOpen, setSettingsPanelOpen] = useState(false);
  const [trainingPanelOpen, setTrainingPanelOpen] = useState(false);
  const [trainingSignalScope, setTrainingSignalScope] = useState<TrainingSignalScope>("osm_only");
  const [trainingJob, setTrainingJob] = useState<TrainingJob | null>(null);
  const [trainingBusy, setTrainingBusy] = useState(false);
  const [savedModels, setSavedModels] = useState<SavedTrainingModel[]>([]);
  const [metricHistory, setMetricHistory] = useState<TrainingMetricPoint[]>([]);
  const [trainingCurriculum, setTrainingCurriculum] = useState<TrainingCurriculum>({
    start_vehicles: 60,
    max_vehicles: 800,
    vehicle_step: 80,
    steps_per_level: 900,
    pedestrians_count: 220,
    random_events_enabled: true
  });
  const [sceneSettings, setSceneSettings] = useState<SceneSettings>({
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
  const isRunningRef = useRef(false);
  const stepInFlightRef = useRef(false);
  const requestSerialRef = useRef(0);
  const drawerUnmountTimerRef = useRef<number | null>(null);
  const mapUnmountTimerRef = useRef<number | null>(null);
  const closeRoadAutomationRef = useRef<number | null>(null);
  const accidentAutomationRef = useRef<number | null>(null);
  const roadworkAutomationRef = useRef<number | null>(null);
  const delayedOpenRoadRefs = useRef<number[]>([]);
  const sessionId = session?.session_id ?? null;
  const selectedMap = useMemo(() => session?.city_map ?? cityMap, [cityMap, session]);
  function applyState(next: SimulationState) {
    setState(next);

    setMetricHistory((current) => {
      const point: TrainingMetricPoint = {
        tick: next.tick,
        speed: next.metrics.average_speed_mps,
        wait: next.metrics.average_vehicle_wait_time,
        congestion: next.metrics.congestion_score,
        stopped: next.metrics.stopped_vehicles,
        vehicles: next.metrics.active_vehicles,
        pedestrians: next.metrics.active_pedestrians,
        reward: trainingJob?.latest_reward ?? null
      };

      const updated = [...current, point];

      return updated.slice(-240);
    });
  }

  function stopSimulationLoop() {
    requestSerialRef.current += 1;
    isRunningRef.current = false;
    stepInFlightRef.current = false;
    setIsRunning(false);

    if (timerRef.current) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }

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

    stopSimulationLoop();
    setIsImporting(true);
    setMapError(null);
    setBbox(selectedBbox);
    setStatus("Importing selected OSM area...");

    try {
      const map = await importOsmArea(selectedBbox);

      setCityMap(map);
      setSession(null);
      setState(null);
      setTrainingJob(null);
      setSavedModels([]);
      setMetricHistory([]);
      setTrainingSignalScope(signalsOnAllIntersections ? "all_intersections" : "osm_only");

      setStatus(
        `Imported from OSM: ${map.roads.length} roads, ${map.buildings.length} buildings, ${(map.surfaces ?? []).length} surfaces. Creating simulation...`
      );
      setMode("rule_based");
      setTrafficLightOverrideState("sumo");

      const created = await createSimulation({
        cityMap: map,
        mode: "rule_based",
        vehiclesCount,
        pedestriansCount,
        randomEventsEnabled: true,
        seed: 42,
        signalsOnAllIntersections
      });

      setSession(created);
      applyState(created.state);
      setStatus("Selected OSM area generated and simulation created.");
      void refreshSavedModels();
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

    const serial = requestSerialRef.current;
    const next = await stepSimulation(sessionId, steps);

    if (serial !== requestSerialRef.current) {
      return;
    }

    applyState(next);
  }

  async function handleReset() {
    if (!sessionId) return;

    stopSimulationLoop();

    const serial = requestSerialRef.current;
    const next = await resetSimulation(sessionId);

    if (serial !== requestSerialRef.current) {
      return;
    }

    applyState(next);
    setMetricHistory([]);
    setIsRunning(false);
  }

  function handlePlayPause() {
    if (!sessionId) return;

    setIsRunning((current) => {
      const next = !current;
      isRunningRef.current = next;

      if (!next && timerRef.current) {
        window.clearTimeout(timerRef.current);
        timerRef.current = null;
      }

      return next;
    });
  }

  async function handleModeChange(nextMode: SimulationMode) {
    setMode(nextMode);

    if (nextMode !== "ai") {
      setTrainingJob(null);
    }

    if (!sessionId) return;

    const next = await setSimulationMode(sessionId, nextMode);
    applyState(next);
  }

  useEffect(() => {
    isRunningRef.current = isRunning;

    if (!isRunning || !sessionId) {
      if (timerRef.current) {
        window.clearTimeout(timerRef.current);
        timerRef.current = null;
      }

      return;
    }

    let cancelled = false;

    async function simulationLoop() {
      if (cancelled || !isRunningRef.current || !sessionId) {
        return;
      }

      if (!stepInFlightRef.current) {
        stepInFlightRef.current = true;

        try {
          await handleStep(speed);
        } finally {
          stepInFlightRef.current = false;
        }
      }

      if (!cancelled && isRunningRef.current) {
        timerRef.current = window.setTimeout(simulationLoop, 110);
      }
    }

    timerRef.current = window.setTimeout(simulationLoop, 0);

    return () => {
      cancelled = true;

      if (timerRef.current) {
        window.clearTimeout(timerRef.current);
        timerRef.current = null;
      }
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
    if (!trainingJob || trainingJob.status !== "running") {
      return;
    }

    let cancelled = false;

    const timer = window.setInterval(() => {
      void (async () => {
        try {
          const next = await getTrainingJob(trainingJob.id);

          if (cancelled) {
            return;
          }

          setTrainingJob(next);
        } catch {
          if (!cancelled) {
            setTrainingJob((current) =>
              current
                ? {
                    ...current,
                    status: "failed",
                    message: "Training status polling failed."
                  }
                : current
            );
          }
        }
      })();
    }, 1200);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [trainingJob?.id, trainingJob?.status]);

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
                    trafficLightOverride={trafficLightOverride}
                    onSpeedChange={setSpeed}
                    onPlayPause={handlePlayPause}
                    onReset={() => void handleReset()}
                    onModeChange={(nextMode) => void handleModeChange(nextMode)}
                    onVehiclesCountChange={setVehiclesCount}
                    onPedestriansCountChange={setPedestriansCount}
                    onSignalsOnAllIntersectionsChange={(enabled) => {
                      setSignalsOnAllIntersections(enabled);
                      setTrainingSignalScope(enabled ? "all_intersections" : "osm_only");
                    }}
                    onTrafficLightOverrideChange={(override) => void handleTrafficLightOverrideChange(override)}
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

            <div className={["dock-section", trainingPanelOpen ? "dock-section-open" : ""].join(" ")}>
              <SideTab
                label="Training"
                icon="training"
                active={trainingPanelOpen}
                expanded={trainingPanelOpen}
                onClick={() => setTrainingPanelOpen((value) => !value)}
              />

              <div className="dock-panel-clip" aria-hidden={!trainingPanelOpen}>
                <div className="dock-panel">
                  <button
                    className="round-close round-close-right"
                    type="button"
                    onClick={() => setTrainingPanelOpen(false)}
                    aria-label="Close training panel"
                  >
                    ‹
                  </button>

                  <TrainingPanel
                    hasSession={Boolean(sessionId)}
                    signalScope={trainingSignalScope}
                    curriculum={trainingCurriculum}
                    job={trainingJob}
                    isBusy={trainingBusy}
                    onSignalScopeChange={setTrainingSignalScope}
                    onCurriculumChange={setTrainingCurriculum}
                    onStartTraining={() => void handleStartTraining()}
                    onStopTraining={() => void handleStopTraining()}
                    onSaveModel={() => void handleSaveTrainingModel()}
                    onExportModel={(format) => void handleExportTrainingModel(format)}
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
            <MetricsPanel
              state={state}
              cityMap={selectedMap}
              trainingJob={trainingJob}
              metricHistory={metricHistory}
            />

            <AIPanel
              state={state}
              trainingJob={trainingJob}
              metricHistory={metricHistory}
            />

            <ModelRegistryPanel
              job={trainingJob}
              models={savedModels}
              isBusy={trainingBusy}
              onRefresh={() => void refreshSavedModels()}
              onDeleteModel={(modelId) => void handleDeleteTrainingModel(modelId)}
            />
          </div>
        </aside>
      )}
    </div>
  );

  async function handleTrafficLightOverrideChange(override: TrafficLightOverride) {
    if (!sessionId) return;

    setTrafficLightOverrideState(override);

    try {
      const next = await setTrafficLightOverride(sessionId, override);
      setState(next);

      if (override === "sumo") {
        setMode("rule_based");
        setStatus("Traffic lights returned to SUMO automatic control.");
      } else {
        setStatus(`Traffic lights forced to ${override} while simulation is running.`);
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown traffic light override error";
      setStatus(`Traffic light override failed: ${message}`);
    }
  }

  async function handleApplySimulationSettings() {
    if (!sessionId) {
      setStatus("Generate OSM area first.");
      return;
    }

    stopSimulationLoop();
    setStatus("Updating simulation objects and traffic lights...");

    try {
      const next = await updateSimulationSettings(sessionId, {
        vehiclesCount,
        pedestriansCount,
        signalsOnAllIntersections
      });

      applyState(next);
      setMetricHistory([]);
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

    stopSimulationLoop();

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
    const serial = requestSerialRef.current;

    try {
      await applyEditorPatch(sessionId, patch);

      const next = await getSimulationState(sessionId);

      if (serial !== requestSerialRef.current) {
        return;
      }

      applyState(next);
      setStatus(`Editor applied: ${editorTool} on ${road.name ?? road.id}.`);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown editor error";
      setStatus(`Editor action failed: ${message}`);
    }
  }

  async function handleClearEditorEvent(eventId: string) {
    if (!sessionId) return;

    stopSimulationLoop();

    const serial = requestSerialRef.current;

    try {
      await applyEditorPatch(sessionId, buildClearEventPatch(eventId));

      const next = await getSimulationState(sessionId);

      if (serial !== requestSerialRef.current) {
        return;
      }

      applyState(next);
      setStatus("Editor event removed.");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown editor error";
      setStatus(`Remove editor event failed: ${message}`);
    }
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

    patch.payload = {
      ...patch.payload,
      duration_ticks: Math.max(1, Math.round(durationSeconds * 4)),
      duration_seconds: durationSeconds,
      manual: false
    };

    await applyEditorPatch(sessionId, patch);

    if (kind === "close_road") {
      const openTimer = window.setTimeout(() => {
        void applyEditorPatch(sessionId, buildEditorPatch("open_road", road, durationSeconds));
      }, durationSeconds * 1000);

      delayedOpenRoadRefs.current.push(openTimer);
    }
    
    const next = await getSimulationState(sessionId);
    applyState(next);
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

  async function handleStartTraining() {
    if (!sessionId) {
      setStatus("Generate OSM area first.");
      return;
    }

    stopSimulationLoop();
    setTrainingBusy(true);
    setStatus("Preparing UrbanFlow AI training on this zone...");

    try {
      const job = await startTraining({
        sessionId,
        signalScope: trainingSignalScope,
        curriculum: trainingCurriculum
      });

      setTrainingJob(job);
      setMode("ai");
      setTrafficLightOverrideState("sumo");
      setSignalsOnAllIntersections(trainingSignalScope === "all_intersections");
      setVehiclesCount(trainingCurriculum.start_vehicles);
      setPedestriansCount(trainingCurriculum.pedestrians_count);

      const next = await getSimulationState(sessionId);
      applyState(next);
      setMetricHistory([]);
      void refreshSavedModels();

      requestSerialRef.current += 1;
      isRunningRef.current = true;
      setIsRunning(true);

      setStatus(
        `UrbanFlow AI training running visually: ${
          trainingSignalScope === "all_intersections" ? "all intersections" : "OSM traffic lights only"
        }.`
      );
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown training error";
      setStatus(`Training start failed: ${message}`);
    } finally {
      setTrainingBusy(false);
    }
  }
  
  async function handleStopTraining() {
    if (!trainingJob) return;

    setTrainingBusy(true);
    setStatus("Stopping UrbanFlow AI training...");

    try {
      const stopped = await stopTraining(trainingJob.id);
      setTrainingJob(stopped);
      stopSimulationLoop();

      if (sessionId) {
        const next = await getSimulationState(sessionId);
        applyState(next);
      }

      setStatus("UrbanFlow AI training stopped.");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown training error";
      setStatus(`Training stop failed: ${message}`);
    } finally {
      setTrainingBusy(false);
    }
  }

  async function refreshSavedModels() {
    try {
      const models = await listTrainingModels();
      setSavedModels(models);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown model registry error";
      setStatus(`Model registry refresh failed: ${message}`);
    }
  }

  async function handleSaveTrainingModel() {
    if (!trainingJob) return;

    setTrainingBusy(true);
    setStatus("Saving trained UrbanFlow AI model...");

    try {
      const saved = await saveTrainingModel({
        jobId: trainingJob.id,
        label: `UrbanFlow ${trainingJob.signal_scope} ${new Date().toLocaleString()}`,
        notes: `Saved from job ${trainingJob.id}`
      });

      await refreshSavedModels();

      const nextJob = await getTrainingJob(trainingJob.id);
      setTrainingJob(nextJob);

      setStatus(`Model saved: ${saved.label}`);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown save model error";
      setStatus(`Save model failed: ${message}`);
    } finally {
      setTrainingBusy(false);
    }
  }

  async function handleExportTrainingModel(format: TrainingModelFormat) {
    if (!trainingJob) return;

    setTrainingBusy(true);
    setStatus(`Exporting UrbanFlow AI model as ${format}...`);

    try {
      const exported = await exportTrainingModel({
        jobId: trainingJob.id,
        format
      });

      await refreshSavedModels();

      setStatus(`Model export ready: ${exported.path}`);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown export model error";
      setStatus(`Export model failed: ${message}`);
    } finally {
      setTrainingBusy(false);
    }
  }

  async function handleDeleteTrainingModel(modelId: string) {
    setTrainingBusy(true);
    setStatus("Deleting saved model...");

    try {
      await deleteTrainingModel(modelId);
      await refreshSavedModels();
      setStatus("Saved model deleted.");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown delete model error";
      setStatus(`Delete model failed: ${message}`);
    } finally {
      setTrainingBusy(false);
    }
  }







}