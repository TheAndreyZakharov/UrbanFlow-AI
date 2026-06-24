import type {
  BoundingBox,
  CityMap,
  EditorPatch,
  SimulationMode,
  SimulationSession,
  SimulationState
} from "../types/domain";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers ?? {})
    },
    ...options
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`API ${response.status}: ${text}`);
  }

  return response.json() as Promise<T>;
}

export async function importOsmArea(bbox: BoundingBox): Promise<CityMap> {
  return request<CityMap>("/osm/import", {
    method: "POST",
    body: JSON.stringify({ bbox })
  });
}

export async function createSimulation(params: {
  cityMap: CityMap;
  mode: SimulationMode;
  vehiclesCount: number;
  pedestriansCount: number;
  randomEventsEnabled: boolean;
  seed: number;
}): Promise<SimulationSession> {
  return request<SimulationSession>("/simulation/create", {
    method: "POST",
    body: JSON.stringify({
      city_map: params.cityMap,
      mode: params.mode,
      vehicles_count: params.vehiclesCount,
      pedestrians_count: params.pedestriansCount,
      random_events_enabled: params.randomEventsEnabled,
      seed: params.seed
    })
  });
}

export async function stepSimulation(sessionId: string, steps: number): Promise<SimulationState> {
  return request<SimulationState>(`/simulation/${sessionId}/step`, {
    method: "POST",
    body: JSON.stringify({ steps })
  });
}

export async function resetSimulation(sessionId: string): Promise<SimulationState> {
  return request<SimulationState>(`/simulation/${sessionId}/reset`, {
    method: "POST"
  });
}

export async function setSimulationMode(
  sessionId: string,
  mode: SimulationMode
): Promise<SimulationState> {
  return request<SimulationState>(`/simulation/${sessionId}/mode/${mode}`, {
    method: "POST"
  });
}

export async function applyEditorPatch(
  sessionId: string,
  patch: EditorPatch
): Promise<{ session_id: string; total_patches: number }> {
  return request<{ session_id: string; total_patches: number }>("/editor/apply", {
    method: "POST",
    body: JSON.stringify({
      session_id: sessionId,
      patch
    })
  });
}