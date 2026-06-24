import { useCallback, useEffect, useRef, useState } from "react";
import { MapContainer, Rectangle, TileLayer, useMap, useMapEvents } from "react-leaflet";
import type { LatLngBoundsExpression } from "leaflet";
import type { BoundingBox } from "../types/domain";

type SearchResult = {
  place_id: number;
  display_name: string;
  lat: string;
  lon: string;
};

type Props = {
  bbox: BoundingBox | null;
  onBboxChange: (bbox: BoundingBox) => void;
  onImportOsm: (bbox: BoundingBox) => void;
  onClose: () => void;
};

function MapFocus({ center }: { center: [number, number] }) {
  const map = useMap();

  useEffect(() => {
    map.setView(center, 15, { animate: true });
    setTimeout(() => map.invalidateSize(), 50);
  }, [center, map]);

  return null;
}

function CenterAreaBinder({
  sizeMeters,
  onCenterChange
}: {
  sizeMeters: number;
  onCenterChange: (lat: number, lon: number) => void;
}) {
  const map = useMap();

  useEffect(() => {
    const center = map.getCenter();
    onCenterChange(center.lat, center.lng);
  }, [map, onCenterChange, sizeMeters]);

  useMapEvents({
    move() {
      const center = map.getCenter();
      onCenterChange(center.lat, center.lng);
    },
    zoomend() {
      const center = map.getCenter();
      onCenterChange(center.lat, center.lng);
    }
  });

  return null;
}

export function MapSelector({ bbox, onBboxChange, onImportOsm, onClose }: Props) {
  const [query, setQuery] = useState("");
  const [center, setCenter] = useState<[number, number]>([55.751244, 37.618423]);
  const [selectedCenter, setSelectedCenter] = useState<[number, number]>([55.751244, 37.618423]);
  const [areaSizeText, setAreaSizeText] = useState("1000");
  const [visualAreaSize, setVisualAreaSize] = useState(1000);
  const animationRef = useRef<number | null>(null);

  const targetAreaSize = clampAreaSize(Number(areaSizeText) || 1000);

  const rectangleBounds: LatLngBoundsExpression | null = bbox
    ? [
        [bbox.south, bbox.west],
        [bbox.north, bbox.east]
      ]
    : null;

  const updateSelectionFromCenter = useCallback(
    (lat: number, lon: number) => {
      setSelectedCenter([lat, lon]);
      onBboxChange(buildSquareBbox(lat, lon, visualAreaSize));
    },
    [onBboxChange, visualAreaSize]
  );

  useEffect(() => {
    if (animationRef.current) {
      window.cancelAnimationFrame(animationRef.current);
    }

    const startSize = visualAreaSize;
    const endSize = targetAreaSize;
    const startedAt = performance.now();
    const duration = 180;

    function animate(now: number) {
      const progress = Math.min(1, (now - startedAt) / duration);
      const eased = 1 - Math.pow(1 - progress, 3);
      const nextSize = startSize + (endSize - startSize) * eased;

      setVisualAreaSize(nextSize);

      const [lat, lon] = selectedCenter;
      onBboxChange(buildSquareBbox(lat, lon, nextSize));

      if (progress < 1) {
        animationRef.current = window.requestAnimationFrame(animate);
      }
    }

    animationRef.current = window.requestAnimationFrame(animate);

    return () => {
      if (animationRef.current) {
        window.cancelAnimationFrame(animationRef.current);
      }
    };
  }, [targetAreaSize]);

  async function searchPlace() {
    const trimmed = query.trim();
    if (!trimmed) return;

    const url = new URL("https://nominatim.openstreetmap.org/search");
    url.searchParams.set("format", "json");
    url.searchParams.set("q", trimmed);
    url.searchParams.set("limit", "1");
    url.searchParams.set("accept-language", "ru,en");

    const response = await fetch(url.toString(), {
      headers: {
        Accept: "application/json"
      }
    });

    if (!response.ok) return;

    const payload = (await response.json()) as SearchResult[];
    const firstResult = payload[0];

    if (!firstResult) return;

    const lat = Number(firstResult.lat);
    const lon = Number(firstResult.lon);

    setCenter([lat, lon]);
    setSelectedCenter([lat, lon]);
    onBboxChange(buildSquareBbox(lat, lon, targetAreaSize));
  }

  function changeAreaSize(delta: number) {
    const nextSize = clampAreaSize(targetAreaSize + delta);
    setAreaSizeText(String(nextSize));
  }

  function confirmSelection() {
    const [lat, lon] = selectedCenter;
    const finalBbox = buildSquareBbox(lat, lon, targetAreaSize);

    onBboxChange(finalBbox);
    onImportOsm(finalBbox);
  }

  return (
    <section className="map-selector-full">
      <button
        className="round-close map-round-close"
        type="button"
        onClick={onClose}
        aria-label="Close map"
      >
        ‹
      </button>

      <div className="fullscreen-map">
        <MapContainer
          center={center}
          zoom={15}
          scrollWheelZoom
          zoomControl={false}
          attributionControl={false}
          style={{ height: "100%", width: "100%" }}
        >
          <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />

          <MapFocus center={center} />
          <CenterAreaBinder sizeMeters={visualAreaSize} onCenterChange={updateSelectionFromCenter} />

          {rectangleBounds && (
            <Rectangle
              bounds={rectangleBounds}
              pathOptions={{
                color: "#22c55e",
                weight: 3,
                fillOpacity: 0.08,
                opacity: 0.95,
                className: "map-selection-rectangle"
              }}
            />
          )}
        </MapContainer>

        <div className="map-center-dot" aria-hidden="true" />
      </div>

      <footer className="map-footer map-footer-compact">
        <div className="map-footer-grid map-footer-grid-compact">
          <input
            value={query}
            placeholder="Search city, street, district..."
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") void searchPlace();
            }}
          />

          <div className="area-size-control">
            <input
              className="area-size-input"
              value={areaSizeText}
              inputMode="numeric"
              aria-label="Area size in meters"
              placeholder="Area size, m"
              onChange={(event) => setAreaSizeText(event.target.value.replace(/[^\d]/g, ""))}
              onBlur={() => setAreaSizeText(String(targetAreaSize))}
            />

            <div className="area-size-stepper">
              <button type="button" onClick={() => changeAreaSize(100)} aria-label="Increase area size">
                +
              </button>
              <button type="button" onClick={() => changeAreaSize(-100)} aria-label="Decrease area size">
                -
              </button>
            </div>
          </div>

          <button type="button" onClick={() => void searchPlace()}>
            Find
          </button>

          <button type="button" onClick={confirmSelection}>
            Confirm area
          </button>
        </div>
      </footer>
    </section>
  );
}

function buildSquareBbox(lat: number, lon: number, sizeMeters: number): BoundingBox {
  const safeSize = clampAreaSize(sizeMeters);
  const halfLat = safeSize / 2 / 111_320;
  const halfLon = safeSize / 2 / (111_320 * Math.cos((lat * Math.PI) / 180));

  return {
    south: lat - halfLat,
    west: lon - halfLon,
    north: lat + halfLat,
    east: lon + halfLon
  };
}

function clampAreaSize(value: number): number {
  return Math.max(200, Math.min(5000, Math.round(value)));
}