import type { SimulationMode } from "../types/domain";
import type { TrafficLightOverride } from "../api/client";

type Props = {
  isRunning: boolean;
  speed: number;
  mode: SimulationMode;
  hasSession: boolean;
  vehiclesCount: number;
  pedestriansCount: number;
  signalsOnAllIntersections: boolean;
  trafficLightOverride: TrafficLightOverride;
  onSpeedChange: (speed: number) => void;
  onPlayPause: () => void;
  onReset: () => void;
  onModeChange: (mode: SimulationMode) => void;
  onVehiclesCountChange: (count: number) => void;
  onPedestriansCountChange: (count: number) => void;
  onSignalsOnAllIntersectionsChange: (enabled: boolean) => void;
  onTrafficLightOverrideChange: (override: TrafficLightOverride) => void;
  onApplySimulationSettings: () => void;
};

export function SimulationControls({
  isRunning,
  speed,
  mode,
  hasSession,
  vehiclesCount,
  pedestriansCount,
  signalsOnAllIntersections,
  trafficLightOverride,
  onTrafficLightOverrideChange,
  onSpeedChange,
  onPlayPause,
  onReset,
  onModeChange,
  onVehiclesCountChange,
  onPedestriansCountChange,
  onSignalsOnAllIntersectionsChange,
  onApplySimulationSettings
}: Props) {
  return (
    <section className="panel-block">
      <h2>Simulation</h2>
      <p className="muted">Start, pause and tune the SUMO-powered city simulation.</p>

      <div className="button-row button-row-two">
        <button disabled={!hasSession} onClick={onPlayPause}>
          {isRunning ? "Pause" : "Start"}
        </button>

        <button disabled={!hasSession} onClick={onReset}>
          Reset
        </button>
      </div>

      <label>
        Speed x{speed}
        <input
          type="range"
          min={1}
          max={20}
          value={speed}
          onChange={(event) => onSpeedChange(Number(event.target.value))}
        />
      </label>

      <div className="simulation-count-grid">
        <label>
          Vehicles
          <input
            type="number"
            min={0}
            max={5000}
            value={vehiclesCount}
            onChange={(event) => onVehiclesCountChange(clampCount(Number(event.target.value), 0, 5000))}
          />
        </label>

        <label>
          Pedestrians
          <input
            type="number"
            min={0}
            max={10000}
            value={pedestriansCount}
            onChange={(event) => onPedestriansCountChange(clampCount(Number(event.target.value), 0, 10000))}
          />
        </label>
      </div>

      <label className="settings-toggle-row">
        <span className="settings-toggle-copy">
          <strong>Signals on all intersections</strong>
          <small>Off: only real OSM traffic lights. On: every intersection gets a signal.</small>
        </span>

        <input
          type="checkbox"
          checked={signalsOnAllIntersections}
          onChange={(event) => onSignalsOnAllIntersectionsChange(event.target.checked)}
        />

        <span className="settings-toggle-switch" aria-hidden="true" />
      </label>

      <button disabled={!hasSession} onClick={onApplySimulationSettings}>
        Apply counts and signals
      </button>
      <div className="button-row button-row-two">
        <button
          disabled={!hasSession}
          className={trafficLightOverride === "sumo" ? "active" : ""}
          onClick={() => onTrafficLightOverrideChange("sumo")}
        >
          SUMO auto
        </button>

        <button
          disabled={!hasSession}
          className={trafficLightOverride === "red" ? "active" : ""}
          onClick={() => onTrafficLightOverrideChange("red")}
        >
          All red
        </button>
      </div>

      <div className="button-row button-row-two">
        <button
          disabled={!hasSession}
          className={trafficLightOverride === "yellow" ? "active" : ""}
          onClick={() => onTrafficLightOverrideChange("yellow")}
        >
          All yellow
        </button>

        <button
          disabled={!hasSession}
          className={trafficLightOverride === "green" ? "active" : ""}
          onClick={() => onTrafficLightOverrideChange("green")}
        >
          All green
        </button>
      </div>
      <label>
        Traffic light controller
        <select value={mode} onChange={(event) => onModeChange(event.target.value as SimulationMode)}>
          <option value="rule_based">SUMO automatic control</option>
          <option value="fixed">Manual fixed cycle</option>
          <option value="ai">UrbanFlow AI control — latest saved model</option>
        </select>
      </label>
    </section>
  );
}

function clampCount(value: number, min: number, max: number) {
  if (!Number.isFinite(value)) return min;
  return Math.max(min, Math.min(max, Math.round(value)));
}