import type { SimulationState, TrainingJob, TrainingMetricPoint } from "../types/domain";
import { LiveMetricChart } from "./LiveMetricChart";

type Props = {
  state: SimulationState | null;
  trainingJob: TrainingJob | null;
  metricHistory: TrainingMetricPoint[];
};

export function AIPanel({ state, trainingJob, metricHistory }: Props) {
  const problematic = state?.intersection_load
    .slice()
    .sort((a, b) => b.congestion_score - a.congestion_score)
    .slice(0, 5);

  return (
    <section className="panel-block">
      <h2>UrbanFlow AI</h2>

      {!state ? (
        <p className="muted">AI controller is waiting for simulation.</p>
      ) : (
        <>
          <div className="ai-status-banner">
            <span>Controller</span>
            <strong>{state.mode === "ai" ? "UrbanFlow AI active" : "Not active"}</strong>
            <small>
              {state.mode === "ai"
                ? "SUMO moves vehicles. UrbanFlow AI controls real SUMO traffic lights through TraCI."
                : "Switch to UrbanFlow AI control or start training to activate AI traffic-light control."}
            </small>
          </div>

          <div className="chart-grid">
            <LiveMetricChart
              title="Reward"
              points={metricHistory.map((point) => ({
                tick: point.tick,
                value: point.reward ?? 0
              }))}
            />

            <LiveMetricChart
              title="Load difficulty"
              points={metricHistory.map((point) => ({
                tick: point.tick,
                value: point.vehicles
              }))}
            />
          </div>

          {trainingJob && (
            <div className="list">
              <div className="list-item">
                <span>Training status</span>
                <strong>{trainingJob.status}</strong>
              </div>

              <div className="list-item">
                <span>Scope</span>
                <strong>{trainingJob.signal_scope}</strong>
              </div>

              <div className="list-item">
                <span>Curriculum</span>
                <strong>
                  {trainingJob.curriculum.start_vehicles} → {trainingJob.curriculum.max_vehicles}
                </strong>
              </div>

              <div className="list-item">
                <span>Checkpoint</span>
                <strong>{trainingJob.checkpoint_path ? "ready" : "not yet"}</strong>
              </div>
            </div>
          )}

          <h3>Problem intersections</h3>
          <div className="list">
            {problematic?.map((item) => (
              <div className="list-item" key={item.intersection_id}>
                <span>{item.intersection_id}</span>
                <strong>{Math.round(item.congestion_score * 100)}%</strong>
              </div>
            ))}
          </div>

          <h3>Active events</h3>
          <div className="list">
            {state.events.length === 0 && <p className="muted">No active events.</p>}
            {state.events.map((event) => (
              <div className="list-item" key={event.id}>
                <span>{event.kind}</span>
                <strong>{event.target_id ?? "city"}</strong>
              </div>
            ))}
          </div>
        </>
      )}
    </section>
  );
}