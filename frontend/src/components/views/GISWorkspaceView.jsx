import React, { useState, useEffect } from 'react';
import { useNavigation } from '../../context/NavigationContext';
import api from '../../services/api';
import MaritimeMap from '../gis/MaritimeMap';
import LayerControls from '../gis/LayerControls';
import TemporalPlayback from '../gis/TemporalPlayback';
import TelemetrySidebar from '../gis/TelemetrySidebar';
import { vesselProfileMSC } from '../../services/mockData';

export default function GISWorkspaceView() {
  const { activeIncidentId, navigateTo } = useNavigation();
  const [incident, setIncident] = useState(null);
  const [candidateVessels, setCandidateVessels] = useState([]);
  const [cursorCoords, setCursorCoords] = useState(null);
  const [currentTimeIndex, setCurrentTimeIndex] = useState(3);
  const [activeLayers, setActiveLayers] = useState({
    sarSlicks: true,
    vesselTracks: true,
    eezBoundaries: true,
    shippingLanes: true
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadWorkspaceData() {
      try {
        const [inc, vessels] = await Promise.all([
          api.getIncident(activeIncidentId),
          api.getAttributedVessels(activeIncidentId)
        ]);
        setIncident(inc);
        setCandidateVessels(vessels);
      } catch (err) {
        console.error('Error loading GIS workspace data:', err);
      } finally {
        setLoading(false);
      }
    }
    loadWorkspaceData();
  }, [activeIncidentId]);

  const handleToggleLayer = (layerId) => {
    setActiveLayers(prev => ({
      ...prev,
      [layerId]: !prev[layerId]
    }));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-3 border-secondary border-t-transparent rounded-full animate-spin"></div>
          <span className="text-label-sm text-on-surface-variant font-semibold">
            Initializing Geospatial Map Engine & Satellite Overlays...
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-5 animate-in fade-in duration-150">
      {/* Top Breadcrumb & Status Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-surface-container-lowest border border-outline-variant p-4 rounded-lg">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded bg-primary-container text-on-primary flex items-center justify-center">
            <span className="material-symbols-outlined text-[20px]">map</span>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-headline-md text-primary font-bold tracking-tight text-[20px] whitespace-nowrap">
                Geospatial Forensics Workspace
              </h1>
              <span className="px-2 py-0.5 bg-error-container text-on-error-container font-mono text-[11px] font-bold rounded uppercase whitespace-nowrap shrink-0">
                {incident?.id || 'INC-2026-001'}
              </span>
            </div>
            <p className="text-label-sm text-on-surface-variant">
              Bay of Bengal Sector 4 • Satellite SAR Slick Polygon & AIS Back-Trajectory Analysis
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={() => navigateTo('attribution', { incidentId: incident?.id })}
            className="px-3.5 py-1.5 bg-secondary-container text-on-secondary-container border border-secondary/30 rounded text-label-sm font-bold hover:bg-secondary/20 transition-colors flex items-center gap-1.5 whitespace-nowrap shrink-0"
          >
            <span className="material-symbols-outlined text-[16px]">fingerprint</span>
            Attribution Matrix (94%)
          </button>
          <button
            onClick={() => navigateTo('dossier', { incidentId: incident?.id })}
            className="px-3.5 py-1.5 bg-primary-container text-on-primary rounded text-label-sm font-bold hover:bg-primary transition-colors flex items-center gap-1.5 whitespace-nowrap shrink-0"
          >
            <span className="material-symbols-outlined text-[16px]">folder_shared</span>
            Evidence Dossier
          </button>
        </div>
      </div>

      {/* Main Workspace: Left Map Canvas + Right Telemetry Sidebar */}
      <div className="flex flex-col lg:flex-row gap-5 min-h-[640px]">
        {/* Left Side: Map + Overlaid Controls */}
        <div className="flex-1 flex flex-col gap-4">
          {/* Leaflet Map Canvas */}
          <div className="flex-1 min-h-[500px] relative">
            <MaritimeMap
              incident={incident}
              candidateVessels={candidateVessels}
              activeLayers={activeLayers}
              currentTimeIndex={currentTimeIndex}
              onCursorMove={setCursorCoords}
              onSlickClick={() => alert(`Oil Slick INC-2026-001: 46.8 km² area, Bunker Fuel type, 94% detection confidence.`)}
              onVesselClick={(name) => navigateTo('vessel', { vesselName: name })}
            />

            {/* Floating Quick Layer Toggle */}
            <div className="absolute top-4 left-4 z-[400] max-w-xs hidden sm:block">
              <LayerControls
                activeLayers={activeLayers}
                onToggleLayer={handleToggleLayer}
              />
            </div>
          </div>

          {/* Bottom: Temporal Playback Slider */}
          <TemporalPlayback
            timelinePoints={candidateVessels?.[0]?.aisTrack || vesselProfileMSC.aisTrajectory}
            currentIndex={currentTimeIndex}
            onChangeIndex={setCurrentTimeIndex}
          />
        </div>

        {/* Right Side: Forensics & Suspect Telemetry Sidebar */}
        <TelemetrySidebar
          incident={incident}
          candidateVessels={candidateVessels}
          cursorCoords={cursorCoords}
          onNavigateAttribution={() => navigateTo('attribution', { incidentId: incident?.id })}
          onNavigateDossier={() => navigateTo('dossier', { incidentId: incident?.id })}
        />
      </div>
    </div>
  );
}
