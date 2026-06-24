import type { SimulationMode } from "../types/domain";

type Props = {
  isRunning: boolean;
  speed: number;
  mode: SimulationMode;
  hasSession: boolean;
  hasCityMap: boolean;
  onSpeedChange: (speed: number) => void;
  onPlayPause: () => void;
  onStep: () => void;
  onReset: () => void;
  onModeChange: (mode: SimulationMode) => void;
  onCreateSimulation: () => void;
};

export function SimulationControls({
  isRunning,
  speed,
  mode,
  hasSession,
  hasCityMap,
  onSpeedChange,
  onPlayPause,
  onStep,
  onReset,
  onModeChange,
  onCreateSimulation
}: Props) {
  return (
    <section className="panel-block">
      <h2>Simulation Controls</h2>
      <p className="muted">Create and control traffic simulation from imported OSM data.</p>

      <button disabled={!hasCityMap} onClick={onCreateSimulation}>
        Create simulation from OSM
      </button>

      <div className="button-row">
        <button disabled={!hasSession} onClick={onPlayPause}>
          {isRunning ? "Pause" : "Play"}
        </button>
        <button disabled={!hasSession} onClick={onStep}>
          Step
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

      <label>
        Controller mode
        <select value={mode} onChange={(event) => onModeChange(event.target.value as SimulationMode)}>
          <option value="fixed">Fixed timings</option>
          <option value="rule_based">Rule-based</option>
          <option value="ai">AI controller</option>
        </select>
      </label>
    </section>
  );
}