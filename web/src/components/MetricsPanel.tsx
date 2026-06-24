import type { CityMap, SimulationState } from "../types/domain";
import { formatNumber, formatSpeed } from "../utils/format";

type Props = {
  state: SimulationState | null;
  cityMap: CityMap | null;
};

export function MetricsPanel({ state, cityMap }: Props) {
  return (
    <section className="panel-block">
      <h2>Metrics</h2>

      {!state ? (
        <p className="muted">No simulation running.</p>
      ) : (
        <div className="metrics-grid">
          <Metric label="Tick" value={state.tick.toString()} />
          <Metric label="Vehicles" value={state.metrics.active_vehicles.toString()} />
          <Metric label="Pedestrians" value={state.metrics.active_pedestrians.toString()} />
          <Metric label="Avg speed" value={formatSpeed(state.metrics.average_speed_mps)} />
          <Metric label="Vehicle wait" value={`${formatNumber(state.metrics.average_vehicle_wait_time)}s`} />
          <Metric label="Congestion" value={`${formatNumber(state.metrics.congestion_score * 100)}%`} />
          <Metric label="Events" value={state.metrics.active_events.toString()} />
          <Metric label="Throughput" value={state.metrics.throughput.toString()} />
        </div>
      )}

      {cityMap && (
        <div className="city-summary">
          <p>Roads: {cityMap.roads.length}</p>
          <p>Buildings: {cityMap.buildings.length}</p>
          <p>Intersections: {cityMap.intersections.length}</p>
          <p>Signals: {cityMap.traffic_signals.length}</p>
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