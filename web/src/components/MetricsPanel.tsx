import type { CityMap, SimulationState, TrainingJob, TrainingMetricPoint } from "../types/domain";
import { formatNumber, formatSpeed } from "../utils/format";
import { LiveMetricChart } from "./LiveMetricChart";

type Props = {
  state: SimulationState | null;
  cityMap: CityMap | null;
  trainingJob: TrainingJob | null;
  metricHistory: TrainingMetricPoint[];
};

export function MetricsPanel({ state, cityMap, trainingJob, metricHistory }: Props) {
  const topRoads = state?.road_load
    .slice()
    .sort((a, b) => b.congestion_score - a.congestion_score)
    .slice(0, 6);

  const topIntersections = state?.intersection_load
    .slice()
    .sort((a, b) => b.congestion_score - a.congestion_score)
    .slice(0, 6);

  return (
    <section className="panel-block">
      <h2>Live metrics</h2>

      {!state ? (
        <p className="muted">No simulation running.</p>
      ) : (
        <>
          <div className="metrics-grid">
            <Metric label="Tick" value={state.tick.toString()} />
            <Metric label="Mode" value={state.mode} />
            <Metric label="Vehicles" value={state.metrics.active_vehicles.toString()} />
            <Metric label="Pedestrians" value={state.metrics.active_pedestrians.toString()} />
            <Metric label="Signals" value={state.signals.length.toString()} />
            <Metric label="Avg speed" value={formatSpeed(state.metrics.average_speed_mps)} />
            <Metric label="Vehicle wait" value={`${formatNumber(state.metrics.average_vehicle_wait_time)}s`} />
            <Metric label="Pedestrian wait" value={`${formatNumber(state.metrics.average_pedestrian_wait_time)}s`} />
            <Metric label="Congestion" value={`${formatNumber(state.metrics.congestion_score * 100)}%`} />
            <Metric label="Stopped" value={state.metrics.stopped_vehicles.toString()} />
            <Metric label="Events" value={state.metrics.active_events.toString()} />
            <Metric label="Throughput" value={state.metrics.throughput.toString()} />
          </div>

          <div className="chart-grid">
            <LiveMetricChart
              title="Average speed"
              suffix=" m/s"
              points={metricHistory.map((point) => ({
                tick: point.tick,
                value: point.speed
              }))}
            />

            <LiveMetricChart
              title="Vehicle wait"
              suffix=" s"
              points={metricHistory.map((point) => ({
                tick: point.tick,
                value: point.wait
              }))}
            />

            <LiveMetricChart
              title="Congestion"
              suffix="%"
              points={metricHistory.map((point) => ({
                tick: point.tick,
                value: point.congestion * 100
              }))}
            />

            <LiveMetricChart
              title="Stopped vehicles"
              points={metricHistory.map((point) => ({
                tick: point.tick,
                value: point.stopped
              }))}
            />
          </div>

          <div className="comparison-card">
            <h3>Controller comparison</h3>

            <div className="comparison-grid">
              <ComparisonItem label="SUMO auto" active={state.mode === "rule_based"} />
              <ComparisonItem label="Fixed cycle" active={state.mode === "fixed"} />
              <ComparisonItem label="UrbanFlow AI" active={state.mode === "ai"} />
            </div>

            <p className="muted">
              Full benchmark comparison will use the same zone and replay settings for SUMO auto, fixed timing and trained UrbanFlow AI.
            </p>
          </div>

          {trainingJob && (
            <div className="training-summary-card">
              <h3>Training run</h3>

              <div className="metrics-grid">
                <Metric label="Status" value={trainingJob.status} />
                <Metric label="Scope" value={trainingJob.signal_scope} />
                <Metric label="Episode" value={trainingJob.current_episode.toString()} />
                <Metric label="Step" value={trainingJob.current_step.toString()} />
                <Metric label="Vehicles" value={trainingJob.current_vehicles.toString()} />
                <Metric label="Best reward" value={formatNullable(trainingJob.best_reward)} />
                <Metric label="Latest reward" value={formatNullable(trainingJob.latest_reward)} />
                <Metric label="Models" value={trainingJob.saved_model_count.toString()} />
              </div>
            </div>
          )}

          <h3>Most congested roads</h3>
          <div className="list">
            {topRoads?.map((road) => (
              <div className="list-item" key={road.road_id}>
                <span>{road.road_id}</span>
                <strong>{Math.round(road.congestion_score * 100)}%</strong>
              </div>
            ))}
          </div>

          <h3>Problem intersections</h3>
          <div className="list">
            {topIntersections?.map((item) => (
              <div className="list-item" key={item.intersection_id}>
                <span>{item.intersection_id}</span>
                <strong>{Math.round(item.congestion_score * 100)}%</strong>
              </div>
            ))}
          </div>
        </>
      )}

      {cityMap && (
        <div className="city-summary">
          <p>Roads: {cityMap.roads.length}</p>
          <p>Buildings: {cityMap.buildings.length}</p>
          <p>Surfaces: {(cityMap.surfaces ?? []).length}</p>
          <p>Intersections: {cityMap.intersections.length}</p>
          <p>OSM Signals: {cityMap.traffic_signals.length}</p>
          <p>Crossings: {cityMap.crossings.length}</p>
          <p>Infra: {cityMap.infrastructure.length}</p>
        </div>
      )}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function ComparisonItem({ label, active }: { label: string; active: boolean }) {
  return (
    <div className={["comparison-item", active ? "comparison-item-active" : ""].join(" ")}>
      <span>{label}</span>
      <strong>{active ? "Live" : "Ready"}</strong>
    </div>
  );
}

function formatNullable(value: number | null | undefined) {
  if (value === null || value === undefined) return "—";
  return Number(value).toFixed(2);
}