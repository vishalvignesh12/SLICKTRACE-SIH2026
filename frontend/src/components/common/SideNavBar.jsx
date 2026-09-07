import React from 'react';
import { useNavigation } from '../../context/NavigationContext';

/**
 * SideNavBar Component
 * Persistent 260px fixed sidebar with logo, active indicator, icons, and status
 */
export default function SideNavBar() {
  const { activeScreen, navigateTo, handleLogout, unreadAlertsCount } = useNavigation();

  const navItems = [
    { id: 'dashboard', label: 'Command Dashboard', icon: 'dashboard' },
    { id: 'detection', label: 'Detection Registry', icon: 'radar' },
    { id: 'gis', label: 'Investigation Map', icon: 'map' },
    { id: 'attribution', label: 'Vessel Attribution', icon: 'fingerprint' },
    { id: 'vessel', label: 'Vessel Details', icon: 'directions_boat' },
    { id: 'dossier', label: 'Evidence Dossier', icon: 'folder_shared' },
    { id: 'alerts', label: 'Security Alerts', icon: 'notifications_active', badge: unreadAlertsCount },
    { id: 'reports', label: 'System Reports', icon: 'description' }
  ];

  return (
    <nav className="w-[260px] h-screen fixed left-0 top-0 bg-surface-container-low border-r border-outline-variant flex flex-col py-6 px-4 z-40 select-none">
      {/* Brand Header */}
      <div 
        onClick={() => navigateTo('dashboard')}
        className="mb-6 px-2 flex items-center gap-3 cursor-pointer group"
      >
        <div className="w-10 h-10 bg-primary-container rounded flex items-center justify-center text-on-primary text-xl font-bold font-sans shadow-sm group-hover:bg-primary transition-colors">
          M
        </div>
        <div>
          <h1 className="text-headline-md text-primary font-bold tracking-tight text-[18px] leading-tight">
            Maritime Intel
          </h1>
          <p className="text-[10px] text-on-surface-variant uppercase tracking-widest font-semibold mt-0.5">
            National Security
          </p>
        </div>
      </div>

      {/* Navigation List */}
      <ul className="flex flex-col gap-1 flex-1 overflow-y-auto pr-1">
        {navItems.map((item) => {
          const isActive = activeScreen === item.id;
          return (
            <li key={item.id}>
              <button
                onClick={() => navigateTo(item.id)}
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded text-label-md transition-all duration-150 ${
                  isActive
                    ? 'text-primary font-bold border-r-4 border-primary bg-surface-container-high shadow-xs'
                    : 'text-on-surface-variant hover:bg-surface-container-highest hover:text-on-surface font-medium'
                }`}
              >
                <div className="flex items-center gap-3">
                  <span
                    className="material-symbols-outlined text-[20px]"
                    style={isActive ? { fontVariationSettings: "'FILL' 1" } : {}}
                  >
                    {item.icon}
                  </span>
                  <span>{item.label}</span>
                </div>
                {item.badge && item.badge > 0 ? (
                  <span className="px-1.5 py-0.5 rounded-full bg-error text-on-error text-[10px] font-bold">
                    {item.badge}
                  </span>
                ) : null}
              </button>
            </li>
          );
        })}

        <div className="my-3 border-t border-outline-variant/60 mx-2"></div>

        <li>
          <button
            onClick={() => navigateTo('settings')}
            className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded text-label-md transition-all ${
              activeScreen === 'settings'
                ? 'text-primary font-bold border-r-4 border-primary bg-surface-container-high'
                : 'text-on-surface-variant hover:bg-surface-container-highest hover:text-on-surface font-medium'
            }`}
          >
            <span className="material-symbols-outlined text-[20px]">settings</span>
            <span>Settings</span>
          </button>
        </li>
      </ul>

      {/* Secure Session Footer */}
      <div className="mt-auto pt-4 border-t border-outline-variant/80">
        <div className="p-2.5 bg-surface-container rounded border border-outline-variant/60 mb-2">
          <div className="flex items-center justify-between text-[11px] text-on-surface-variant font-semibold">
            <span>SURVEILLANCE MATRIX</span>
            <span className="text-secondary flex items-center gap-1 font-bold">
              <span className="w-1.5 h-1.5 rounded-full bg-secondary animate-pulse"></span>
              ONLINE
            </span>
          </div>
        </div>

        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-3 px-3 py-2 rounded text-on-surface-variant hover:bg-error-container/40 hover:text-error transition-colors text-label-sm font-semibold"
        >
          <span className="material-symbols-outlined text-secondary text-[18px]">lock_person</span>
          <span>Secure Sign Out</span>
        </button>
      </div>
    </nav>
  );
}
