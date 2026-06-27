export type SimulationMode = "fixed" | "rule_based" | "ai";

export type BoundingBox = {
  south: number;
  west: number;
  north: number;
  east: number;
};

export type Coordinate = {
  lat: number;
  lon: number;
  x: number;
  z: number;
};

export type Road = {
  id: string;
  osm_id: string;
  name: string | null;
  kind: string;
  lanes: number;
  lanes_forward: number | null;
  lanes_backward: number | null;
  turn_lanes: string | null;
  turn_lanes_forward: string | null;
  turn_lanes_backward: string | null;
  route_refs: string[];
  route_types: string[];
  one_way: boolean;
  max_speed_kph: number;
  surface: string | null;
  access: string | null;
  bridge: string | null;
  tunnel: string | null;
  layer: number | null;
  is_driveable: boolean;
  is_walkable: boolean;
  coordinates: Coordinate[];
  tags: Record<string, string>;
};

export type Building = {
  id: string;
  osm_id: string;
  height: number;
  levels: number | null;
  kind: string | null;
  coordinates: Coordinate[];
  holes: Coordinate[][];
  tags: Record<string, string>;
};

export type Surface = {
  id: string;
  osm_id: string;
  kind: string;
  name: string | null;
  coordinates: Coordinate[];
  tags: Record<string, string>;
};

export type RailLine = {
  id: string;
  osm_id: string;
  kind: string;
  name: string | null;
  is_tram: boolean;
  is_service: boolean;
  route_refs: string[];
  route_types: string[];
  bridge: string | null;
  tunnel: string | null;
  layer: number | null;
  coordinates: Coordinate[];
  tags: Record<string, string>;
};

export type TransitStop = {
  id: string;
  osm_id: string;
  kind: string;
  name: string | null;
  route_refs: string[];
  lat: number;
  lon: number;
  x: number;
  z: number;
  tags: Record<string, string>;
};

export type Intersection = {
  id: string;
  lat: number;
  lon: number;
  x: number;
  z: number;
  connected_road_ids: string[];
  has_signal: boolean;
};

export type TrafficSignal = {
  id: string;
  osm_id: string;
  lat: number;
  lon: number;
  x: number;
  z: number;
  signal_type: string | null;
  direction: string | null;
  tags: Record<string, string>;
};

export type Crossing = {
  id: string;
  osm_id: string;
  lat: number;
  lon: number;
  x: number;
  z: number;
  tags: Record<string, string>;
};

export type Infrastructure = {
  id: string;
  osm_id: string;
  kind: string;
  name: string | null;
  lat: number;
  lon: number;
  x: number;
  z: number;
  tags: Record<string, string>;
};

export type CityMap = {
  bbox: BoundingBox;
  origin_lat: number;
  origin_lon: number;
  roads: Road[];
  buildings: Building[];
  surfaces: Surface[];
  rail_lines: RailLine[];
  transit_stops: TransitStop[];
  intersections: Intersection[];
  traffic_signals: TrafficSignal[];
  crossings: Crossing[];
  infrastructure: Infrastructure[];
};

export type VehicleState = {
  id: string;
  kind: string;
  color: string;
  lat: number;
  lon: number;
  x: number;
  z: number;
  elevation_m: number;
  speed_mps: number;
  wait_time: number;
  road_id: string;
  route_edge_ids: string[];
  current_edge_id: string | null;
  heading_rad: number;
  lane_offset_m: number;
  length_m: number;
  width_m: number;
};

export type PedestrianState = {
  id: string;
  color: string;
  lat: number;
  lon: number;
  x: number;
  z: number;
  speed_mps: number;
  wait_time: number;
  heading_rad: number;
};

export type SignalState = {
  id: string;
  intersection_id: string;
  phase: string;
  time_left: number;
  controlled_road_ids: string[];
};

export type TrafficEvent = {
  id: string;
  kind: string;
  target_id: string | null;
  started_at_tick: number;
  duration_ticks: number;
  payload: Record<string, unknown>;
};

export type RoadLoad = {
  road_id: string;
  vehicle_count: number;
  average_speed_mps: number;
  congestion_score: number;
};

export type IntersectionLoad = {
  intersection_id: string;
  waiting_vehicles: number;
  waiting_pedestrians: number;
  congestion_score: number;
};

export type EditorPatch = {
  id: string;
  kind:
    | "close_road"
    | "open_road"
    | "remove_road"
    | "add_road"
    | "add_crossing"
    | "remove_crossing"
    | "add_signal"
    | "remove_signal"
    | "accident"
    | "roadwork"
    | "traffic_boost"
    | "attraction_point"
    | "clear_event";
  target_id: string | null;
  payload: Record<string, unknown>;
};

export type SimulationMetrics = {
  average_vehicle_wait_time: number;
  average_pedestrian_wait_time: number;
  average_speed_mps: number;
  active_vehicles: number;
  active_pedestrians: number;
  congestion_score: number;
  stopped_vehicles: number;
  active_events: number;
  throughput: number;
};

export type SimulationState = {
  session_id: string;
  tick: number;
  mode: SimulationMode;
  vehicles: VehicleState[];
  pedestrians: PedestrianState[];
  signals: SignalState[];
  events: TrafficEvent[];
  road_load: RoadLoad[];
  intersection_load: IntersectionLoad[];
  metrics: SimulationMetrics;
  editor_patches: EditorPatch[];
  closed_road_ids: string[];
  forced_open_road_ids: string[];
};

export type SimulationSession = {
  session_id: string;
  city_map: CityMap;
  state: SimulationState;
};

export type TrainingSignalScope = "osm_only" | "all_intersections";

export type TrainingJobStatus = "idle" | "running" | "stopping" | "stopped" | "failed" | "completed";

export type TrainingCurriculum = {
  start_vehicles: number;
  max_vehicles: number;
  vehicle_step: number;
  steps_per_level: number;
  pedestrians_count: number;
  random_events_enabled: boolean;
};

export type TrainingJob = {
  id: string;
  session_id: string;
  status: TrainingJobStatus;
  signal_scope: TrainingSignalScope;
  current_episode: number;
  current_step: number;
  current_vehicles: number;
  best_reward: number | null;
  latest_reward: number | null;
  average_wait_time: number | null;
  congestion_score: number | null;
  stopped_vehicles: number | null;
  message: string;
  model_output_dir: string;
  checkpoint_path: string | null;
  can_save_model: boolean;
  saved_model_count: number;
  curriculum: TrainingCurriculum;
};

export type TrainingModelFormat = "checkpoint" | "onnx" | "torchscript" | "pickle";

export type SavedTrainingModel = {
  id: string;
  job_id: string;
  session_id: string;
  signal_scope: TrainingSignalScope;
  label: string;
  notes: string;
  path: string;
  format: TrainingModelFormat;
  created_at_tick: number;
  best_reward: number | null;
  average_wait_time: number | null;
  congestion_score: number | null;
  stopped_vehicles: number | null;
};

export type TrainingMetricPoint = {
  tick: number;
  speed: number;
  wait: number;
  congestion: number;
  stopped: number;
  vehicles: number;
  pedestrians: number;
  reward: number | null;
};