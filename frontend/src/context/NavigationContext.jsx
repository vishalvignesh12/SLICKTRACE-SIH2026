import React, { createContext, useContext, useState, useEffect } from 'react';
import api from '../services/api';

const NavigationContext = createContext();

export function NavigationProvider({ children }) {
  // Screens: 'dashboard' | 'detection' | 'gis' | 'attribution' | 'vessel' | 'dossier' | 'alerts' | 'reports' | 'settings' | 'login'
  const [activeScreen, setActiveScreen] = useState(() => sessionStorage.getItem('active_screen') || 'login');
  const [activeIncidentId, setActiveIncidentId] = useState(() => sessionStorage.getItem('active_incident_id') || 'INC-2026-001');
  const [selectedVesselName, setSelectedVesselName] = useState(() => sessionStorage.getItem('selected_vessel_name') || 'MSC Ocean Star');
  const [searchQuery, setSearchQuery] = useState('');
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [unreadAlertsCount, setUnreadAlertsCount] = useState(2);

  useEffect(() => {
    let isMounted = true;

    async function initAuth() {
      const token = localStorage.getItem('auth_token');
      if (!token) {
        if (isMounted) {
          setIsAuthenticated(false);
          setUser(null);
          setActiveScreen('login');
          sessionStorage.removeItem('active_screen');
          setAuthLoading(false);
        }
        return;
      }

      try {
        const me = await api.getMe();
        if (isMounted) {
          setUser(me);
          setIsAuthenticated(true);
          const savedScreen = sessionStorage.getItem('active_screen');
          setActiveScreen(savedScreen && savedScreen !== 'login' ? savedScreen : 'dashboard');
        }
      } catch (err) {
        console.warn('Persisted auth token validation failed:', err);
        api.logout();
        if (isMounted) {
          setUser(null);
          setIsAuthenticated(false);
          setActiveScreen('login');
          sessionStorage.removeItem('active_screen');
        }
      } finally {
        if (isMounted) {
          setAuthLoading(false);
        }
      }
    }

    initAuth();

    const handleUnauthorized = () => {
      api.logout();
      if (isMounted) {
        setUser(null);
        setIsAuthenticated(false);
        setActiveScreen('login');
        sessionStorage.removeItem('active_screen');
      }
    };

    window.addEventListener('auth:unauthorized', handleUnauthorized);
    return () => {
      isMounted = false;
      window.removeEventListener('auth:unauthorized', handleUnauthorized);
    };
  }, []);

  const navigateTo = (screen, params = {}) => {
    if (params.incidentId) {
      setActiveIncidentId(params.incidentId);
      sessionStorage.setItem('active_incident_id', params.incidentId);
    }
    if (params.vesselName) {
      setSelectedVesselName(params.vesselName);
      sessionStorage.setItem('selected_vessel_name', params.vesselName);
    }
    setActiveScreen(screen);
    sessionStorage.setItem('active_screen', screen);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleLogout = () => {
    api.logout();
    setUser(null);
    setIsAuthenticated(false);
    setActiveScreen('login');
    sessionStorage.removeItem('active_screen');
    sessionStorage.removeItem('active_incident_id');
    sessionStorage.removeItem('selected_vessel_name');
  };

  return (
    <NavigationContext.Provider
      value={{
        activeScreen,
        setActiveScreen,
        activeIncidentId,
        setActiveIncidentId,
        selectedVesselName,
        setSelectedVesselName,
        searchQuery,
        setSearchQuery,
        isAuthenticated,
        setIsAuthenticated,
        user,
        setUser,
        authLoading,
        unreadAlertsCount,
        setUnreadAlertsCount,
        navigateTo,
        handleLogout
      }}
    >
      {children}
    </NavigationContext.Provider>
  );
}

export function useNavigation() {
  const context = useContext(NavigationContext);
  if (!context) {
    throw new Error('useNavigation must be used within a NavigationProvider');
  }
  return context;
}
