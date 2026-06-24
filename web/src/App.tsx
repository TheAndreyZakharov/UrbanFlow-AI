import { useEffect, useMemo, useRef, useState } from "react";
import {
  createSimulation,
  importOsmArea,
  resetSimulation,
  setSimulationMode,
  stepSimulation
} from "./api/client";
import { AIPanel } from "./components/AIPanel";
import { EditorPanel } from "./components/EditorPanel";
import { Header } from "./components/Header";
import { MapSelector } from "./components/MapSelector";
import { MetricsPanel } from "./components/MetricsPanel";
import { SideTab } from "./components/SideTab";
import { SimulationControls } from "./components/SimulationControls";
import { CityScene } from "./scene/CityScene";
import type {
  BoundingBox,
  CityMap,
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
  const [status, setStatus] = useState("Open Map, search a place and import real OSM data.");
  const [mapOpen, setMapOpen] = useState(false);
  const [mapMounted, setMapMounted] = useState(false);
  const [simulationPanelOpen, setSimulationPanelOpen] = useState(false);
  const [editorPanelOpen, setEditorPanelOpen] = useState(false);
  const [rightPanelOpen, setRightPanelOpen] = useState(false);
  const [rightPanelMounted, setRightPanelMounted] = useState(false);

  const timerRef = useRef<number | null>(null);
  const drawerUnmountTimerRef = useRef<number | null>(null);
  const mapUnmountTimerRef = useRef<number | null>(null);

  const sessionId = session?.session_id ?? null;
  const selectedMap = useMemo(() => session?.city_map ?? cityMap, [cityMap, session]);

  function openMap() {
    if (mapUnmountTimerRef.current) {
      window.clearTimeout(mapUnmountTimerRef.current);
      mapUnmountTimerRef.current = null;
    }

    setMapMounted(true);
    window.requestAnimationFrame(() => setMapOpen(true));
  }

  function closeMap() {
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
    setBbox(selectedBbox);
    setStatus("Importing real OSM data...");

    const map = await importOsmArea(selectedBbox);

    setCityMap(map);
    setSession(null);
    setState(null);
    setStatus(`Imported from OSM: ${map.roads.length} roads, ${map.buildings.length} buildings.`);
    closeMap();
    setSimulationPanelOpen(true);
  }

  async function handleCreateSimulation() {
    if (!cityMap) {
      setStatus("Import OSM area first.");
      openMap();
      return;
    }

    setStatus("Creating simulation from imported OSM city map...");
    const created = await createSimulation({
      cityMap,
      mode,
      vehiclesCount: 160,
      pedestriansCount: 220,
      randomEventsEnabled: true,
      seed: 42
    });

    setSession(created);
    setState(created.state);
    setStatus("Simulation created.");
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
    return () => {
      if (drawerUnmountTimerRef.current) {
        window.clearTimeout(drawerUnmountTimerRef.current);
      }

      if (mapUnmountTimerRef.current) {
        window.clearTimeout(mapUnmountTimerRef.current);
      }
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
        <CityScene cityMap={selectedMap} state={state} />

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
                    hasCityMap={Boolean(cityMap)}
                    onSpeedChange={setSpeed}
                    onPlayPause={() => setIsRunning((value) => !value)}
                    onStep={() => void handleStep(1)}
                    onReset={() => void handleReset()}
                    onModeChange={(nextMode) => void handleModeChange(nextMode)}
                    onCreateSimulation={() => void handleCreateSimulation()}
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
                    onPatchApplied={async () => {
                      if (sessionId) {
                        const next = await stepSimulation(sessionId, 1);
                        setState(next);
                      }
                    }}
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
            onBboxChange={setBbox}
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
}