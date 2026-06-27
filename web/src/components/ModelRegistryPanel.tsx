import type { SavedTrainingModel, TrainingJob } from "../types/domain";

type Props = {
  job: TrainingJob | null;
  models: SavedTrainingModel[];
  isBusy: boolean;
  onRefresh: () => void;
  onDeleteModel: (modelId: string) => void;
};

export function ModelRegistryPanel({
  job,
  models,
  isBusy,
  onRefresh,
  onDeleteModel
}: Props) {
  return (
    <section className="panel-block">
      <h2>Model registry</h2>

      <p className="muted">
        Saved UrbanFlow traffic-light models for the current project. Real model files appear here after training writes checkpoints.
      </p>

      <div className="button-row button-row-two">
        <button disabled={isBusy} onClick={onRefresh}>
          Refresh models
        </button>

        <button disabled={!job} className="secondary" onClick={onRefresh}>
          Current job
        </button>
      </div>

      {job && (
        <div className="model-status-card">
          <span>Active output</span>
          <strong>{job.model_output_dir}</strong>
          <small>{job.checkpoint_path ? `Checkpoint: ${job.checkpoint_path}` : "No checkpoint from trainer yet."}</small>
        </div>
      )}

      <div className="list">
        {models.length === 0 && <p className="muted">No saved models yet.</p>}

        {models.map((model) => (
          <div className="model-row" key={model.id}>
            <div>
              <strong>{model.label}</strong>
              <span>{model.signal_scope}</span>
              <small>{model.path}</small>
            </div>

            <div className="model-row-actions">
              <span>{model.format}</span>
              <button disabled={isBusy} className="danger-button" onClick={() => onDeleteModel(model.id)}>
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}