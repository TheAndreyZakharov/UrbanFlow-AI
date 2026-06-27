type TabIcon = "map" | "simulation" | "editor" | "settings" | "metrics" | "training";

type Props = {
  label: string;
  icon: TabIcon;
  side?: "left" | "right";
  active?: boolean;
  expanded?: boolean;
  onClick: () => void;
};

export function SideTab({
  label,
  icon,
  side = "left",
  active = false,
  expanded = false,
  onClick
}: Props) {
  return (
    <button
      className={[
        "dock-tab",
        side === "right" ? "dock-tab-right" : "dock-tab-left",
        active ? "dock-tab-active" : "",
        expanded ? "dock-tab-expanded" : ""
      ].join(" ")}
      type="button"
      onClick={onClick}
      title={label}
    >
      <span className="dock-tab-icon">
        <Icon type={icon} />
      </span>
      <span className="dock-tab-label">{label}</span>
    </button>
  );
}

function Icon({ type }: { type: TabIcon }) {
  if (type === "map") {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M9 18l-6 3V6l6-3 6 3 6-3v15l-6 3-6-3z" />
        <path d="M9 3v15" />
        <path d="M15 6v15" />
      </svg>
    );
  }

  if (type === "simulation") {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M4 17h4l3-10 4 10h5" />
        <path d="M5 21h14" />
        <path d="M7 13h10" />
      </svg>
    );
  }

  if (type === "editor") {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M4 20h4l11-11-4-4L4 16v4z" />
        <path d="M13 7l4 4" />
        <path d="M12 20h8" />
      </svg>
    );
  }

  if (type === "training") {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M4 18c4-8 8-8 16-12" />
        <path d="M5 6h5v5H5z" />
        <path d="M14 13h5v5h-5z" />
        <path d="M10 8h4" />
        <path d="M16 10v3" />
      </svg>
    );
  }
  
  if (type === "settings") {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M4 7h10" />
        <path d="M18 7h2" />
        <path d="M16 5v4" />
        <path d="M4 12h3" />
        <path d="M11 12h9" />
        <path d="M9 10v4" />
        <path d="M4 17h12" />
        <path d="M20 17h0" />
        <path d="M18 15v4" />
      </svg>
    );
  }

  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 19V5" />
      <path d="M4 19h16" />
      <path d="M8 16v-5" />
      <path d="M12 16V8" />
      <path d="M16 16v-9" />
    </svg>
  );
}