import type { SceneSettings } from "../types/scene";

type Props = {
  settings: SceneSettings;
  onChange: (settings: SceneSettings) => void;
};

export function SceneSettingsPanel({ settings, onChange }: Props) {
  function updateSetting<Key extends keyof SceneSettings>(key: Key, value: SceneSettings[Key]) {
    onChange({
      ...settings,
      [key]: value
    });
  }

  return (
    <section className="panel-block">
      <h2>View Settings</h2>
      <p className="muted">Control what is visible in the generated city scene.</p>

      <ToggleRow
        title="Scene shadows"
        description="Render dynamic shadows. Looks nicer, but costs a lot on large maps."
        checked={settings.enableShadows}
        onChange={(checked) => updateSetting("enableShadows", checked)}
      />

      <ToggleRow
        title="High resolution rendering"
        description="Use Retina-quality rendering. Sharper image, heavier GPU load."
        checked={settings.highDpr}
        onChange={(checked) => updateSetting("highDpr", checked)}
      />

      <ToggleRow
        title="Depth precision mode"
        description="Improves huge-scene depth precision, but may reduce performance. Scene will rebuild when toggled."
        checked={settings.logarithmicDepthBuffer}
        onChange={(checked) => updateSetting("logarithmicDepthBuffer", checked)}
      />

      <ToggleRow
        title="Fine geometry details"
        description="Road joints, rail joints, sleepers, lane markings and dense crossings. Best visuals, more draw calls."
        checked={settings.fineGeometryDetails}
        onChange={(checked) => updateSetting("fineGeometryDetails", checked)}
      />

      <ToggleRow
        title="Show buildings"
        description="Show or hide all 3D buildings."
        checked={settings.showBuildings}
        onChange={(checked) => updateSetting("showBuildings", checked)}
      />

      <ToggleRow
        title="Ground zone colors"
        description="Show colored land zones. Water is always visible."
        checked={settings.showGroundZones}
        onChange={(checked) => updateSetting("showGroundZones", checked)}
      />

      <ToggleRow
        title="Show special zones"
        description="Hospitals, schools, parking and other special zones get their own colors."
        checked={settings.showSpecialZones}
        onChange={(checked) => updateSetting("showSpecialZones", checked)}
      />

      <ToggleRow
        title="Highlight road access"
        description="Shows only road availability: blocked roads, opened roads, roadworks and roads unavailable for cars."
        checked={settings.highlightRoadAccess}
        onChange={(checked) => updateSetting("highlightRoadAccess", checked)}
      />

      <ToggleRow
        title="Highlight congestion"
        description="Shows only traffic load: yellow, orange and red roads by congestion level."
        checked={settings.highlightRoadCongestion}
        onChange={(checked) => updateSetting("highlightRoadCongestion", checked)}
      />
    </section>
  );
}

function ToggleRow({
  title,
  description,
  checked,
  onChange
}: {
  title: string;
  description: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label className="settings-toggle-row">
      <span className="settings-toggle-copy">
        <strong>{title}</strong>
        <small>{description}</small>
      </span>

      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
      />

      <span className="settings-toggle-switch" aria-hidden="true" />
    </label>
  );
}