"use client";

import { useEffect, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { geocodeBatch } from "@/lib/geocode";
import type { CollectionCenter } from "@/lib/collection-centers.api";

// Leaflet's default marker icons reference image paths that don't
// resolve correctly under most bundlers (Webpack/Turbopack). This is
// the standard workaround: point the default icon at CDN-hosted assets.
const markerIcon = L.icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

type Pin = {
  center: CollectionCenter;
  lat: number;
  lon: number;
};

// Fallback center point (roughly Caracas, Venezuela) used while no
// pins have geocoded yet, so the map doesn't render at (0, 0).
const DEFAULT_CENTER: [number, number] = [10.4806, -66.9036];
const DEFAULT_ZOOM = 6;

export function CentersMap({ centers }: { centers: CollectionCenter[] }) {
  const [pins, setPins] = useState<Pin[]>([]);
  const [status, setStatus] = useState<"loading" | "done">("loading");

  useEffect(() => {
    let cancelled = false;

    async function run() {
      setStatus("loading");
      const queries = centers.map((c) =>
        [c.address, c.city, c.state, c.country].filter(Boolean).join(", "),
      );
      const results = await geocodeBatch(queries);

      if (cancelled) return;

      const nextPins: Pin[] = [];
      results.forEach((result, i) => {
        if (result) {
          nextPins.push({ center: centers[i], lat: result.lat, lon: result.lon });
        }
      });
      setPins(nextPins);
      setStatus("done");
    }

    if (centers.length > 0) {
      run();
    } else {
      setStatus("done");
    }

    return () => {
      cancelled = true;
    };
  }, [centers]);

  return (
    <div className="mb-8">
      {status === "loading" && (
        <p className="mb-2 text-sm text-muted">
          Locating centers on the map… ({pins.length}/{centers.length})
        </p>
      )}
      <div className="h-[400px] w-full overflow-hidden rounded-lg border">
        <MapContainer
          center={DEFAULT_CENTER}
          zoom={DEFAULT_ZOOM}
          scrollWheelZoom
          style={{ height: "100%", width: "100%" }}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {pins.map((pin) => (
            <Marker
              key={pin.center.id}
              position={[pin.lat, pin.lon]}
              icon={markerIcon}
            >
              <Popup>
                <strong>{pin.center.name}</strong>
                <br />
                {pin.center.address}
                <br />
                {pin.center.city}
                {pin.center.state ? `, ${pin.center.state}` : ""}
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>
    </div>
  );
}