import type {
  TrainingCurriculum,
  TrainingJob,
  TrainingModelFormat,
  TrainingSignalScope
} from "../types/domain";

type Props = {
  hasSession: boolean;
  signalScope: TrainingSignalScope;
  curriculum: TrainingCurriculum;
  job: TrainingJob | null;
  isBusy: boolean;
  onSignalScopeChange: (scope: TrainingSignalScope) => void;
  onCurriculumChange: (curriculum: TrainingCurriculum) => void;
  onStartTraining: () => void;
  onStopTraining: () => void;
  onSaveModel: () => void;
  onExportModel: (format: TrainingModelFormat) => void;
};

export function TrainingPanel({
  hasSession,
  signalScope,
  curriculum,
  job,
  isBusy,
  onSignalScopeChange,
  onCurriculumChange,
  onStartTraining,
  onStopTraining,
  onSaveModel,
  onExportModel
}: Props) {
  const isRunning = job?.status === "running";
  const canSaveModel = Boolean(job?.can_save_model);

  return (
    <section className="panel-block">
      <h2>AI training</h2>
      <p className="muted">
        Train UrbanFlow AI on the current generated SUMO zone. SUMO moves vehicles, UrbanFlow AI controls real SUMO
        traffic lights. Curriculum increases traffic difficulty from low load to high load.
      </p>

      <label>
        Signal scope
        <select
          value={signalScope}
          disabled={!hasSession || isRunning || isBusy}
          onChange={(event) => onSignalScopeChange(event.target.value as TrainingSignalScope)}
        >
          <option value="osm_only">OSM traffic lights only</option>
          <option value="all_intersections">All possible intersections</option>
        </select>
      </label>

      <div className="simulation-count-grid">
        <label>
          Start vehicles
          <input
            type="number"
            min={0}
            max={5000}
            value={curriculum.start_vehicles}
            disabled={isRunning || isBusy}
            onChange={(event) =>
              onCurriculumChange({
                ...curriculum,
                start_vehicles: clampInt(Number(event.target.value), 0, 5000)
              })
            }
          />
        </label>

        <label>
          Max vehicles
          <input
            type="number"
            min={1}
            max={5000}
            value={curriculum.max_vehicles}
            disabled={isRunning || isBusy}
            onChange={(event) =>
              onCurriculumChange({
                ...curriculum,
                max_vehicles: clampInt(Number(event.target.value), 1, 5000)
              })
            }
          />
        </label>
      </div>

      <div className="simulation-count-grid">
        <label>
          Vehicle step
          <input
            type="number"
            min={1}
            max={1000}
            value={curriculum.vehicle_step}
            disabled={isRunning || isBusy}
            onChange={(event) =>
              onCurriculumChange({
                ...curriculum,
                vehicle_step: clampInt(Number(event.target.value), 1, 1000)
              })
            }
          />
        </label>

        <label>
          Steps per level
          <input
            type="number"
            min={60}
            max={100000}
            value={curriculum.steps_per_level}
            disabled={isRunning || isBusy}
            onChange={(event) =>
              onCurriculumChange({
                ...curriculum,
                steps_per_level: clampInt(Number(event.target.value), 60, 100000)
              })
            }
          />
        </label>
      </div>

      <label>
        Pedestrians
        <input
          type="number"
          min={0}
          max={10000}
          value={curriculum.pedestrians_count}
          disabled={isRunning || isBusy}
          onChange={(event) =>
            onCurriculumChange({
              ...curriculum,
              pedestrians_count: clampInt(Number(event.target.value), 0, 10000)
            })
          }
        />
      </label>

      <label className="settings-toggle-row">
        <span className="settings-toggle-copy">
          <strong>Random road events during training</strong>
          <small>Accidents and roadworks make the controller more robust after the real trainer is connected.</small>
        </span>

        <input
          type="checkbox"
          checked={curriculum.random_events_enabled}
          disabled={isRunning || isBusy}
          onChange={(event) =>
            onCurriculumChange({
              ...curriculum,
              random_events_enabled: event.target.checked
            })
          }
        />

        <span className="settings-toggle-switch" aria-hidden="true" />
      </label>

      <div className="button-row button-row-two">
        <button disabled={!hasSession || isRunning || isBusy} onClick={onStartTraining}>
          Start visual training
        </button>

        <button disabled={!job || !isRunning || isBusy} className="danger-button" onClick={onStopTraining}>
          Stop training
        </button>
      </div>

      <h3>Model actions</h3>

      <div className="button-row button-row-two">
        <button disabled={!job || !canSaveModel || isBusy} onClick={onSaveModel}>
          Save trained model
        </button>

        <button disabled={!job || !canSaveModel || isBusy} onClick={() => onExportModel("checkpoint")}>
          Export checkpoint
        </button>
      </div>

      <div className="button-row button-row-two">
        <button disabled={!job || !canSaveModel || isBusy} onClick={() => onExportModel("onnx")}>
          Export ONNX
        </button>

        <button disabled={!job || !canSaveModel || isBusy} onClick={() => onExportModel("torchscript")}>
          Export TorchScript
        </button>
      </div>

      {!canSaveModel && (
        <p className="muted">
          Model saving unlocks after the real RL trainer writes checkpoint_path. The UI is ready; the trainer will fill it.
        </p>
      )}

      <div className="metrics-grid">
        <Metric label="Status" value={job?.status ?? "idle"} />
        <Metric label="Scope" value={job?.signal_scope ?? signalScope} />
        <Metric label="Episode" value={job?.current_episode ?? 0} />
        <Metric label="Step" value={job?.current_step ?? 0} />
        <Metric label="Vehicles" value={job?.current_vehicles ?? curriculum.start_vehicles} />
        <Metric label="Best reward" value={formatNullable(job?.best_reward)} />
        <Metric label="Latest reward" value={formatNullable(job?.latest_reward)} />
        <Metric label="Saved models" value={job?.saved_model_count ?? 0} />
      </div>

      {job && (
        <div className="list">
          <div className="list-item">
            <span>Model dir</span>
            <strong>{job.model_output_dir}</strong>
          </div>

          <div className="list-item">
            <span>Checkpoint</span>
            <strong>{job.checkpoint_path ?? "not created yet"}</strong>
          </div>

          <div className="list-item">
            <span>Message</span>
            <strong>{job.message}</strong>
          </div>
        </div>
      )}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function clampInt(value: number, min: number, max: number) {
  if (!Number.isFinite(value)) return min;
  return Math.max(min, Math.min(max, Math.round(value)));
}

function formatNullable(value: number | null | undefined) {
  if (value === null || value === undefined) return "—";
  return Number(value).toFixed(2);
}