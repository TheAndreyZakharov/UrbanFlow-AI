import type { SimulationState } from "../types/domain";

type Props = {
  state: SimulationState | null;
};

export function AIPanel({ state }: Props) {
  const problematic = state?.intersection_load
    .slice()
    .sort((a, b) => b.congestion_score - a.congestion_score)
    .slice(0, 5);

  return (
    <section className="panel-block">
      <h2>AI Panel</h2>

      {!state ? (
        <p className="muted">AI controller is waiting for simulation.</p>
      ) : (
        <>
          <p>
            Mode: <strong>{state.mode}</strong>
          </p>

          <p className="muted">
            The AI mode is reserved for the future trained multi-agent RL controller. Current backend keeps the same API contract.
          </p>

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