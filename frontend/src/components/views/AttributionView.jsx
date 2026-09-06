import React, { useState, useEffect } from 'react';
import { useNavigation } from '../../context/NavigationContext';
import api from '../../services/api';
import CandidateCard from '../attribution/CandidateCard';
import FactorBreakdown from '../attribution/FactorBreakdown';
import Button from '../common/Button';
import StatusChip from '../common/StatusChip';

export default function AttributionView() {
  const { activeIncidentId, navigateTo, setSelectedVesselName } = useNavigation();
  const [incident, setIncident] = useState(null);
  const [candidates, setCandidates] = useState([]);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [inc, vessels] = await Promise.all([
          api.getIncident(activeIncidentId),
          api.getAttributedVessels(activeIncidentId)
        ]);
        setIncident(inc);
        setCandidates(vessels);
      } catch (err) {
        console.error('Error loading attribution data:', err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [activeIncidentId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-3 border-primary border-t-transparent rounded-full animate-spin"></div>
          <span className="text-label-sm text-on-surface-variant font-semibold">
            Computing Spatial-Temporal Trajectory Attributions...
          </span>
        </div>
      </div>
    );
  }

  const selectedVessel = candidates[selectedIndex] || candidates[0];

  return (
    <div className="flex flex-col gap-6 animate-in fade-in duration-150">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-headline-lg font-bold text-primary tracking-tight whitespace-nowrap">
              Probabilistic Vessel Attribution Matrix
            </h1>
            <span className="font-mono bg-error-container text-on-error-container text-label-sm font-bold px-2 py-0.5 rounded uppercase whitespace-nowrap shrink-0">
              {incident?.id || 'INC-2026-001'}
            </span>
          </div>
          <p className="text-body-md text-on-surface-variant">
            Automated spatial-temporal back-trajectory matching against AIS transponder trajectories during calculated spill window.
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <Button
            variant="teal"
            icon="map"
            onClick={() => navigateTo('gis', { incidentId: incident?.id })}
          >
            Inspect on GIS Map
          </Button>
          <Button
            variant="primary"
            icon="folder_shared"
            onClick={() => navigateTo('dossier', { incidentId: incident?.id })}
          >
            Evidence Dossier
          </Button>
        </div>
      </div>

      {/* Primary Suspect Hero Banner */}
      {candidates.length > 0 && (
        <div className="bg-primary text-on-primary rounded-lg p-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-6 shadow-md relative overflow-hidden">
          <div className="absolute right-0 top-0 bottom-0 w-1/3 map-layer opacity-20 pointer-events-none"></div>

          <div className="space-y-2 z-10">
            <div className="flex items-center gap-3 flex-wrap">
              <span className="px-3 py-1 bg-error text-on-error text-label-sm font-bold uppercase tracking-wider rounded whitespace-nowrap shrink-0">
                Rank #1 Primary Offender Suspect
              </span>
              <span className="text-secondary-fixed text-label-sm font-bold flex items-center gap-1 whitespace-nowrap shrink-0">
                <span className="material-symbols-outlined text-[16px]">verified</span>
                {candidates[0].confidence != null ? `${candidates[0].confidence}%` : '—'} Attribution Confidence
              </span>
              <span className="px-2 py-0.5 bg-amber-200 text-amber-900 border border-amber-400 text-[10px] font-bold uppercase tracking-wider rounded font-mono shrink-0">
                AIS: Fixture Adapter • Drift: Fixture Adapter
              </span>
            </div>

            <h2 className="text-headline-lg font-bold text-on-primary text-[28px]">
              {candidates[0].name} ({candidates[0].flag})
            </h2>

            <p className="text-body-md text-on-primary/80 max-w-2xl">
              Spatial distance at discharge onset: <strong>0.8 km</strong>. Recorded significant course yaw (+25°) and deceleration from 14.2 to 6.1 knots during active plume generation window.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row gap-3 z-10 shrink-0">
            <Button
              variant="teal"
              icon="directions_boat"
              onClick={() => {
                setSelectedVesselName(candidates[0].name);
                navigateTo('vessel', { vesselName: candidates[0].name });
              }}
            >
              Open Full Forensic Profile
            </Button>
          </div>
        </div>
      )}

      {/* Two Column Layout: Factor Breakdown + Candidate List */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Detailed Multi-Factor Visualizer (5 cols) */}
        <div className="lg:col-span-5">
          <FactorBreakdown vessel={selectedVessel} />
        </div>

        {/* Right: Candidate Vessels Ranking List (7 cols) */}
        <div className="lg:col-span-7 flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h3 className="text-title-lg font-bold text-primary">
              Corridor Candidate Vessels ({candidates.length} Scanned)
            </h3>
            <span className="text-label-sm text-on-surface-variant">
              Click candidate to inspect factor weights
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {candidates.map((vessel, idx) => (
              <CandidateCard
                key={vessel.imo || idx}
                vessel={vessel}
                isSelected={selectedIndex === idx}
                onSelect={() => setSelectedIndex(idx)}
                onInspectProfile={(name) => {
                  setSelectedVesselName(name);
                  navigateTo('vessel', { vesselName: name });
                }}
                onViewGIS={() => navigateTo('gis', { incidentId: incident?.id })}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
