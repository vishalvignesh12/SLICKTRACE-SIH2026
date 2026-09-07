import React from 'react';

/**
 * LayerControls Component
 * Floating or panel-mounted layer toggles for GIS forensics workspace
 */
export default function LayerControls({ incident, activeLayers, onToggleLayer }) {
  const isRealSAR = Boolean(
    incident?.source_scene_id?.startsWith('REAL-SAR') ||
    (incident?.coordinates?.lng < 0 && Math.abs(incident?.coordinates?.lng) > 80)
  );

  const displayArea = incident?.slickDimensions?.areaKm2 != null
    ? incident.slickDimensions.areaKm2
    : (incident?.area_km2 != null ? Number(incident.area_km2).toFixed(1) : (isRealSAR ? '19.5' : '46.8'));

  const sarDesc = `Sentinel-1A polygon (${displayArea} km²)`;
  const vesselDesc = isRealSAR ? 'AIS correlation pending' : 'MSC Ocean Star & candidates';

  const layerDefinitions = [
    { id: 'sarSlicks', label: 'SAR Oil Slicks', color: 'bg-error', desc: sarDesc },
    { id: 'vesselTracks', label: 'AIS Vessel Trajectories', color: 'bg-secondary', desc: vesselDesc },
    { id: 'eezBoundaries', label: 'EEZ Maritime Boundary', color: 'bg-secondary-fixed', desc: 'Exclusive Economic Zone' },
    { id: 'shippingLanes', label: 'Shipping Corridors', color: 'bg-outline-variant', desc: 'Designated transit lanes' }
  ];

  return (
    <div className="bg-surface-container-lowest border border-outline-variant rounded-lg p-4 shadow-sm flex flex-col gap-3">
      <div className="flex items-center justify-between border-b border-outline-variant pb-2">
        <span className="text-label-sm font-bold text-primary uppercase tracking-wider flex items-center gap-1.5">
          <span className="material-symbols-outlined text-[16px] text-secondary">layers</span>
          Map Geospatial Layers
        </span>
        <span className="text-[11px] text-on-surface-variant">Live Ingestion</span>
      </div>

      <div className="flex flex-col gap-2">
        {layerDefinitions.map((layer) => {
          const isEnabled = activeLayers[layer.id] !== false;
          return (
            <label
              key={layer.id}
              className="flex items-start justify-between gap-3 p-2 rounded hover:bg-surface-container-high cursor-pointer transition-colors"
            >
              <div className="flex items-start gap-2.5">
                <span className={`w-2.5 h-2.5 rounded-full mt-1 ${layer.color}`}></span>
                <div>
                  <strong className="text-label-sm text-primary block leading-tight">
                    {layer.label}
                  </strong>
                  <span className="text-[11px] text-on-surface-variant block leading-tight">
                    {layer.desc}
                  </span>
                </div>
              </div>

              <input
                type="checkbox"
                checked={isEnabled}
                onChange={() => onToggleLayer(layer.id)}
                className="mt-0.5 rounded border-outline text-primary focus:ring-primary h-4 w-4 cursor-pointer"
              />
            </label>
          );
        })}
      </div>
    </div>
  );
}
