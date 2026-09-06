import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { geoJsonToLeaflet } from '../../services/api';

// Fix for default Leaflet icon paths in Vite bundling
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

export default function MaritimeMap({
  incident,
  candidateVessels = [],
  activeLayers = {},
  currentTimeIndex = 3,
  onCursorMove,
  onSlickClick,
  onVesselClick
}) {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const layersRef = useRef({
    slickLayer: null,
    vesselTrackLayers: [],
    animatedVesselMarker: null,
    eezLayer: null,
    shippingLaneLayer: null,
    gridLayer: null
  });

  // Initialize Map Instance
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    const center = incident?.coordinates ? [incident.coordinates.lat, incident.coordinates.lng] : [14.8214, 88.2915];
    const map = L.map(mapContainerRef.current, {
      center: center,
      zoom: 8,
      zoomControl: false,
      attributionControl: false
    });

    // Dark Tactical Nautical Tile Layer (CartoDB Dark Matter)
    // CARTO now requires an API key on all tile requests (enforced 2025–2026).
    // VITE_CARTO_API_KEY is read from .env and injected by Vite at build time.
    const cartoKey = import.meta.env.VITE_CARTO_API_KEY || '';
    const tileUrl = cartoKey
      ? `https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png?key=${cartoKey}`
      : 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png';
    L.tileLayer(tileUrl, {
      maxZoom: 19,
      subdomains: 'abcd',
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, &copy; <a href="https://carto.com/attributions">CARTO</a>',
    }).addTo(map);

    // Custom Zoom Control at Bottom Right
    L.control.zoom({ position: 'bottomright' }).addTo(map);

    // Track mouse cursor coordinates
    map.on('mousemove', (e) => {
      if (onCursorMove) {
        onCursorMove({
          lat: e.latlng.lat.toFixed(4),
          lng: e.latlng.lng.toFixed(4)
        });
      }
    });

    mapInstanceRef.current = map;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, [incident]);

  // Update Map Layers & Overlays based on state & activeLayers
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    const layers = layersRef.current;

    // 1. Oil Slick Polygon
    if (layers.slickLayer) {
      map.removeLayer(layers.slickLayer);
      layers.slickLayer = null;
    }

    if (activeLayers.sarSlicks !== false) {
      let slickCoords = [
        [14.8850, 88.1920],
        [14.8980, 88.2450],
        [14.8620, 88.3580],
        [14.8120, 88.3980],
        [14.7750, 88.3450],
        [14.7920, 88.2410],
        [14.8350, 88.1850]
      ];

      // Convert dynamic backend GeoJSON geometry if available
      const rawGeom = incident?.geometry || incident?.slick_polygon || incident?.slick_detections?.[0]?.geometry;
      if (rawGeom) {
        const converted = geoJsonToLeaflet(rawGeom);
        if (converted && Array.isArray(converted) && converted.length > 0) {
          slickCoords = Array.isArray(converted[0]) && Array.isArray(converted[0][0]) ? converted[0] : converted;
        }
      }

      const slickPolygon = L.polygon(slickCoords, {
        color: '#ba1a1a', // Error red
        weight: 2,
        fillColor: '#93000a',
        fillOpacity: 0.45,
        dashArray: '4, 4'
      }).addTo(map);

      slickPolygon.bindTooltip(
        `<strong>Incident ${incident?.id || 'INC-2026-001'}</strong><br/>${incident?.sensor || 'Sentinel-1A C-SAR'} Hydrocarbon Discharge<br/>Area: ${incident?.slickDimensions?.areaKm2 || '46.8'} km² | Confidence: 94%`,
        { sticky: true, className: 'leaflet-tactical-tooltip' }
      );

      slickPolygon.on('click', () => {
        if (onSlickClick) onSlickClick();
      });

      layers.slickLayer = slickPolygon;
    }

    // 2. EEZ Maritime Boundary
    if (layers.eezLayer) {
      map.removeLayer(layers.eezLayer);
      layers.eezLayer = null;
    }
    if (activeLayers.eezBoundaries !== false) {
      const eezCoords = [
        [16.5000, 86.0000],
        [15.8000, 87.5000],
        [14.2000, 89.2000],
        [12.8000, 90.5000]
      ];
      const eezPoly = L.polyline(eezCoords, {
        color: '#a2f0ef',
        weight: 1.5,
        dashArray: '8, 8',
        opacity: 0.8
      }).addTo(map);
      eezPoly.bindTooltip('Exclusive Economic Zone (EEZ) Boundary', { sticky: true });
      layers.eezLayer = eezPoly;
    }

    // 3. Commercial Shipping Lane
    if (layers.shippingLaneLayer) {
      map.removeLayer(layers.shippingLaneLayer);
      layers.shippingLaneLayer = null;
    }
    if (activeLayers.shippingLanes !== false) {
      const laneCoords = [
        [14.5000, 86.5000],
        [14.7500, 88.0000],
        [14.8500, 88.5000],
        [15.1000, 90.0000]
      ];
      const lanePoly = L.polyline(laneCoords, {
        color: '#e9e8e7',
        weight: 2,
        dashArray: '3, 6',
        opacity: 0.4
      }).addTo(map);
      lanePoly.bindTooltip('International Maritime Transit Corridor', { sticky: true });
      layers.shippingLaneLayer = lanePoly;
    }

    // 4. Vessel Trajectories
    layers.vesselTrackLayers.forEach(l => map.removeLayer(l));
    layers.vesselTrackLayers = [];

    if (activeLayers.vesselTracks !== false) {
      // MSC Ocean Star Trajectory (Primary Suspect - Cyan)
      const mscTrajectory = [
        [14.6210, 87.9120],
        [14.7140, 88.0850],
        [14.7820, 88.2140],
        [14.8214, 88.2915], // epicenter
        [14.8490, 88.3420],
        [14.8910, 88.3980],
        [14.9542, 88.4218]
      ];

      const mscTrack = L.polyline(mscTrajectory, {
        color: '#096969',
        weight: 3,
        opacity: 0.9
      }).addTo(map);

      mscTrack.bindTooltip('<strong>MSC Ocean Star (Liberia)</strong><br/>Track overlap: 96% | Proximity: 0.8 km', { sticky: true });
      layers.vesselTrackLayers.push(mscTrack);

      // Nordic Voyager (Secondary Suspect - Amber)
      const nordicTrajectory = [
        [14.9000, 88.1000],
        [15.0500, 88.4000],
        [15.2105, 88.7512]
      ];
      const nordicTrack = L.polyline(nordicTrajectory, {
        color: '#b97958',
        weight: 2,
        dashArray: '5, 5',
        opacity: 0.7
      }).addTo(map);
      nordicTrack.bindTooltip('<strong>Nordic Voyager (Norway)</strong><br/>Proximity: 4.2 km (68% Match)', { sticky: true });
      layers.vesselTrackLayers.push(nordicTrack);

      // Anomaly Point Marker (Discharge Epicenter)
      const anomalyIcon = L.divIcon({
        className: 'custom-anomaly-icon',
        html: `
          <div class="relative flex items-center justify-center">
            <div class="w-6 h-6 rounded-full bg-error/30 animate-ping absolute"></div>
            <div class="w-3.5 h-3.5 rounded-full bg-error border-2 border-white shadow-md"></div>
          </div>
        `,
        iconSize: [24, 24],
        iconAnchor: [12, 12]
      });

      const epicenterMarker = L.marker([14.8214, 88.2915], { icon: anomalyIcon }).addTo(map);
      epicenterMarker.bindPopup(`
        <div class="p-2 text-on-surface">
          <strong class="text-error font-bold text-label-md block mb-1">Discharge Origin Point</strong>
          <div class="text-[12px] space-y-1 font-mono">
            <div>Coords: 14°49'17"N, 88°17'29"E</div>
            <div>Time: 2026-08-26 23:15 UTC</div>
            <div>Nearest Suspect: MSC Ocean Star (0.8 km)</div>
          </div>
        </div>
      `);
      layers.vesselTrackLayers.push(epicenterMarker);
    }

    // 5. Animated Position Marker for Temporal Playback
    if (layers.animatedVesselMarker) {
      map.removeLayer(layers.animatedVesselMarker);
      layers.animatedVesselMarker = null;
    }

    const mscTrajectory = [
      [14.6210, 87.9120],
      [14.7140, 88.0850],
      [14.7820, 88.2140],
      [14.8214, 88.2915],
      [14.8490, 88.3420],
      [14.8910, 88.3980],
      [14.9542, 88.4218]
    ];

    const currentPos = mscTrajectory[Math.min(currentTimeIndex, mscTrajectory.length - 1)];

    const vesselShipIcon = L.divIcon({
      className: 'custom-vessel-ship-icon',
      html: `
        <div class="relative flex items-center justify-center cursor-pointer group">
          <div class="w-8 h-8 rounded-full bg-secondary/30 border border-secondary flex items-center justify-center text-secondary shadow-lg">
            <svg class="w-4 h-4 transform rotate-45" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2L4 21l8-4 8 4L12 2z"/>
            </svg>
          </div>
          <div class="absolute -top-8 px-2 py-0.5 bg-primary text-on-primary text-[10px] font-bold rounded whitespace-nowrap opacity-90 shadow-md">
            MSC Ocean Star (6.1 kts)
          </div>
        </div>
      `,
      iconSize: [32, 32],
      iconAnchor: [16, 16]
    });

    const vesselMarker = L.marker(currentPos, { icon: vesselShipIcon }).addTo(map);
    vesselMarker.on('click', () => {
      if (onVesselClick) onVesselClick('MSC Ocean Star');
    });

    layers.animatedVesselMarker = vesselMarker;

  }, [activeLayers, currentTimeIndex]);

  return (
    <div className="relative w-full h-full min-h-[500px] overflow-hidden rounded-lg border border-outline-variant bg-[#0b1426]">
      <div ref={mapContainerRef} className="w-full h-full" />
    </div>
  );
}
