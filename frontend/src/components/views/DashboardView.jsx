import React, { useState, useEffect } from 'react';
import { useNavigation } from '../../context/NavigationContext';
import api from '../../services/api';
import MetricCard from '../common/MetricCard';
import StatusChip from '../common/StatusChip';
import Button from '../common/Button';

export default function DashboardView() {
  const { navigateTo, setActiveIncidentId } = useNavigation();
  const [metrics, setMetrics] = useState(null);
  const [incident, setIncident] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [m, incList, alt] = await Promise.all([
          api.getSystemMetrics(),
          api.getIncidents(),
          api.getAlerts()
        ]);
        setMetrics(m);
        setAlerts(alt);
        if (Array.isArray(incList) && incList.length > 0) {
          setIncident(incList[0]);
          if (setActiveIncidentId) setActiveIncidentId(incList[0].id);
        } else {
          const singleInc = await api.getIncident('INC-2026-001');
          setIncident(singleInc);
        }
      } catch (err) {
        console.error('Error loading dashboard data:', err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-3 border-primary border-t-transparent rounded-full animate-spin"></div>
          <span className="text-label-sm text-on-surface-variant font-semibold">
            Loading National Surveillance Matrix...
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 animate-in fade-in duration-150">
      {/* Page Title Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-headline-lg font-bold text-primary tracking-tight">
            Command & Control Dashboard
          </h1>
          <p className="text-body-md text-on-surface-variant">
            Real-time satellite surveillance, automated anomaly attribution, and maritime enforcement readiness.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="secondary"
            icon="radar"
            onClick={() => navigateTo('detection')}
          >
            Detection Registry
          </Button>
          <Button
            variant="primary"
            icon="map"
            onClick={() => navigateTo('gis', { incidentId: incident?.id })}
          >
            Launch GIS Workspace
          </Button>
        </div>
      </div>

      {/* KPI Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Active Incidents"
          value={metrics?.activeIncidents || '3'}
          change={metrics?.activeIncidentsChange}
          subtext="1 Critical discharge under attribution"
          icon="crisis_alert"
          accent="error"
          onClick={() => navigateTo('detection')}
        />
        <MetricCard
          label="Monitored Vessels"
          value={metrics?.monitoredVessels?.toLocaleString() || '1,428'}
          change={metrics?.monitoredVesselsChange}
          subtext="AIS transponders actively tracking"
          icon="directions_boat"
          accent="primary"
          onClick={() => navigateTo('attribution')}
        />
        <MetricCard
          label="Verified Slick Area"
          value={metrics?.verifiedSlicksArea || '184.6 km²'}
          subtext="Across 12 confirmed satellite passes"
          icon="water_drop"
          accent="secondary"
          onClick={() => navigateTo('detection')}
        />
        <MetricCard
          label="Attribution Confidence"
          value={metrics?.attributionRate || '94.2%'}
          change="Composite ML Score"
          subtext="Spatial-temporal back-trajectory"
          icon="fingerprint"
          accent="secondary"
          onClick={() => navigateTo('attribution')}
        />
      </div>

      {/* Primary Incident Card */}
      {incident && (() => {
        const displayTitle = incident.title || incident.name || 'Oil Spill Anomaly';
        const displaySeverity = incident.severity || 'HIGH';
        const displaySensor = incident.sensor || 'Sentinel-1 C-SAR';
        const displayCoords = incident.coordinates?.formatted ||
          (incident.location?.coordinates ? `${incident.location.coordinates[1].toFixed(4)}° N, ${incident.location.coordinates[0].toFixed(4)}° E` : '09.7200° N, 75.9800° E');
        const displayTimestamp = String(incident.detectionTimestamp || incident.timestamp || new Date().toISOString()).replace('T', ' ').replace('Z', ' UTC');
        const displayArea = incident.slickDimensions?.areaKm2 || '12.4';
        const displayDrift = incident.slickDimensions?.driftVector || '142° @ 1.8 kts';
        const suspectName = incident.primarySuspect?.name || 'MSC ELSA III';
        const suspectFlag = incident.primarySuspect?.flag || 'Liberia';
        const suspectFlagCode = incident.primarySuspect?.flagCode || 'LR';
        const suspectVesselType = incident.primarySuspect?.vesselType || 'Container Ship';
        const suspectImo = incident.primarySuspect?.imo || '9781423';
        const suspectMmsi = incident.primarySuspect?.mmsi || '636019284';

        return (
          <div className="bg-surface-container-lowest border-2 border-primary/30 rounded-lg overflow-hidden shadow-xs">
            {/* Incident Banner Header */}
            <div className="px-6 py-4 bg-primary text-on-primary flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-3 shrink-0 flex-wrap">
                <span className="px-3 py-1 bg-error text-on-error rounded font-bold text-label-sm uppercase tracking-wider animate-pulse whitespace-nowrap shrink-0">
                  {displaySeverity} Anomaly
                </span>
                <span className="text-title-lg font-bold text-on-primary whitespace-nowrap">
                  {String(incident.id).slice(0, 12)}...: {displayTitle}
                </span>
              </div>

              <div className="flex items-center gap-3 text-label-sm shrink-0 whitespace-nowrap">
                <span className="text-on-primary/80 flex items-center gap-1 whitespace-nowrap">
                  <span className="material-symbols-outlined text-[16px] text-secondary-fixed">satellite_alt</span>
                  {displaySensor}
                </span>
                <span className="text-on-primary/40">•</span>
                <span className="text-on-primary/80 font-mono whitespace-nowrap">
                  {displayCoords}
                </span>
              </div>
            </div>

            {/* Incident Body */}
            <div className="p-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Left: Forensic Radar Snapshot Visual */}
              <div className="lg:col-span-1 rounded bg-slate-950 border border-outline-variant p-4 flex flex-col justify-between relative overflow-hidden map-layer min-h-[220px]">
                <div className="flex items-center justify-between z-10">
                  <span className="text-[11px] font-bold text-secondary-fixed bg-slate-900/80 px-2 py-0.5 rounded border border-secondary/40">
                    SAR SATELLITE PASS
                  </span>
                  <span className="text-[11px] font-mono text-slate-300">
                    {displayTimestamp}
                  </span>
                </div>

                {/* Simulated Slick Vector Overlay */}
                <div className="my-auto text-center z-10 py-6">
                  <div className="inline-block relative">
                    <div className="w-24 h-12 rounded-full border-2 border-error bg-error/20 rotate-[-25deg] shadow-[0_0_20px_rgba(239,68,68,0.4)] animate-pulse mx-auto"></div>
                    <span className="text-[11px] font-bold text-error bg-slate-900/90 px-2 py-0.5 rounded border border-error/40 mt-2 inline-block">
                      SLICK: {displayArea} km²
                    </span>
                  </div>
                </div>

                <div className="flex items-center justify-between text-[11px] text-slate-400 z-10 border-t border-slate-800 pt-2">
                  <span>Drift: {displayDrift}</span>
                  <span>Type: Bunker Fuel</span>
                </div>
              </div>

              {/* Middle: Suspect Attribution Details */}
              <div className="lg:col-span-1 flex flex-col justify-between">
                <div>
                  <span className="text-label-sm font-semibold uppercase tracking-wider text-on-surface-variant block mb-1">
                    Primary Attributed Vessel
                  </span>
                  <div className="flex items-center gap-2 mb-2">
                    <h3 className="text-headline-md font-bold text-primary">
                      {suspectName}
                    </h3>
                    <StatusChip status="Attributed" label="94% Match" />
                  </div>

                  <div className="grid grid-cols-2 gap-2 my-3 p-3 bg-surface-container-low rounded border border-outline-variant/60 text-label-sm">
                    <div>
                      <span className="text-on-surface-variant block text-[11px]">Flag / Registry</span>
                      <strong className="text-on-surface">{suspectFlag} ({suspectFlagCode})</strong>
                    </div>
                    <div>
                      <span className="text-on-surface-variant block text-[11px]">Vessel Type</span>
                      <strong className="text-on-surface">{suspectVesselType}</strong>
                    </div>
                    <div>
                      <span className="text-on-surface-variant block text-[11px]">IMO Number</span>
                      <strong className="text-on-surface font-mono">{suspectImo}</strong>
                    </div>
                    <div>
                      <span className="text-on-surface-variant block text-[11px]">MMSI Transponder</span>
                      <strong className="text-on-surface font-mono">{suspectMmsi}</strong>
                    </div>
                  </div>

                  <p className="text-label-sm text-on-surface-variant">
                    Back-trajectory spatial overlap confirms vessel passed within <strong>0.8 km</strong> with an anomalous speed drop (14.2 → 6.1 kts).
                  </p>
                </div>

              <div className="flex items-center gap-2 mt-4 pt-3 border-t border-outline-variant/60">
                <Button
                  size="sm"
                  variant="primary"
                  icon="fingerprint"
                  onClick={() => navigateTo('attribution', { incidentId: incident.id })}
                >
                  Attribution Analysis
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  icon="directions_boat"
                  onClick={() => navigateTo('vessel', { vesselName: incident.primarySuspect.name })}
                >
                  Vessel Profile
                </Button>
              </div>
            </div>

            {/* Right: Quick Forensic Actions & Evidentiary Status */}
            <div className="lg:col-span-1 bg-surface-container-low p-4 rounded border border-outline-variant flex flex-col justify-between">
              <div>
                <span className="text-label-sm font-semibold uppercase tracking-wider text-on-surface-variant block mb-2">
                  Investigation Dossier Status
                </span>
                
                <div className="space-y-2 mb-4">
                  <div className="flex items-center justify-between text-label-sm">
                    <span className="text-on-surface-variant">Chain of Custody ID:</span>
                    <strong className="font-mono text-primary">{incident.chainOfCustodyId || 'CC-2026-0829-01'}</strong>
                  </div>
                  <div className="flex items-center justify-between text-label-sm">
                    <span className="text-on-surface-variant">Assigned Officer:</span>
                    <strong className="text-primary">{incident.assignedInvestigator || 'Cmdr. Rajesh Verma'}</strong>
                  </div>
                  <div className="flex items-center justify-between text-label-sm">
                    <span className="text-on-surface-variant">Estimated Discharge Volume:</span>
                    <strong className="text-error">{incident.slickDimensions?.estimatedVolumeTonnes || '380 MT'}</strong>
                  </div>
                </div>
              </div>

              <div className="flex flex-col gap-2">
                <Button
                  variant="teal"
                  icon="map"
                  onClick={() => navigateTo('gis', { incidentId: incident.id })}
                  className="w-full"
                >
                  Open in GIS Investigation Workspace
                </Button>
                <Button
                  variant="outline"
                  icon="folder_shared"
                  onClick={() => navigateTo('dossier', { incidentId: incident.id })}
                  className="w-full"
                >
                  View Official Evidence Dossier
                </Button>
              </div>
            </div>
          </div>
        </div>
      ); })()}

      {/* Two Column Layout: Regional Sectors + Priority Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Regional Surveillance Sectors (2 cols) */}
        <div className="lg:col-span-2 bg-surface-container-lowest border border-outline-variant rounded p-5 flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-title-lg font-bold text-primary">
                National Maritime Surveillance Sectors
              </h3>
              <p className="text-label-sm text-on-surface-variant">
                Continuous synthetic aperture radar and coastal AIS coverage readiness
              </p>
            </div>
            <span className="font-label-sm text-secondary font-bold flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-secondary animate-pulse"></span>
              All Radar Feeds Live
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="p-3.5 bg-surface-container-low border border-error-container rounded flex flex-col justify-between">
              <div className="flex items-center justify-between mb-2">
                <strong className="text-label-md text-primary font-bold">Sector 4 — Bay of Bengal</strong>
                <StatusChip status="Critical" label="Active Spill" />
              </div>
              <p className="text-label-sm text-on-surface-variant mb-2">
                Incident INC-2026-001 under forensic investigation. 42 vessels tracked in corridor.
              </p>
              <div className="flex items-center justify-between text-[11px] text-on-surface-variant font-mono border-t border-outline-variant/40 pt-1.5">
                <span>Coverage: 99.2%</span>
                <span className="text-error font-bold">14°49'N 88°17'E</span>
              </div>
            </div>

            <div className="p-3.5 bg-surface-container-low border border-outline-variant rounded flex flex-col justify-between">
              <div className="flex items-center justify-between mb-2">
                <strong className="text-label-md text-primary font-bold">Sector 1 — Arabian Sea</strong>
                <StatusChip status="High" label="Investigating" />
              </div>
              <p className="text-label-sm text-on-surface-variant mb-2">
                DET-2026-088 plume identified (18.2 km²). AIS trajectory correlation in progress.
              </p>
              <div className="flex items-center justify-between text-[11px] text-on-surface-variant font-mono border-t border-outline-variant/40 pt-1.5">
                <span>Coverage: 97.5%</span>
                <span className="text-primary font-bold">18°12'N 69°45'E</span>
              </div>
            </div>

            <div className="p-3.5 bg-surface-container-low border border-outline-variant rounded flex flex-col justify-between">
              <div className="flex items-center justify-between mb-2">
                <strong className="text-label-md text-primary font-bold">Sector 2 — Gulf of Mannar</strong>
                <StatusChip status="Medium" label="Investigating" />
              </div>
              <p className="text-label-sm text-on-surface-variant mb-2">
                Minor 7.4 km² slick observed near coral biosphere reserve. Coastal patrol alerted.
              </p>
              <div className="flex items-center justify-between text-[11px] text-on-surface-variant font-mono border-t border-outline-variant/40 pt-1.5">
                <span>Coverage: 98.1%</span>
                <span className="text-primary font-bold">08°44'N 78°51'E</span>
              </div>
            </div>

            <div className="p-3.5 bg-surface-container-low border border-outline-variant rounded flex flex-col justify-between">
              <div className="flex items-center justify-between mb-2">
                <strong className="text-label-md text-primary font-bold">Sector 3 — Andaman & Nicobar</strong>
                <StatusChip status="Clear" label="Nominal" />
              </div>
              <p className="text-label-sm text-on-surface-variant mb-2">
                No active anomalies. Routine AIS compliance monitoring and satellite passes green.
              </p>
              <div className="flex items-center justify-between text-[11px] text-on-surface-variant font-mono border-t border-outline-variant/40 pt-1.5">
                <span>Coverage: 99.8%</span>
                <span className="text-secondary font-bold">Clear Zone</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right: Real-time Priority Alerts (1 col) */}
        <div className="bg-surface-container-lowest border border-outline-variant rounded p-5 flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-title-lg font-bold text-primary">
              Recent Alerts Feed
            </h3>
            <button
              onClick={() => navigateTo('alerts')}
              className="text-label-sm text-primary font-bold hover:underline"
            >
              View All ({alerts.length})
            </button>
          </div>

          <div className="flex flex-col gap-3 overflow-y-auto max-h-[340px] pr-1">
            {alerts.slice(0, 4).map((alert) => (
              <div
                key={alert.id}
                onClick={() => navigateTo('alerts')}
                className="p-3 rounded bg-surface-container-low border border-outline-variant/70 hover:border-primary cursor-pointer transition-colors"
              >
                <div className="flex items-center justify-between mb-1">
                  <StatusChip status={alert.severity} size="sm" />
                  <span className="text-[11px] font-mono text-on-surface-variant">
                    {alert.timestamp.substring(11, 19)}
                  </span>
                </div>
                <h4 className="text-label-md font-bold text-primary leading-snug line-clamp-1">
                  {alert.title}
                </h4>
                <p className="text-[12px] text-on-surface-variant line-clamp-2 mt-1">
                  {alert.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
