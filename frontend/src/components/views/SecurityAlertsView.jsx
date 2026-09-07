import React, { useState, useEffect } from 'react';
import { useNavigation } from '../../context/NavigationContext';
import api from '../../services/api';
import StatusChip from '../common/StatusChip';
import Button from '../common/Button';

export default function SecurityAlertsView() {
  const { navigateTo, setUnreadAlertsCount } = useNavigation();
  const [alerts, setAlerts] = useState([]);
  const [filterSeverity, setFilterSeverity] = useState('ALL');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadAlerts() {
      try {
        const data = await api.getAlerts();
        setAlerts(data);
        const unread = data.filter(a => !a.acknowledged).length;
        setUnreadAlertsCount(unread);
      } catch (err) {
        console.error('Error loading alerts:', err);
      } finally {
        setLoading(false);
      }
    }
    loadAlerts();
  }, [setUnreadAlertsCount]);

  const handleAcknowledge = async (alertId) => {
    await api.acknowledgeAlert(alertId, 'Cmdr. R. Verma');
    setAlerts(prev => prev.map(a => {
      if (a.id === alertId) {
        return {
          ...a,
          acknowledged: true,
          acknowledgedBy: 'Cmdr. R. Verma (Just now)'
        };
      }
      return a;
    }));
    setUnreadAlertsCount(prev => Math.max(0, prev - 1));
  };

  const filteredAlerts = alerts.filter(a => {
    if (filterSeverity === 'ALL') return true;
    return a.severity.toUpperCase() === filterSeverity;
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-3 border-primary border-t-transparent rounded-full animate-spin"></div>
          <span className="text-label-sm text-on-surface-variant font-semibold">
            Connecting to Real-Time Satellite Anomaly Feed...
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 animate-in fade-in duration-150">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3 flex-wrap mb-1">
            <h1 className="text-headline-lg font-bold text-primary tracking-tight">
              Security &amp; Reconnaissance Alerts
            </h1>
            <span className="px-2 py-0.5 bg-amber-100 text-amber-800 border border-amber-300 text-[10px] font-bold uppercase tracking-wider rounded font-mono">
              FIXTURE DATA — AIS/SAR Real Integration Pending
            </span>
          </div>
          <p className="text-body-md text-on-surface-variant">
            Synthetic aperture radar detection events, AIS transponder dark events, and attribution updates. Alerts are seeded from fixture data while real SAR/AIS integration is pending.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            icon="done_all"
            onClick={() => {
              alerts.forEach(a => { if (!a.acknowledged) handleAcknowledge(a.id); });
            }}
          >
            Acknowledge All
          </Button>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 border-b border-outline-variant pb-2 overflow-x-auto">
        {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'INFO'].map((sev) => (
          <button
            key={sev}
            onClick={() => setFilterSeverity(sev)}
            className={`px-4 py-2 rounded text-label-sm font-bold transition-all ${
              filterSeverity === sev
                ? 'bg-primary text-on-primary shadow-xs'
                : 'bg-surface-container-low text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface'
            }`}
          >
            {sev === 'ALL' ? 'All Alerts' : sev} ({
              sev === 'ALL' ? alerts.length : alerts.filter(a => a.severity.toUpperCase() === sev).length
            })
          </button>
        ))}
      </div>

      {/* Alert Cards Feed */}
      <div className="flex flex-col gap-4">
        {filteredAlerts.length === 0 ? (
          <div className="p-12 text-center bg-surface-container-lowest border border-outline-variant rounded-lg text-on-surface-variant">
            <span className="material-symbols-outlined text-[36px] text-outline mb-2 block">notifications_off</span>
            No alerts matching current severity filter.
          </div>
        ) : (
          filteredAlerts.map((alert) => (
            <div
              key={alert.id}
              className={`p-5 bg-surface-container-lowest border rounded-lg shadow-xs flex flex-col md:flex-row items-start md:items-center justify-between gap-4 transition-all ${
                !alert.acknowledged
                  ? 'border-error/40 ring-1 ring-error/20 bg-error-container/5'
                  : 'border-outline-variant'
              }`}
            >
              <div className="space-y-1.5 flex-1">
                <div className="flex flex-wrap items-center gap-3">
                  <StatusChip status={alert.severity} size="sm" />
                  <span className="font-mono text-label-sm font-bold text-primary">{alert.id}</span>
                  {alert.incidentId && (
                    <span 
                      onClick={() => navigateTo('gis', { incidentId: alert.incidentId })}
                      className="text-[11px] font-mono font-bold bg-surface-container-high px-2 py-0.5 rounded text-primary hover:underline cursor-pointer"
                    >
                      {alert.incidentId}
                    </span>
                  )}
                  <span className="text-[12px] font-mono text-on-surface-variant">
                    {alert.timestamp}
                  </span>
                </div>

                <h3 className="text-title-lg font-bold text-primary">{alert.title}</h3>
                <p className="text-body-md text-on-surface-variant">{alert.description}</p>

                {alert.acknowledged && (
                  <div className="text-[12px] text-secondary font-semibold flex items-center gap-1 mt-1">
                    <span className="material-symbols-outlined text-[14px]">check_circle</span>
                    Acknowledged by {alert.acknowledgedBy}
                  </div>
                )}
              </div>

              <div className="flex items-center gap-2 shrink-0 w-full md:w-auto justify-end">
                {alert.incidentId && (
                  <Button
                    size="sm"
                    variant="teal"
                    icon="map"
                    onClick={() => navigateTo('gis', { incidentId: alert.incidentId })}
                  >
                    Forensics
                  </Button>
                )}
                {!alert.acknowledged ? (
                  <Button
                    size="sm"
                    variant="primary"
                    icon="check"
                    onClick={() => handleAcknowledge(alert.id)}
                  >
                    Acknowledge
                  </Button>
                ) : (
                  <span className="text-label-sm text-on-surface-variant font-semibold px-3 py-1">
                    Logged
                  </span>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
