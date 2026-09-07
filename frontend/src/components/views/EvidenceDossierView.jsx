import React, { useState, useEffect } from 'react';
import { useNavigation } from '../../context/NavigationContext';
import api from '../../services/api';
import StatusChip from '../common/StatusChip';
import Button from '../common/Button';

export default function EvidenceDossierView() {
  const { activeIncidentId, navigateTo } = useNavigation();
  const [incident, setIncident] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const data = await api.getIncident(activeIncidentId);
        setIncident(data);
      } catch (err) {
        console.error('Error loading dossier:', err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [activeIncidentId]);

  const handlePrint = () => {
    window.print();
  };

  const handleExportCSV = async () => {
    const displayId = String(incident?.id || 'INC-2026-001');
    try {
      let invId = incident?.id;
      // If investigation exists, use investigation id or export
      const csvData = await api.exportInvestigationCsv(invId || '2f8a1304-fe74-4482-8311-5059da82c215');
      const blob = new Blob([csvData], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.setAttribute('href', url);
      link.setAttribute('download', `evidence_dossier_${displayId}_${new Date().toISOString().substring(0, 10)}.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err) {
      console.error('Export CSV failed:', err);
      alert(`Export CSV Notification: ${err.message}`);
    }
  };

  if (loading || !incident) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-3 border-primary border-t-transparent rounded-full animate-spin"></div>
          <span className="text-label-sm text-on-surface-variant font-semibold">
            Compiling Official Legal Evidence Dossier...
          </span>
        </div>
      </div>
    );
  }

  // Mirrors api.js isRealSAR detection (api.js line ~393)
  const lng = incident.location?.coordinates ? incident.location.coordinates[0] : null;
  const isRealSAR = Boolean(
    incident.source_scene_id?.startsWith('REAL-SAR') ||
    (lng !== null && lng < 0 && Math.abs(lng) > 80)
  );
  const isFixture = !isRealSAR;

  const displayId = String(incident.id || 'INC-2026-001');
  const displayChainId = incident.chainOfCustodyId || 'CC-2026-0827-04';
  const displayInvestigator = incident.assignedInvestigator || 'Cmdr. Rajesh Verma';
  const displayCoords = incident.coordinates?.formatted ||
    (incident.location?.coordinates
      ? `${Math.abs(incident.location.coordinates[1]).toFixed(4)}° ${incident.location.coordinates[1] >= 0 ? 'N' : 'S'}, ${Math.abs(incident.location.coordinates[0]).toFixed(4)}° ${incident.location.coordinates[0] >= 0 ? 'E' : 'W'}`
      : '14.8250° N, 88.2410° E');
  const displayArea = incident.slickDimensions?.areaKm2 || '46.8';
  const displayVolume = incident.slickDimensions?.estimatedVolumeTonnes || '420 MT';
  const displayConfidence = incident.confidence ?? 94;
  const displayLengthKm = incident.slickDimensions?.lengthKm;
  const sceneId = incident.source_scene_id || null;

  // Fixture-only vessel fields
  const suspectName = incident.primarySuspect?.name || 'MSC Ocean Star';
  const suspectFlag = incident.primarySuspect?.flag || 'Liberia';
  const suspectImo = incident.primarySuspect?.imo || '9412345';
  const suspectMmsi = incident.primarySuspect?.mmsi || '636018492';
  const suspectVesselType = incident.primarySuspect?.vesselType || 'Crude Oil Tanker';

  return (
    <div className="flex flex-col gap-6 max-w-5xl mx-auto animate-in fade-in duration-150">
      {/* Top Toolbar (Hidden during print) */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 bg-surface-container-lowest border border-outline-variant rounded-lg shadow-xs print:hidden">
        <div>
          <h1 className="text-headline-md font-bold text-primary">
            Official Incident Evidence Dossier
          </h1>
          <p className="text-label-sm text-on-surface-variant">
            Case Reference: <strong className="font-mono text-primary">{displayId}</strong>
            {isFixture && (
              <> • Chain of Custody: <strong className="font-mono text-secondary">{displayChainId}</strong></>
            )}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="teal"
            icon="map"
            onClick={() => navigateTo('gis', { incidentId: incident.id })}
          >
            GIS Forensics Map
          </Button>
          <Button
            variant="outline"
            icon="download"
            onClick={handleExportCSV}
          >
            Export CSV
          </Button>
          <Button
            variant="primary"
            icon="print"
            onClick={handlePrint}
          >
            Export / Print Official Dossier
          </Button>
        </div>
      </div>

      {/* Official Government Dossier Sheet */}
      <div className="bg-surface-container-lowest border border-outline-variant rounded-lg p-8 sm:p-12 shadow-sm text-on-surface space-y-8 print:p-0 print:border-none print:shadow-none">
        {/* Government Header */}
        <div className="border-b-2 border-primary pb-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 bg-primary-container text-on-primary rounded flex items-center justify-center font-bold text-2xl font-sans">
              M
            </div>
            <div>
              <div className="text-[11px] font-bold uppercase tracking-widest text-secondary">
                National Maritime Oversight &amp; Environmental Enforcement
              </div>
              <h2 className="text-headline-md font-bold text-primary tracking-tight">
                Forensic Incident Investigation Report
              </h2>
              <div className="text-label-sm text-on-surface-variant font-mono mt-0.5">
                Statutory Case ID: {displayId} • Classification: {isRealSAR ? 'RESTRICTED / ANALYTICAL' : 'RESTRICTED / LEGAL ADMISSIBLE'}
              </div>
            </div>
          </div>

          <div className="text-left sm:text-right text-label-sm space-y-1">
            <div><strong>Date Generated:</strong> {new Date().toISOString().substring(0, 10)}</div>
            <div><strong>Investigating Unit:</strong> {isRealSAR ? 'SAR Integration Cell' : 'Sector 4 Coast Command'}</div>
            <div><strong>Investigator:</strong> {displayInvestigator}</div>
          </div>
        </div>

        {/* Section 1: Executive Summary */}
        <section className="space-y-3">
          <h3 className="text-title-lg font-bold text-primary border-b border-outline-variant pb-1 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-primary"></span>
            1. Executive Incident Summary
          </h3>

          {isRealSAR ? (
            <>
              <p className="text-body-md leading-relaxed text-on-surface">
                Automated SAR segmentation processing on a <strong>Sentinel-1A</strong> pass detected a
                surface slick signature in the <strong>Gulf of Mexico</strong> region
                {sceneId ? <> (Scene: <strong className="font-mono">{sceneId}</strong>)</> : ''}.{' '}
                The ML model assigned a detection confidence of <strong>{displayConfidence}%</strong>.
                The detected slick covers approximately <strong>{displayArea} km²</strong>.
                Vessel attribution is <strong>pending AIS correlation</strong> — no suspect vessel has been
                identified or attributed to this incident.
              </p>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-4 bg-surface-container-low rounded border border-outline-variant text-label-sm">
                <div>
                  <span className="text-on-surface-variant block text-[11px]">Epicenter Coords</span>
                  <strong className="text-primary font-mono">{displayCoords}</strong>
                </div>
                <div>
                  <span className="text-on-surface-variant block text-[11px]">Detected Slick Area</span>
                  <strong className="text-primary font-mono">{displayArea} km²</strong>
                </div>
                <div>
                  <span className="text-on-surface-variant block text-[11px]">Discharge Volume</span>
                  <strong className="text-on-surface-variant font-mono">Not estimated</strong>
                </div>
                <div>
                  <span className="text-on-surface-variant block text-[11px]">Attribution Status</span>
                  <strong className="text-amber-600 font-bold">AIS Correlation Pending</strong>
                </div>
              </div>
            </>
          ) : (
            <>
              <p className="text-body-md leading-relaxed text-on-surface">
                On <strong>2026-08-27 at 04:15 UTC</strong>, automated synthetic aperture radar (SAR) processing on the <strong>Sentinel-1A</strong> satellite pass detected a major surface hydrocarbon anomaly covering <strong>{displayArea} km²</strong> in international waters within Sector 4 (Bay of Bengal). Spatial-temporal back-trajectory analysis corroborates deliberate bilge discharge or catastrophic bunker leakage from crude oil tanker <strong>{suspectName}</strong> ({suspectFlag} Flag, IMO {suspectImo}) with a <strong>94% statistical confidence attribution</strong>.
              </p>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-4 bg-surface-container-low rounded border border-outline-variant text-label-sm">
                <div>
                  <span className="text-on-surface-variant block text-[11px]">Epicenter Coords</span>
                  <strong className="text-primary font-mono">{displayCoords}</strong>
                </div>
                <div>
                  <span className="text-on-surface-variant block text-[11px]">Calculated Spill Area</span>
                  <strong className="text-primary font-mono">{displayArea} km²</strong>
                </div>
                <div>
                  <span className="text-on-surface-variant block text-[11px]">Discharge Volume</span>
                  <strong className="text-error font-mono">{displayVolume}</strong>
                </div>
                <div>
                  <span className="text-on-surface-variant block text-[11px]">Attribution Status</span>
                  <strong className="text-secondary font-bold">Confirmed (94%)</strong>
                </div>
              </div>
            </>
          )}
        </section>

        {/* Section 2: Satellite SAR & Physical Observations */}
        <section className="space-y-3">
          <h3 className="text-title-lg font-bold text-primary border-b border-outline-variant pb-1 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-primary"></span>
            2. Satellite SAR &amp; Physical Observations
            {isFixture && (
              <span className="ml-2 px-2 py-0.5 bg-amber-100 text-amber-800 border border-amber-300 text-[10px] font-bold uppercase tracking-wider rounded font-mono">FIXTURE DATA — Sentinel-1A Real Integration Pending</span>
            )}
          </h3>

          {isRealSAR ? (
            <>
              <p className="text-body-md text-on-surface-variant">
                SAR segmentation detected a surface slick signature with{' '}
                <strong>{displayConfidence}% model confidence</strong> covering approximately{' '}
                <strong>{displayArea} km²</strong>. The ML model classifies this as a detected slick
                region; material composition (hydrocarbon vs. look-alike) requires independent in-situ
                or spectral verification.
              </p>
              <div className="p-4 bg-slate-950 text-slate-200 rounded border border-slate-800 font-mono text-[12px] space-y-2">
                <div className="text-secondary-fixed font-bold"># SAR DETECTION TELEMETRY LOG</div>
                <div>Satellite Constellation: Copernicus Sentinel-1A (C-Band SAR)</div>
                <div>Scene ID: {sceneId || 'Not available from current dataset'}</div>
                <div>Orbit / Swath Mode: Not available from current dataset</div>
                <div>Acquisition Timestamp: Not available from current dataset</div>
                <div>Detection Epicenter: {displayCoords}</div>
                <div>Detected Slick Area: {displayArea} km²</div>
                <div>Plume Length: {displayLengthKm && displayLengthKm !== 'N/A' ? `${displayLengthKm} km` : 'Not available from current dataset'}</div>
                <div>Drift Vector / Surface Current: Not available from current dataset</div>
                <div>Material Classification: Not available from current dataset — SAR look-alike discrimination pending</div>
                <div>ML Model Confidence: {displayConfidence}%</div>
              </div>
            </>
          ) : (
            <>
              <p className="text-body-md text-on-surface-variant">
                Radar backscatter suppression confirms damping of capillary ocean waves consistent with mineral oil slick emulsion.
              </p>
              <div className="p-4 bg-slate-950 text-slate-200 rounded border border-slate-800 font-mono text-[12px] space-y-2">
                <div className="text-secondary-fixed font-bold"># SATELLITE TELEMETRY INGESTION LOG</div>
                <div>Satellite Constellation: Copernicus Sentinel-1A (C-Band SAR)</div>
                <div>Orbit / Swath Mode: Ascending Pass #1428 / Interferometric Wide Swath (IW)</div>
                <div>Slick Boundary Extents: 14.885°N, 88.192°E to 14.775°N, 88.345°E (Length: 28.4 km)</div>
                <div>Drift Vector Analysis: Surface current 112° at 1.4 kts (East-Southeast)</div>
                <div>Hydrocarbon Signature: Bunker C Fuel Oil / Heavy Crude Fraction</div>
              </div>
            </>
          )}
        </section>

        {/* Section 3: Suspect Vessel Attribution Proofs */}
        <section className="space-y-3">
          <h3 className="text-title-lg font-bold text-primary border-b border-outline-variant pb-1 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-primary"></span>
            3. Vessel Attribution &amp; Trajectory Evidence
          </h3>

          {isRealSAR ? (
            <div className="p-6 bg-surface-container-high rounded border border-outline-variant space-y-4">
              <div className="flex items-center gap-3">
                <svg className="w-8 h-8 text-amber-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9.348 14.651a3 3 0 010-5.303m5.304 0a3 3 0 010 5.303m-7.425 2.122a6.75 6.75 0 010-9.546m9.546 0a6.75 6.75 0 010 9.546M5.106 18.894c-3.808-3.808-3.808-9.98 0-13.789m13.788 0c3.808 3.808 3.808 9.98 0 13.788M12 12h.008v.008H12V12z" />
                </svg>
                <div>
                  <strong className="text-title-lg text-amber-600">AIS Correlation Pending</strong>
                  <p className="text-label-sm text-on-surface-variant mt-0.5">
                    No suspect vessel has been identified or attributed to this incident.
                  </p>
                </div>
              </div>

              <div className="p-4 bg-amber-50 border border-amber-200 rounded text-[13px] text-amber-900 leading-relaxed space-y-2">
                <p>
                  <strong>This is not an attribution result.</strong> SAR segmentation detected a surface
                  slick signature with <strong>{displayConfidence}% model confidence</strong> covering
                  approximately <strong>{displayArea} km²</strong> near {displayCoords}.
                </p>
                <p>
                  Vessel attribution requires historical AIS track data for the slick time window and
                  location. No AIS tracks have been ingested for this observation area. Attribution will
                  be calculated after AIS correlation is completed.
                </p>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-label-sm">
                <div className="p-3 bg-surface-container-low rounded border border-outline-variant">
                  <span className="text-on-surface-variant block text-[11px]">Suspect Vessel</span>
                  <strong className="text-on-surface-variant">Not identified</strong>
                </div>
                <div className="p-3 bg-surface-container-low rounded border border-outline-variant">
                  <span className="text-on-surface-variant block text-[11px]">IMO Number</span>
                  <strong className="text-on-surface-variant font-mono">N/A</strong>
                </div>
                <div className="p-3 bg-surface-container-low rounded border border-outline-variant">
                  <span className="text-on-surface-variant block text-[11px]">MMSI</span>
                  <strong className="text-on-surface-variant font-mono">N/A</strong>
                </div>
                <div className="p-3 bg-surface-container-low rounded border border-outline-variant">
                  <span className="text-on-surface-variant block text-[11px]">Attribution Score</span>
                  <strong className="text-amber-600 font-bold">Pending</strong>
                </div>
              </div>

              <p className="text-label-sm text-on-surface-variant italic">
                AIS telemetry data is not available from the current observation dataset. No speed, heading,
                or proximity data can be reported until historical AIS tracks are ingested for this region
                and time window.
              </p>
            </div>
          ) : (
            <div className="p-4 bg-surface-container-high rounded border border-outline-variant space-y-3">
              <div className="flex items-center justify-between">
                <strong className="text-title-lg text-primary">{suspectName}</strong>
                <StatusChip status="Attributed" label="Attribution: 94%" />
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-label-sm text-on-surface">
                <div><span>Flag:</span> <strong>{suspectFlag}</strong></div>
                <div><span>IMO:</span> <strong className="font-mono">{suspectImo}</strong></div>
                <div><span>MMSI:</span> <strong className="font-mono">{suspectMmsi}</strong></div>
                <div><span>Vessel Type:</span> <strong>{suspectVesselType}</strong></div>
              </div>

              <div className="p-3 bg-surface-container-lowest rounded border border-outline-variant text-[12px] text-on-surface leading-relaxed">
                <strong>Forensic Telemetry Summary:</strong> At 2026-08-26 23:15 UTC, {suspectName} passed within 0.8 km of the slick epicenter. The vessel's AIS log indicates a sudden drop in cruising speed from 14.2 knots to 6.1 knots lasting 42 minutes with a 25° heading deviation, coinciding with calculated discharge onset.
              </div>
            </div>
          )}
        </section>

        {/* Section 4a: Chain of Custody & Legal (fixture only) */}
        {isFixture && (
          <section className="space-y-4 pt-4 border-t border-outline-variant">
            <h3 className="text-title-lg font-bold text-primary flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-primary"></span>
              4. Chain of Custody &amp; Cryptographic Verification
            </h3>

            <div className="p-4 bg-surface-container-low rounded border border-outline-variant text-label-sm space-y-2">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between text-on-surface-variant">
                <span>Evidentiary Checksum (SHA-256):</span>
                <strong className="font-mono text-primary text-[11px] break-all">
                  e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
                </strong>
              </div>
              <div className="flex justify-between text-on-surface-variant">
                <span>Certified Digital Signature:</span>
                <strong className="text-secondary font-mono">VERIFIED • MEA-OFFICER-KEY-9841</strong>
              </div>
              <div className="flex justify-between text-on-surface-variant">
                <span>Legal Status:</span>
                <strong className="text-primary font-bold">Forwarded to Admiralty Court &amp; Port Authority</strong>
              </div>
            </div>

            {/* Signature Block */}
            <div className="grid grid-cols-2 gap-8 pt-6">
              <div className="border-t border-on-surface/40 pt-2 text-label-sm">
                <strong className="text-primary block">{displayInvestigator}</strong>
                <span className="text-on-surface-variant">Lead Maritime Environmental Investigator</span>
              </div>
              <div className="border-t border-on-surface/40 pt-2 text-label-sm text-right">
                <strong className="text-primary block">Adm. V. K. Menon</strong>
                <span className="text-on-surface-variant">Director General, Maritime Security Directorate</span>
              </div>
            </div>
          </section>
        )}

        {/* Section 4b: Observation Status & Next Steps (real SAR only) */}
        {isRealSAR && (
          <section className="space-y-4 pt-4 border-t border-outline-variant">
            <h3 className="text-title-lg font-bold text-primary flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-amber-500"></span>
              4. Observation Status &amp; Next Steps
            </h3>
            <div className="p-4 bg-surface-container-low rounded border border-outline-variant text-label-sm space-y-3 text-on-surface-variant leading-relaxed">
              <p>
                This dossier reflects the current state of the{' '}
                <strong>{sceneId || 'real SAR'}</strong> observation. The following steps are required
                to complete the investigation:
              </p>
              <ul className="list-disc list-inside space-y-1 pl-2">
                <li>Ingest historical AIS tracks for the Gulf of Mexico spill time window</li>
                <li>Run spatial/temporal vessel correlation against the detected slick epicenter</li>
                <li>Perform drift hindcast to estimate probable discharge origin time</li>
                <li>Conduct SAR look-alike discrimination to classify material type</li>
                <li>Complete chain-of-custody documentation after attribution is confirmed</li>
              </ul>
              <p className="text-[11px] italic">
                This report is an intermediate analytical output. It is not a legal attribution and must
                not be cited as evidence of vessel culpability until AIS correlation and independent
                material verification are complete.
              </p>
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
