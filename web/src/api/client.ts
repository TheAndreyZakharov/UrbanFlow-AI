import type {
  BoundingBox,
  CityMap,
  EditorPatch,
  SimulationMode,
  SimulationSession,
  SimulationState,
  SavedTrainingModel,
  TrainingCurriculum,
  TrainingJob,
  TrainingModelFormat,
  TrainingSignalScope
} from "../types/domain";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

type CreateSimulationPayload = {
  cityMap: CityMap;
  mode: SimulationMode;
  vehiclesCount: number;
  pedestriansCount: number;
  randomEventsEnabled: boolean;
  seed: number;
  signalsOnAllIntersections: boolean;
};

type UpdateSimulationSettingsPayload = {
  vehiclesCount: number;
  pedestriansCount: number;
  signalsOnAllIntersections: boolean;
};

export async function importOsmArea(bbox: BoundingBox): Promise<CityMap> {
  return request<CityMap>("/osm/import", {
    method: "POST",
    body: JSON.stringify({
      bbox
    })
  });
}

export async function createSimulation(payload: CreateSimulationPayload): Promise<SimulationSession> {
  return request<SimulationSession>("/simulation/create", {
    method: "POST",
    body: JSON.stringify({
      city_map: payload.cityMap,
      mode: payload.mode,
      vehicles_count: payload.vehiclesCount,
      pedestrians_count: payload.pedestriansCount,
      random_events_enabled: payload.randomEventsEnabled,
      seed: payload.seed,
      signals_on_all_intersections: payload.signalsOnAllIntersections
    })
  });
}

export async function getSimulationState(sessionId: string): Promise<SimulationState> {
  return request<SimulationState>(`/simulation/${encodeURIComponent(sessionId)}/state`);
}

export async function updateSimulationSettings(
  sessionId: string,
  payload: UpdateSimulationSettingsPayload
): Promise<SimulationState> {
  return request<SimulationState>(`/simulation/${encodeURIComponent(sessionId)}/settings`, {
    method: "PATCH",
    body: JSON.stringify({
      vehicles_count: payload.vehiclesCount,
      pedestrians_count: payload.pedestriansCount,
      signals_on_all_intersections: payload.signalsOnAllIntersections
    })
  });
}

export async function stepSimulation(sessionId: string, steps: number): Promise<SimulationState> {
  return request<SimulationState>(`/simulation/${encodeURIComponent(sessionId)}/step`, {
    method: "POST",
    body: JSON.stringify({
      steps
    })
  });
}

export async function resetSimulation(sessionId: string): Promise<SimulationState> {
  return request<SimulationState>(`/simulation/${encodeURIComponent(sessionId)}/reset`, {
    method: "POST"
  });
}

export async function setSimulationMode(
  sessionId: string,
  mode: SimulationMode
): Promise<SimulationState> {
  return request<SimulationState>(
    `/simulation/${encodeURIComponent(sessionId)}/mode/${encodeURIComponent(mode)}`,
    {
      method: "POST"
    }
  );
}

export async function applyEditorPatch(sessionId: string, patch: EditorPatch): Promise<void> {
  await request(`/editor/apply`, {
    method: "POST",
    body: JSON.stringify({
      session_id: sessionId,
      patch
    })
  });
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init.headers ?? {})
    }
  });

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;

    try {
      const payload = (await response.json()) as { detail?: unknown };
      if (payload.detail) {
        detail = typeof payload.detail === "string" ? payload.detail : JSON.stringify(payload.detail);
      }
    } catch {
      const text = await response.text().catch(() => "");
      if (text) detail = text;
    }

    throw new Error(detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export type TrafficLightOverride = "sumo" | "red" | "yellow" | "green";

export async function setTrafficLightOverride(
  sessionId: string,
  override: TrafficLightOverride
): Promise<SimulationState> {
  return request<SimulationState>(`/simulation/${encodeURIComponent(sessionId)}/traffic-light-override/${override}`, {
    method: "POST"
  });
}

type StartTrainingPayload = {
  sessionId: string;
  signalScope: TrainingSignalScope;
  curriculum: TrainingCurriculum;
};

export async function startTraining(payload: StartTrainingPayload): Promise<TrainingJob> {
  return request<TrainingJob>("/training/start", {
    method: "POST",
    body: JSON.stringify({
      session_id: payload.sessionId,
      signal_scope: payload.signalScope,
      curriculum: payload.curriculum
    })
  });
}

export async function stopTraining(jobId: string): Promise<TrainingJob> {
  return request<TrainingJob>(`/training/${encodeURIComponent(jobId)}/stop`, {
    method: "POST"
  });
}

export async function getTrainingJob(jobId: string): Promise<TrainingJob> {
  return request<TrainingJob>(`/training/${encodeURIComponent(jobId)}`);
}

export async function getTrainingJobForSession(sessionId: string): Promise<TrainingJob | null> {
  return request<TrainingJob | null>(`/training/session/${encodeURIComponent(sessionId)}`);
}

type SaveTrainingModelPayload = {
  jobId: string;
  label: string;
  notes: string;
};

export async function saveTrainingModel(payload: SaveTrainingModelPayload): Promise<SavedTrainingModel> {
  return request<SavedTrainingModel>(`/training/${encodeURIComponent(payload.jobId)}/save-model`, {
    method: "POST",
    body: JSON.stringify({
      label: payload.label,
      notes: payload.notes
    })
  });
}

type ExportTrainingModelPayload = {
  jobId: string;
  format: TrainingModelFormat;
};

export async function exportTrainingModel(payload: ExportTrainingModelPayload): Promise<SavedTrainingModel> {
  return request<SavedTrainingModel>(`/training/${encodeURIComponent(payload.jobId)}/export-model`, {
    method: "POST",
    body: JSON.stringify({
      format: payload.format
    })
  });
}

export async function listTrainingModels(): Promise<SavedTrainingModel[]> {
  return request<SavedTrainingModel[]>("/training/models/list");
}

export async function deleteTrainingModel(modelId: string): Promise<void> {
  await request(`/training/models/${encodeURIComponent(modelId)}`, {
    method: "DELETE"
  });
}