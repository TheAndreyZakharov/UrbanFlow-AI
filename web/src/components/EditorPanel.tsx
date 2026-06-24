import { applyEditorPatch } from "../api/client";
import type { CityMap, EditorPatch } from "../types/domain";

type Props = {
  sessionId: string | null;
  cityMap: CityMap | null;
  onPatchApplied: () => void;
};

export function EditorPanel({ sessionId, cityMap, onPatchApplied }: Props) {
  const firstRoad = cityMap?.roads[0] ?? null;

  async function apply(kind: EditorPatch["kind"]) {
    if (!sessionId || !firstRoad) return;

    const patch: EditorPatch = {
      id: `patch:${Date.now()}:${kind}`,
      kind,
      target_id: firstRoad.id,
      payload:
        kind === "accident" || kind === "roadwork"
          ? { duration_ticks: 240, speed_multiplier: kind === "accident" ? 0.25 : 0.45 }
          : {}
    };

    await applyEditorPatch(sessionId, patch);
    onPatchApplied();
  }

  return (
    <section className="panel-block">
      <h2>Editor Mode</h2>
      <p className="muted">
        Road click-selection will be added next. For now the first imported OSM road is used as target.
      </p>

      <div className="button-column">
        <button disabled={!sessionId || !firstRoad} onClick={() => void apply("close_road")}>
          Close road
        </button>
        <button disabled={!sessionId || !firstRoad} onClick={() => void apply("open_road")}>
          Open road
        </button>
        <button disabled={!sessionId || !firstRoad} onClick={() => void apply("accident")}>
          Add accident
        </button>
        <button disabled={!sessionId || !firstRoad} onClick={() => void apply("roadwork")}>
          Add roadwork
        </button>
      </div>

      {firstRoad ? (
        <p className="status">Target: {firstRoad.name ?? firstRoad.id}</p>
      ) : (
        <p className="muted">Import OSM area first.</p>
      )}
    </section>
  );
}