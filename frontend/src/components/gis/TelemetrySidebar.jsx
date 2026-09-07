import React from 'react';
import StatusChip from '../common/StatusChip';
import Button from '../common/Button';

export default function TelemetrySidebar({
  incident,
  candidateVessels = [],
  cursorCoords,
  onNavigateAttribution,
  onNavigateDossier
}) {
  const primarySuspect = candidateVessels[0] || incident?.primarySuspect || {};

  return (
    <div className="w-full lg:w-96 flex flex-col gap-4 bg-surface-container-lowest border border-outline-variant rounded-lg p-5 overflow-y-auto">
      {/* Incident Header */}
      <div className="border-b border-outline-variant pb-4">
        <div className="flex items-center justify-between mb-2">
          <StatusChip status={incident?.severity || 'Critical'} label="Active Investigation" />
          <span className="font-mono text-label-sm font-bold text-primary">
            {incident?.id || 'INC-2026-001'}
          </span>
        </div>
        <h2 className="text-title-lg font-bold text-primary leading-snug">
          {incident?.title || 'Major Marine Hydrocarbon Discharge'}
        </h2>
        <p className="text-label-sm text-on-surface-variant mt-1">
          {incident?.zone || 'Bay of Bengal / Sector 4'}
        </p>
      </div>

      {/* Live Cursor Telemetry */}
      <div className="p-3 bg-surface-container-low rounded border border-outline-variant text-label-sm flex items-center justify-between font-mono">
        <span className="text-on-surface-variant flex items-center gap-1">
          <span className="material-symbols-outlined text-[16px] text-secondary">explore</span>
          Cursor Coords:
        </span>
        <strong className="text-primary">
          {cursorCoords
            ? `${cursorCoords.lat}°N, ${Math.abs(Number(cursorCoords.lng)).toFixed(4)}°${Number(cursorCoords.lng) >= 0 ? 'E' : 'W'}`
            : (incident?.coordinates?.formatted || '14.8214°N, 88.2915°E')}
        </strong>
      </div>

      {/* Slick Geometry & SAR Physical Attributes */}
      <div className="space-y-3">
        <span className="text-label-sm font-bold uppercase tracking-wider text-primary block">
          Satellite Slick Geometry
        </span>

        <div className="grid grid-cols-2 gap-2 text-label-sm">
          <div className="p-2.5 bg-surface-container rounded border border-outline-variant/60">
            <span className="text-[11px] text-on-surface-variant block">Surface Area</span>
            <strong className="text-primary font-mono text-[14px]">
              {incident?.slickDimensions?.areaKm2 != null ? `${incident.slickDimensions.areaKm2} km²` : 'N/A'}
            </strong>
          </div>
          <div className="p-2.5 bg-surface-container rounded border border-outline-variant/60">
            <span className="text-[11px] text-on-surface-variant block">Plume Length</span>
            <strong className="text-primary font-mono text-[14px]">
              {incident?.slickDimensions?.lengthKm && incident.slickDimensions.lengthKm !== 'N/A' ? `${incident.slickDimensions.lengthKm} km` : 'N/A'}
            </strong>
          </div>
          <div className="p-2.5 bg-surface-container rounded border border-outline-variant/60">
            <span className="text-[11px] text-on-surface-variant block">Discharge Est.</span>
            <strong className="text-error font-mono text-[14px]">
              {incident?.slickDimensions?.estimatedVolumeTonnes || 'Not estimated'}
            </strong>
          </div>
          <div className="p-2.5 bg-surface-container rounded border border-outline-variant/60">
            <span className="text-[11px] text-on-surface-variant block">Plume Drift</span>
            <strong className="text-primary font-mono text-[13px]">
              {incident?.slickDimensions?.driftVector || 'N/A'}
            </strong>
          </div>
        </div>
      </div>

      {/* Suspect Attribution Summary Box */}
      <div className="p-4 bg-surface-container-high rounded-lg border border-outline-variant space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-label-sm font-bold text-primary uppercase tracking-wider">
            {primarySuspect.name === 'Pending AIS Correlation' ? 'Attribution Status' : 'Attribution Candidate #1'}
          </span>
          <StatusChip
            status={primarySuspect.name === 'Pending AIS Correlation' ? 'Investigating' : 'Attributed'}
            label={primarySuspect.name === 'Pending AIS Correlation' ? 'AIS Pending' : `${incident?.confidence || 94}% Confidence`}
            size="sm"
          />
        </div>

        <div>
          <h4 className="text-title-lg font-bold text-primary">
            {primarySuspect.name || 'MSC Ocean Star'}
          </h4>
          <div className="flex items-center gap-2 text-[12px] text-on-surface-variant mt-0.5">
            <span>{primarySuspect.flag || 'Liberia'}</span>
            <span>•</span>
            <span className="font-mono">IMO: {primarySuspect.imo || '9412345'}</span>
            <span>•</span>
            <span>{primarySuspect.type || primarySuspect.vesselType || 'Crude Oil Tanker'}</span>
          </div>
        </div>

        <div className="p-2.5 bg-surface-container-lowest rounded border border-outline-variant/80 text-[12px] text-on-surface leading-relaxed">
          <strong className="text-error block mb-0.5">Discharge Correlation:</strong>
          {primarySuspect.name === 'Pending AIS Correlation'
            ? 'Real satellite radar detection cataloged. Vessel AIS back-hindcast correlation is queued.'
            : (
              <>
                Vessel transited <strong>0.8 km</strong> from calculated origin at 23:15 UTC. Recorded sudden speed deceleration from 14.2 to 6.1 knots during plume generation.
              </>
            )}
        </div>

        <div className="grid grid-cols-2 gap-2 text-[12px]">
          <div className="flex justify-between border-b border-outline-variant/40 pb-1">
            <span className="text-on-surface-variant">Track Overlap:</span>
            <strong className="text-primary font-mono">{primarySuspect.name === 'Pending AIS Correlation' ? 'Pending' : '96%'}</strong>
          </div>
          <div className="flex justify-between border-b border-outline-variant/40 pb-1">
            <span className="text-on-surface-variant">Time Delta:</span>
            <strong className="text-primary font-mono">{primarySuspect.name === 'Pending AIS Correlation' ? 'Pending' : '18 mins'}</strong>
          </div>
          <div className="flex justify-between border-b border-outline-variant/40 pb-1">
            <span className="text-on-surface-variant">Confidence:</span>
            <strong className="text-primary font-mono">{incident?.confidence ? `${incident.confidence}%` : '94%'}</strong>
          </div>
          <div className="flex justify-between border-b border-outline-variant/40 pb-1">
            <span className="text-on-surface-variant">Severity:</span>
            <strong className="text-error font-mono">{incident?.severity || 'HIGH'}</strong>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex flex-col gap-2 mt-auto pt-2">
        <Button
          variant="primary"
          icon="fingerprint"
          onClick={onNavigateAttribution}
          className="w-full"
        >
          View Attribution Ranking Matrix
        </Button>
        <Button
          variant="secondary"
          icon="folder_shared"
          onClick={onNavigateDossier}
          className="w-full"
        >
          Open Official Evidence Dossier
        </Button>
      </div>
    </div>
  );
}
