import React, { useState, useEffect } from 'react';
import { useNavigation } from '../../context/NavigationContext';
import api from '../../services/api';
import StatusChip from '../common/StatusChip';
import Button from '../common/Button';

export default function VesselProfileView() {
  const { selectedVesselName, activeIncidentId, navigateTo } = useNavigation();
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadProfile() {
      try {
        const data = await api.getVesselProfile(selectedVesselName || 'MSC Ocean Star');
        setProfile(data);
      } catch (err) {
        console.error('Error loading vessel profile:', err);
      } finally {
        setLoading(false);
      }
    }
    loadProfile();
  }, [selectedVesselName]);

  if (loading || !profile) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-3 border-primary border-t-transparent rounded-full animate-spin"></div>
          <span className="text-label-sm text-on-surface-variant font-semibold">
            Retrieving Vessel Forensic Profile (Fixture AIS Data)...
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 animate-in fade-in duration-150">
      {/* Top Breadcrumb & Actions Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <h1 className="text-headline-lg font-bold text-primary tracking-tight">
              Vessel Forensic Profile
            </h1>
            <StatusChip status="Critical" label={`Primary Suspect${profile?.confidence != null ? `: ${profile.confidence}% Attribution` : ''}`} />
            <span className="px-2 py-0.5 bg-amber-100 text-amber-800 border border-amber-300 text-[10px] font-bold uppercase tracking-wider rounded font-mono">
              AIS: Fixture Data
            </span>
          </div>
          <p className="text-body-md text-on-surface-variant">
            Official maritime registry records, ownership structure, MARPOL compliance history, and AIS telemetry audit.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="teal"
            icon="map"
            onClick={() => navigateTo('gis', { incidentId: activeIncidentId })}
          >
            Track in GIS Workspace
          </Button>
          <Button
            variant="primary"
            icon="folder_shared"
            onClick={() => navigateTo('dossier', { incidentId: activeIncidentId })}
          >
            Add to Evidence Dossier
          </Button>
        </div>
      </div>

      {/* Hero Header Card */}
      <div className="bg-surface-container-lowest border border-outline-variant rounded-lg p-6 flex flex-col md:flex-row justify-between gap-6 shadow-xs">
        <div className="flex items-start gap-4">
          <div className="w-14 h-14 rounded-lg bg-primary-container text-on-primary flex items-center justify-center font-bold text-2xl shrink-0">
            <span className="material-symbols-outlined text-[32px]">directions_boat</span>
          </div>

          <div>
            <div className="flex flex-wrap items-center gap-3 mb-1">
              <h2 className="text-headline-md font-bold text-primary">{profile.name}</h2>
              <span className="px-2.5 py-0.5 rounded bg-surface-container-high border border-outline-variant font-semibold text-label-sm text-on-surface">
                Flag: {profile.flag} ({profile.flagCode})
              </span>
              <span className="px-2.5 py-0.5 rounded bg-secondary-container text-on-secondary-container font-semibold text-label-sm">
                Call Sign: {profile.callSign}
              </span>
            </div>

            <p className="text-label-sm text-on-surface-variant">
              Owner: <strong className="text-primary">{profile.owner}</strong> • Operator: <strong className="text-primary">{profile.operator}</strong>
            </p>
          </div>
        </div>

        <div className="flex flex-wrap md:flex-col justify-end items-end gap-1 text-right">
          <span className="text-[11px] text-on-surface-variant uppercase tracking-wider font-semibold">
            Registry Identifiers
          </span>
          <div className="font-mono text-label-md text-primary font-bold">
            IMO: {profile.imo} | MMSI: {profile.mmsi}
          </div>
          <span className="text-[12px] text-secondary font-semibold">
            Class: {profile.classificationSociety} • P&I: {profile.pAndIClub}
          </span>
        </div>
      </div>

      {/* Technical Specifications 4-Column Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 bg-surface-container-lowest border border-outline-variant rounded">
          <span className="text-[11px] font-bold uppercase tracking-wider text-on-surface-variant block mb-1">
            Vessel Dimensions
          </span>
          <div className="space-y-1 text-label-sm">
            <div className="flex justify-between">
              <span className="text-on-surface-variant">Length Overall:</span>
              <strong className="text-primary font-mono">{profile.lengthMeters} m</strong>
            </div>
            <div className="flex justify-between">
              <span className="text-on-surface-variant">Beam:</span>
              <strong className="text-primary font-mono">{profile.beamMeters} m</strong>
            </div>
            <div className="flex justify-between">
              <span className="text-on-surface-variant">Draught:</span>
              <strong className="text-primary font-mono">{profile.draughtMeters} m</strong>
            </div>
          </div>
        </div>

        <div className="p-4 bg-surface-container-lowest border border-outline-variant rounded">
          <span className="text-[11px] font-bold uppercase tracking-wider text-on-surface-variant block mb-1">
            Tonnage & Hull
          </span>
          <div className="space-y-1 text-label-sm">
            <div className="flex justify-between">
              <span className="text-on-surface-variant">Deadweight (DWT):</span>
              <strong className="text-primary font-mono">{profile.dwt?.toLocaleString()} MT</strong>
            </div>
            <div className="flex justify-between">
              <span className="text-on-surface-variant">Gross Tonnage:</span>
              <strong className="text-primary font-mono">{profile.grossTonnage}</strong>
            </div>
            <div className="flex justify-between">
              <span className="text-on-surface-variant">Hull Design:</span>
              <strong className="text-secondary">{profile.hullType}</strong>
            </div>
          </div>
        </div>

        <div className="p-4 bg-surface-container-lowest border border-outline-variant rounded">
          <span className="text-[11px] font-bold uppercase tracking-wider text-on-surface-variant block mb-1">
            Propulsion Machinery
          </span>
          <div className="space-y-1 text-label-sm">
            <div className="flex justify-between">
              <span className="text-on-surface-variant">Main Engine:</span>
              <strong className="text-primary text-[12px]">{profile.engineType}</strong>
            </div>
            <div className="flex justify-between">
              <span className="text-on-surface-variant">Built Year:</span>
              <strong className="text-primary font-mono">{profile.builtYear}</strong>
            </div>
            <div className="flex justify-between">
              <span className="text-on-surface-variant">Fuel Bunkers:</span>
              <strong className="text-primary font-mono">{profile.currentVoyage?.fuelBunkers}</strong>
            </div>
          </div>
        </div>

        <div className="p-4 bg-surface-container-lowest border border-outline-variant rounded">
          <span className="text-[11px] font-bold uppercase tracking-wider text-on-surface-variant block mb-1">
            Voyage Cargo Manifest
          </span>
          <div className="space-y-1 text-label-sm">
            <div className="flex justify-between">
              <span className="text-on-surface-variant">Cargo Type:</span>
              <strong className="text-error">{profile.currentVoyage?.cargoManifest}</strong>
            </div>
            <div className="flex justify-between">
              <span className="text-on-surface-variant">Origin Port:</span>
              <strong className="text-primary text-[12px]">{profile.currentVoyage?.originPort}</strong>
            </div>
            <div className="flex justify-between">
              <span className="text-on-surface-variant">Destination:</span>
              <strong className="text-primary text-[12px]">{profile.currentVoyage?.destinationPort}</strong>
            </div>
          </div>
        </div>
      </div>

      {/* Two Column Section: Compliance History + AIS Telemetry Waypoints */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Prior Compliance Infractions Table */}
        <div className="bg-surface-container-lowest border border-outline-variant rounded-lg p-5 flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-title-lg font-bold text-primary">
              MARPOL & Port State Control Compliance
            </h3>
            <span className="text-label-sm text-error font-semibold flex items-center gap-1">
              <span className="material-symbols-outlined text-[16px]">warning</span>
              2 Historical Deficiencies
            </span>
          </div>

          <div className="divide-y divide-outline-variant/60">
            {profile.priorViolations?.map((violation, idx) => (
              <div key={idx} className="py-3 text-label-sm space-y-1">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-primary font-bold">{violation.date}</span>
                  <span className="text-on-surface-variant">{violation.port}</span>
                </div>
                <p className="text-error font-semibold">{violation.deficiency}</p>
                <p className="text-[12px] text-on-surface-variant">Action: {violation.action}</p>
              </div>
            ))}
          </div>
        </div>

        {/* AIS Trajectory Waypoint Log Table */}
        <div className="bg-surface-container-lowest border border-outline-variant rounded-lg p-5 flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-title-lg font-bold text-primary">
              Incident Interval AIS Telemetry
            </h3>
            <span className="font-mono text-label-sm text-secondary font-bold">
              Bay of Bengal Corridor
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-[12px] border-collapse">
              <thead>
                <tr className="bg-surface-container-low border-b border-outline-variant text-label-sm font-bold text-primary">
                  <th className="py-2 px-2">Time (UTC)</th>
                  <th className="py-2 px-2">Latitude</th>
                  <th className="py-2 px-2">Longitude</th>
                  <th className="py-2 px-2">Speed</th>
                  <th className="py-2 px-2">Heading</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant/50 font-mono">
                {profile.aisTrajectory?.map((pt, idx) => {
                  const isAnomalous = pt.speed < 10;
                  return (
                    <tr key={idx} className={isAnomalous ? 'bg-error-container/30 text-error font-bold' : ''}>
                      <td className="py-2 px-2">{pt.time.substring(11, 19)}</td>
                      <td className="py-2 px-2">{pt.lat}°N</td>
                      <td className="py-2 px-2">{pt.lng}°E</td>
                      <td className="py-2 px-2">
                        {pt.speed} kts {isAnomalous && '⚠️ (Decel)'}
                      </td>
                      <td className="py-2 px-2">{pt.heading}°</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
