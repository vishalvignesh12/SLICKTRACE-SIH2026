import React from 'react';
import { useNavigation } from '../../context/NavigationContext';

/**
 * Header Component
 * Top app bar with contextual view tags, search, notifications, and officer profile
 */
export default function Header() {
  const { 
    activeIncidentId, 
    activeIncident,
    activeScreen, 
    navigateTo, 
    unreadAlertsCount,
    searchQuery,
    setSearchQuery 
  } = useNavigation();

  const isIncidentView = ['gis', 'attribution', 'vessel', 'dossier'].includes(activeScreen);

  const renderContextBadges = () => {
    if (activeScreen === 'detection') {
      return (
        <div className="hidden sm:flex items-center gap-2 pl-4 border-l border-outline-variant shrink-0">
          <span className="text-[11px] leading-none bg-surface-container-high text-primary px-2.5 py-1.5 rounded font-bold uppercase tracking-wider border border-outline-variant whitespace-nowrap shrink-0">
            Detection Registry
          </span>
          <span className="text-[12px] text-on-surface-variant flex items-center gap-1.5 whitespace-nowrap shrink-0 font-medium">
            <span className="w-2 h-2 rounded-full bg-secondary animate-pulse shrink-0"></span>
            6 Active Slicks
          </span>
        </div>
      );
    }

    if (activeScreen === 'dashboard') {
      return (
        <div className="hidden sm:flex items-center gap-2 pl-4 border-l border-outline-variant shrink-0">
          <span className="text-[11px] leading-none bg-primary text-on-primary px-2.5 py-1.5 rounded font-bold uppercase tracking-wider whitespace-nowrap shrink-0">
            Sector 4 Surveillance
          </span>
          <span className="text-[12px] text-secondary flex items-center gap-1.5 whitespace-nowrap shrink-0 font-bold">
            <span className="w-2 h-2 rounded-full bg-secondary animate-pulse shrink-0"></span>
            Matrix Live
          </span>
        </div>
      );
    }

    if (isIncidentView) {
      const isUUID = typeof activeIncidentId === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(activeIncidentId);
      const isRealSAR = Boolean(
        activeIncident?.source_scene_id?.startsWith('REAL-SAR') ||
        (activeIncident?.coordinates?.lng < 0 && Math.abs(activeIncident?.coordinates?.lng) > 80) ||
        (isUUID && activeIncidentId !== 'INC-2026-001')
      );

      const zoneDisplay = activeIncident?.zone || (isRealSAR ? 'Gulf of Mexico (Real SAR)' : 'Bay of Bengal');
      let confidenceVal = isRealSAR ? '99.98' : '94';
      if (activeIncident?.confidence != null) {
        const conf = activeIncident.confidence;
        if (typeof conf === 'number') {
          const scaled = conf > 1 ? conf : conf * 100;
          confidenceVal = (scaled >= 99.9 && scaled < 100) ? scaled.toFixed(2) : (scaled % 1 === 0 ? String(scaled) : scaled.toFixed(1));
        } else {
          confidenceVal = String(conf);
        }
      }
      const confidenceDisplay = `${confidenceVal}% Confidence`;

      return (
        <div className="hidden sm:flex items-center gap-2.5 pl-4 border-l border-outline-variant shrink-0 whitespace-nowrap">
          <span 
            onClick={() => navigateTo('dossier', { incidentId: activeIncidentId })}
            className="cursor-pointer text-[11px] leading-none bg-error-container text-on-error-container px-2.5 py-1.5 rounded font-bold uppercase tracking-wider hover:opacity-90 transition-opacity whitespace-nowrap shrink-0 inline-flex items-center"
            title="Jump to Incident Dossier"
          >
            {activeIncident?.id || activeIncidentId}
          </span>
          <span className="text-[13px] text-on-surface-variant flex items-center gap-1 whitespace-nowrap shrink-0 font-medium">
            <span className="material-symbols-outlined text-[16px] text-secondary">location_on</span>
            {zoneDisplay}
          </span>
          <span className="text-[12px] leading-none bg-secondary-container text-on-secondary-container px-2.5 py-1.5 rounded border border-secondary/20 flex items-center gap-1.5 font-semibold whitespace-nowrap shrink-0 inline-flex">
            <span className="w-2 h-2 rounded-full bg-secondary animate-pulse shrink-0"></span>
            {confidenceDisplay}
          </span>
        </div>
      );
    }

    if (activeScreen === 'alerts') {
      return (
        <div className="hidden sm:flex items-center gap-2 pl-4 border-l border-outline-variant shrink-0">
          <span className="text-[11px] leading-none bg-error-container text-on-error-container px-2.5 py-1.5 rounded font-bold uppercase tracking-wider whitespace-nowrap shrink-0">
            Anomaly Stream
          </span>
        </div>
      );
    }

    if (activeScreen === 'reports') {
      return (
        <div className="hidden sm:flex items-center gap-2 pl-4 border-l border-outline-variant shrink-0">
          <span className="text-[11px] leading-none bg-surface-container-high text-primary px-2.5 py-1.5 rounded font-bold uppercase tracking-wider border border-outline-variant whitespace-nowrap shrink-0">
            Briefing Dispatcher
          </span>
        </div>
      );
    }

    if (activeScreen === 'settings') {
      return (
        <div className="hidden sm:flex items-center gap-2 pl-4 border-l border-outline-variant shrink-0">
          <span className="text-[11px] leading-none bg-surface-container-high text-primary px-2.5 py-1.5 rounded font-bold uppercase tracking-wider border border-outline-variant whitespace-nowrap shrink-0">
            Terminal Configuration
          </span>
        </div>
      );
    }

    return null;
  };

  return (
    <header className="h-16 bg-surface-container-lowest border-b border-outline-variant flex justify-between items-center px-6 z-30 shrink-0 sticky top-0">
      {/* Left: View Brand & Dynamic Screen Context */}
      <div className="flex items-center gap-4 shrink-0 min-w-0">
        <h2 
          onClick={() => navigateTo('dashboard')}
          className="text-title-lg text-primary font-bold tracking-tight whitespace-nowrap shrink-0 cursor-pointer hover:opacity-80 transition-opacity"
        >
          Maritime Intel
        </h2>

        {renderContextBadges()}
      </div>

      {/* Right: Search, Alerts Badge, GIS shortcut, and Officer Avatar */}
      <div className="flex items-center gap-3 shrink-0">
        {/* Quick Search */}
        <div className="relative hidden lg:block w-44 xl:w-60 shrink-0">
          <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-[18px]">
            search
          </span>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search registry..."
            className="w-full pl-9 pr-4 py-1.5 bg-surface-container-low border border-outline-variant rounded text-label-md text-on-surface focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all placeholder:text-outline text-[13px]"
          />
        </div>

        {/* Alerts Button */}
        <button
          onClick={() => navigateTo('alerts')}
          className="relative w-9 h-9 rounded flex items-center justify-center text-on-surface-variant hover:bg-surface-container-high transition-colors shrink-0"
          title="Security Alerts"
        >
          <span className="material-symbols-outlined text-[20px]">notifications</span>
          {unreadAlertsCount > 0 && (
            <span className="absolute top-1.5 right-1.5 w-2.5 h-2.5 bg-error rounded-full ring-2 ring-surface-container-lowest animate-pulse"></span>
          )}
        </button>

        {/* GIS Forensics Quick Jump */}
        <button
          onClick={() => navigateTo('gis')}
          className={`w-9 h-9 rounded flex items-center justify-center transition-colors shrink-0 ${
            activeScreen === 'gis' ? 'bg-primary-container text-on-primary' : 'text-on-surface-variant hover:bg-surface-container-high'
          }`}
          title="GIS Map Workspace"
        >
          <span className="material-symbols-outlined text-[20px]">map</span>
        </button>

        {/* User / Officer Profile */}
        <div 
          onClick={() => navigateTo('settings')}
          className="flex items-center gap-2.5 pl-3 border-l border-outline-variant cursor-pointer hover:opacity-80 transition-opacity shrink-0"
          title="Officer Settings"
        >
          <div className="w-8 h-8 rounded-full bg-primary-container text-on-primary flex items-center justify-center font-bold text-label-sm shrink-0">
            RV
          </div>
          <div className="hidden xl:block text-left whitespace-nowrap">
            <div className="text-label-sm font-bold text-primary leading-tight">Cmdr. R. Verma</div>
            <div className="text-[11px] text-on-surface-variant leading-tight">Surveillance Command</div>
          </div>
        </div>
      </div>
    </header>
  );
}
