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
  center: [number, number];
  selectedCenter: [number, number];
  zoom: number;
  query: string;
  areaSizeText: string;
  isImporting: boolean;
  error: string | null;
  onBboxChange: (bbox: BoundingBox) => void;
  onCenterChange: (center: [number, number]) => void;
  onSelectedCenterChange: (center: [number, number]) => void;
  onZoomChange: (zoom: number) => void;
  onQueryChange: (query: string) => void;
  onAreaSizeTextChange: (value: string) => void;
  onImportOsm: (bbox: BoundingBox) => void;
  onClose: () => void;
};

function MapFocus({ target }: { target: { center: [number, number]; zoom: number; key: number } }) {
  const map = useMap();

  useEffect(() => {
    map.setView(target.center, target.zoom, { animate: true });
    setTimeout(() => map.invalidateSize(), 50);
  }, [target.key, map]);

  return null;
}

function CenterAreaBinder({
  sizeMeters,
  onMapMove
}: {
  sizeMeters: number;
  onMapMove: (lat: number, lon: number, zoom: number) => void;
}) {
  const map = useMap();

  useEffect(() => {
    const center = map.getCenter();
    onMapMove(center.lat, center.lng, map.getZoom());
  }, [map, onMapMove, sizeMeters]);

  useMapEvents({
    move() {
      const center = map.getCenter();
      onMapMove(center.lat, center.lng, map.getZoom());
    },
    zoomend() {
      const center = map.getCenter();
      onMapMove(center.lat, center.lng, map.getZoom());
    }
  });

  return null;
}

export function MapSelector({
  bbox,
  center,
  selectedCenter,
  zoom,
  query,
  areaSizeText,
  isImporting,
  error,
  onBboxChange,
  onCenterChange,
  onSelectedCenterChange,
  onZoomChange,
  onQueryChange,
  onAreaSizeTextChange,
  onImportOsm,
  onClose
}: Props) {
  const [focusTarget, setFocusTarget] = useState({
    center,
    zoom,
    key: 0
  });
  const [visualAreaSize, setVisualAreaSize] = useState(clampAreaSize(Number(areaSizeText) || 1000));
  const animationRef = useRef<number | null>(null);

  const targetAreaSize = clampAreaSize(Number(areaSizeText) || 1000);

  const rectangleBounds: LatLngBoundsExpression | null = bbox
    ? [
        [bbox.south, bbox.west],
        [bbox.north, bbox.east]
      ]
    : null;

  const updateSelectionFromCenter = useCallback(
    (lat: number, lon: number, nextZoom: number) => {
      const nextCenter: [number, number] = [lat, lon];

      onCenterChange(nextCenter);
      onSelectedCenterChange(nextCenter);
      onZoomChange(nextZoom);
      onBboxChange(buildSquareBbox(lat, lon, visualAreaSize));
    },
    [onBboxChange, onCenterChange, onSelectedCenterChange, onZoomChange, visualAreaSize]
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
    if (!trimmed || isImporting) return;

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
    const nextCenter: [number, number] = [lat, lon];
    const nextZoom = 15;

    setFocusTarget((current) => ({
      center: nextCenter,
      zoom: nextZoom,
      key: current.key + 1
    }));
    onCenterChange(nextCenter);
    onSelectedCenterChange(nextCenter);
    onZoomChange(nextZoom);
    onBboxChange(buildSquareBbox(lat, lon, targetAreaSize));
  }

  function changeAreaSize(delta: number) {
    if (isImporting) return;

    const nextSize = clampAreaSize(targetAreaSize + delta);
    onAreaSizeTextChange(String(nextSize));
  }

  function confirmSelection() {
    if (isImporting) return;

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
        disabled={isImporting}
        aria-label="Close map"
      >
        ‹
      </button>

      <div className="fullscreen-map">
        <MapContainer
          center={center}
          zoom={zoom}
          scrollWheelZoom
          zoomControl={false}
          attributionControl={false}
          style={{ height: "100%", width: "100%" }}
        >
          <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />

          <MapFocus target={focusTarget} />
          <CenterAreaBinder sizeMeters={visualAreaSize} onMapMove={updateSelectionFromCenter} />

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
            disabled={isImporting}
            placeholder="Search city, street, district..."
            onChange={(event) => onQueryChange(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") void searchPlace();
            }}
          />

          <div className="area-size-control">
            <input
              className="area-size-input"
              value={areaSizeText}
              disabled={isImporting}
              inputMode="numeric"
              aria-label="Area size in meters"
              placeholder="Area size, m"
              onChange={(event) => onAreaSizeTextChange(event.target.value.replace(/[^\d]/g, ""))}
              onBlur={() => onAreaSizeTextChange(String(targetAreaSize))}
            />

            <div className="area-size-stepper">
              <button type="button" disabled={isImporting} onClick={() => changeAreaSize(100)} aria-label="Increase area size">
                +
              </button>
              <button type="button" disabled={isImporting} onClick={() => changeAreaSize(-100)} aria-label="Decrease area size">
                -
              </button>
            </div>
          </div>

          <button type="button" disabled={isImporting} onClick={() => void searchPlace()}>
            Find
          </button>

          <button type="button" disabled={isImporting} onClick={confirmSelection}>
            {isImporting ? "Loading..." : "Confirm area"}
          </button>
        </div>

        {error && <p className="map-error">{error}</p>}
      </footer>

      {isImporting && (
        <div className="map-loading-overlay">
          <div className="map-loading-card">
            <div className="map-loading-spinner" />
            <strong>Generating selected OSM area</strong>
            <span>Loading roads, buildings, parks, water, infrastructure and creating traffic simulation...</span>
          </div>
        </div>
      )}
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