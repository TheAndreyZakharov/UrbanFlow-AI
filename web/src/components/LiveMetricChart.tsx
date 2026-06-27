type ChartPoint = {
  tick: number;
  value: number;
};

type Props = {
  title: string;
  points: ChartPoint[];
  suffix?: string;
  maxPoints?: number;
};

export function LiveMetricChart({ title, points, suffix = "", maxPoints = 80 }: Props) {
  const visiblePoints = points.slice(-maxPoints);
  const width = 320;
  const height = 110;
  const paddingX = 10;
  const paddingY = 12;

  const values = visiblePoints.map((point) => point.value);
  const minValue = Math.min(...values, 0);
  const maxValue = Math.max(...values, 1);
  const latest = visiblePoints.at(-1)?.value ?? 0;

  const path = visiblePoints
    .map((point, index) => {
      const x =
        paddingX +
        (index / Math.max(1, visiblePoints.length - 1)) *
          (width - paddingX * 2);

      const normalized =
        maxValue === minValue
          ? 0
          : (point.value - minValue) / Math.max(0.000001, maxValue - minValue);

      const y = height - paddingY - normalized * (height - paddingY * 2);

      return `${index === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(" ");

  return (
    <div className="live-chart-card">
      <div className="live-chart-header">
        <span>{title}</span>
        <strong>
          {formatChartValue(latest)}
          {suffix}
        </strong>
      </div>

      <svg className="live-chart-svg" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={title}>
        <path className="live-chart-grid" d={`M 0 ${height - paddingY} L ${width} ${height - paddingY}`} />
        <path className="live-chart-line" d={path} />
      </svg>
    </div>
  );
}

function formatChartValue(value: number) {
  if (!Number.isFinite(value)) return "0";
  if (Math.abs(value) >= 100) return Math.round(value).toString();
  if (Math.abs(value) >= 10) return value.toFixed(1);
  return value.toFixed(2);
}