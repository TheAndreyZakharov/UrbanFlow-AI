import type { CityMap, EditorPatch, Road, TrafficEvent } from "../types/domain";

export type EditorTool = "close_road" | "open_road" | "roadwork" | "accident" | null;

export type EditorAutomationConfig = {
  enabled: boolean;
  durationSeconds: number;
  frequencySeconds: number;
};

export type EditorAutomationSettings = {
  closeRoads: EditorAutomationConfig;
  accidents: EditorAutomationConfig;
  roadworks: EditorAutomationConfig;
};

type Props = {
  sessionId: string | null;
  cityMap: CityMap | null;
  selectedTool: EditorTool;
  selectedRoad: Road | null;
  automation: EditorAutomationSettings;
  activeEvents: TrafficEvent[];
  onToolChange: (tool: EditorTool) => void;
  onAutomationChange: (automation: EditorAutomationSettings) => void;
  onClearEvent: (eventId: string) => void;
};

export function EditorPanel({
  sessionId,
  cityMap,
  selectedTool,
  selectedRoad,
  automation,
  activeEvents,
  onToolChange,
  onAutomationChange,
  onClearEvent
}: Props) {
  const hasRoads = Boolean(cityMap?.roads.some((road) => road.is_driveable));

  return (
    <section className="panel-block">
      <h2>Editor Mode</h2>
      <p className="muted">
        Choose an editor action, then click the target road directly in the 3D scene.
      </p>

      <div className="editor-tool-grid">
        <EditorToolButton
          label="Close road"
          tone="red"
          disabled={!sessionId || !hasRoads}
          active={selectedTool === "close_road"}
          onClick={() => onToolChange(selectedTool === "close_road" ? null : "close_road")}
        />

        <EditorToolButton
          label="Open road"
          tone="green"
          disabled={!sessionId || !hasRoads}
          active={selectedTool === "open_road"}
          onClick={() => onToolChange(selectedTool === "open_road" ? null : "open_road")}
        />

        <EditorToolButton
          label="Roadwork"
          tone="yellow"
          disabled={!sessionId || !hasRoads}
          active={selectedTool === "roadwork"}
          onClick={() => onToolChange(selectedTool === "roadwork" ? null : "roadwork")}
        />

        <EditorToolButton
          label="Accident point"
          tone="orange"
          disabled={!sessionId || !hasRoads}
          active={selectedTool === "accident"}
          onClick={() => onToolChange(selectedTool === "accident" ? null : "accident")}
        />
      </div>

      {selectedTool ? (
        <p className="status">
          Click road in scene: {toolLabel(selectedTool)}
          {selectedRoad ? ` · selected ${selectedRoad.name ?? selectedRoad.id}` : ""}
        </p>
      ) : (
        <p className="muted">All editor tools are off.</p>
      )}

      <div className="editor-automation-list">
        <AutomationRow
          title="Auto close roads"
          description="Randomly closes a road, then opens it again after duration."
          config={automation.closeRoads}
          onChange={(nextConfig) =>
            onAutomationChange({
              ...automation,
              closeRoads: nextConfig
            })
          }
        />

        <AutomationRow
          title="Auto accidents"
          description="Randomly places an accident point on part of a road."
          config={automation.accidents}
          onChange={(nextConfig) =>
            onAutomationChange({
              ...automation,
              accidents: nextConfig
            })
          }
        />

        <AutomationRow
          title="Auto roadworks"
          description="Randomly places roadworks on a road."
          config={automation.roadworks}
          onChange={(nextConfig) =>
            onAutomationChange({
              ...automation,
              roadworks: nextConfig
            })
          }
        />
      </div>

      <div className="editor-event-list">
        <h3>Active editor events</h3>

        {activeEvents.filter((event) => event.kind === "accident" || event.kind === "roadwork").length ? (
          activeEvents
            .filter((event) => event.kind === "accident" || event.kind === "roadwork")
            .map((event) => (
              <div className="editor-event-row" key={event.id}>
                <span>
                  <strong>{event.kind === "accident" ? "Accident" : "Roadwork"}</strong>
                  <small>{event.target_id ?? "no road"}</small>
                </span>

                <button
                  className="secondary editor-event-clear"
                  type="button"
                  onClick={() => onClearEvent(event.id)}
                >
                  Remove
                </button>
              </div>
            ))
        ) : (
          <p className="muted">No active accidents or roadworks.</p>
        )}
      </div>
    </section>
  );
}

function EditorToolButton({
  label,
  tone,
  active,
  disabled,
  onClick
}: {
  label: string;
  tone: "red" | "green" | "yellow" | "orange";
  active: boolean;
  disabled: boolean;
  onClick: () => void;
}) {
  return (
    <button
      className={[
        "editor-tool-button",
        `editor-tool-button-${tone}`,
        active ? "editor-tool-button-active" : ""
      ].join(" ")}
      type="button"
      disabled={disabled}
      onClick={onClick}
    >
      {label}
    </button>
  );
}

function AutomationRow({
  title,
  description,
  config,
  onChange
}: {
  title: string;
  description: string;
  config: EditorAutomationConfig;
  onChange: (config: EditorAutomationConfig) => void;
}) {
  return (
    <div className="editor-automation-row">
      <label className="settings-toggle-row editor-automation-toggle">
        <span className="settings-toggle-copy">
          <strong>{title}</strong>
          <small>{description}</small>
        </span>

        <input
          type="checkbox"
          checked={config.enabled}
          onChange={(event) =>
            onChange({
              ...config,
              enabled: event.target.checked
            })
          }
        />

        <span className="settings-toggle-switch" aria-hidden="true" />
      </label>

      <div className="editor-automation-inputs">
        <label>
          Duration, sec
          <input
            type="number"
            min={1}
            max={3600}
            value={config.durationSeconds}
            onChange={(event) =>
              onChange({
                ...config,
                durationSeconds: clampInteger(Number(event.target.value), 1, 3600)
              })
            }
          />
        </label>

        <label>
          Every, sec
          <input
            type="number"
            min={1}
            max={3600}
            value={config.frequencySeconds}
            onChange={(event) =>
              onChange({
                ...config,
                frequencySeconds: clampInteger(Number(event.target.value), 1, 3600)
              })
            }
          />
        </label>
      </div>
    </div>
  );
}

function toolLabel(tool: NonNullable<EditorTool>) {
  const labels: Record<NonNullable<EditorTool>, string> = {
    close_road: "close selected road",
    open_road: "open selected road",
    roadwork: "add roadwork to selected road",
    accident: "place accident point"
  };

  return labels[tool];
}

function clampInteger(value: number, min: number, max: number) {
  if (!Number.isFinite(value)) return min;
  return Math.max(min, Math.min(max, Math.round(value)));
}

export function buildEditorPatch(
  kind: NonNullable<EditorTool>,
  road: Road,
  durationSeconds: number,
  point?: {
    progress: number;
    x: number;
    z: number;
  }
): EditorPatch {
  const durationTicks = Math.max(1, Math.round(durationSeconds * 4));
  const manualDurationTicks = 2_147_483_647;

  if (kind === "close_road" || kind === "open_road") {
    return {
      id: `patch:${Date.now()}:${kind}:${road.id}`,
      kind,
      target_id: road.id,
      payload: {}
    };
  }

  if (kind === "roadwork") {
    return {
      id: `patch:${Date.now()}:roadwork:${road.id}`,
      kind: "roadwork",
      target_id: road.id,
      payload: {
        duration_ticks: manualDurationTicks,
        duration_seconds: null,
        manual: true,
        speed_multiplier: 0.5
      }
    };
  }

  return {
    id: `patch:${Date.now()}:accident:${road.id}`,
    kind: "accident",
    target_id: road.id,
    payload: {
      duration_ticks: manualDurationTicks,
      duration_seconds: null,
      manual: true,
      speed_multiplier: 0.28,
      progress: point?.progress ?? 0.5,
      x: point?.x,
      z: point?.z,
      radius_m: 10
    }
  };
  
}

export function buildClearEventPatch(eventId: string): EditorPatch {
  return {
    id: `patch:${Date.now()}:clear_event:${eventId}`,
    kind: "clear_event",
    target_id: eventId,
    payload: {}
  };
}