import React from 'react';
import { NavigationProvider, useNavigation } from './context/NavigationContext';
import SideNavBar from './components/common/SideNavBar';
import Header from './components/common/Header';
import LoginView from './components/views/LoginView';
import DashboardView from './components/views/DashboardView';
import DetectionRegistryView from './components/views/DetectionRegistryView';
import GISWorkspaceView from './components/views/GISWorkspaceView';
import AttributionView from './components/views/AttributionView';
import VesselProfileView from './components/views/VesselProfileView';
import EvidenceDossierView from './components/views/EvidenceDossierView';
import SecurityAlertsView from './components/views/SecurityAlertsView';
import SystemReportsView from './components/views/SystemReportsView';
import SettingsView from './components/views/SettingsView';

// View Router
function ActiveViewRenderer() {
  const { activeScreen, isAuthenticated, authLoading } = useNavigation();

  // 1. Initial auth verification loading state (prevents auth flashes / race conditions)
  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-surface text-on-surface">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
          <span className="text-label-md text-on-surface-variant font-semibold">
            Verifying Operational Terminal Credentials...
          </span>
        </div>
      </div>
    );
  }

  // 2. Unauthenticated or explicit login screen -> render standalone login view
  if (!isAuthenticated || activeScreen === 'login') {
    return <LoginView />;
  }

  // 3. Authenticated operational shell
  const renderCurrentView = () => {
    switch (activeScreen) {
      case 'dashboard':
        return <DashboardView />;
      case 'detection':
        return <DetectionRegistryView />;
      case 'gis':
        return <GISWorkspaceView />;
      case 'attribution':
        return <AttributionView />;
      case 'vessel':
        return <VesselProfileView />;
      case 'dossier':
        return <EvidenceDossierView />;
      case 'alerts':
        return <SecurityAlertsView />;
      case 'reports':
        return <SystemReportsView />;
      case 'settings':
        return <SettingsView />;
      default:
        return <DashboardView />;
    }
  };

  return (
    <div className="flex bg-surface min-h-screen text-on-surface">
      {/* Fixed Left Navigation Sidebar */}
      <SideNavBar />

      {/* Main Content Area */}
      <div className="ml-[260px] flex-1 flex flex-col min-h-screen min-w-0 overflow-x-hidden">
        <Header />

        <main className="flex-1 p-6 md:p-8 overflow-y-auto max-w-[1500px] w-full mx-auto min-w-0">
          {renderCurrentView()}
        </main>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <NavigationProvider>
      <ActiveViewRenderer />
    </NavigationProvider>
  );
}
