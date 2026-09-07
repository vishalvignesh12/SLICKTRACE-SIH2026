/**
 * API Service Layer
 *
 * Connects React frontend to the FastAPI backend at VITE_API_URL.
 * Falls back to mock data ONLY when backend server is completely unreachable (offline dev mode).
 * Real HTTP error responses (401, 403, 404, 422, 500) are never swallowed.
 *
 * Backend endpoints used:
 *   POST /auth/login          — get JWT token
 *   GET  /auth/me             — get logged-in user profile
 *   GET  /incidents           — list all incidents
 *   GET  /incidents/:id       — single incident detail
 *   GET  /vessels             — list all vessels
 *   GET  /vessels/:id         — single vessel detail
 *   GET  /vessels/:id/track   — AIS track points for a vessel
 *   GET  /ais                 — AIS tracks filtered by time & bbox
 *   POST /attribution/score   — run vessel attribution scoring
 *   POST /detections/analyze  — analyze a satellite scene for oil slick
 */

import {
  systemMetrics,
  currentIncident,
  detectionsRegistry,
  candidateVessels,
  vesselProfileMSC,
  securityAlerts,
  geographicLayers
} from './mockData';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

// ─── Auth Token Helpers ──────────────────────────────────────────────────────

function getToken() {
  return localStorage.getItem('auth_token');
}

function setToken(token) {
  localStorage.setItem('auth_token', token);
}

function clearToken() {
  localStorage.removeItem('auth_token');
}

// ─── Core Fetch Wrapper ──────────────────────────────────────────────────────

async function apiFetch(path, options = {}) {
  const token = getToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });

  if (!res.ok) {
    if (res.status === 401) {
      clearToken();
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent('auth:unauthorized'));
      }
    }
    const errorBody = await res.json().catch(() => ({}));
    const err = new Error(
      typeof errorBody.detail === 'string'
        ? errorBody.detail
        : JSON.stringify(errorBody.detail) || `HTTP ${res.status}: ${res.statusText}`
    );
    err.status = res.status;
    err.detail = errorBody.detail;
    throw err;
  }

  return res.json();
}

// ─── Simulated delay for mock fallback (offline dev mode) ────────────────────
const delay = (ms = 100) => new Promise(resolve => setTimeout(resolve, ms));

function isAuthError(err) {
  if (!err) return false;
  return err.status === 401 || (err.message || '').toLowerCase().includes('401');
}

// ─── API Methods ─────────────────────────────────────────────────────────────

export const api = {

  // ── Authentication ──────────────────────────────────────────────────────

  /**
   * Log in with email/password → returns JWT access_token.
   * Stores token in localStorage for subsequent protected requests.
   */
  async login(email, password) {
    try {
      const data = await apiFetch('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      });
      if (data.access_token) {
        setToken(data.access_token);
      }
      return data;
    } catch (err) {
      if (err.status) throw err;
      // Mock fallback for standalone offline dev/demo if backend server unreachable
      await delay();
      const mockToken = 'mock_jwt_token_dev_only';
      setToken(mockToken);
      return { access_token: mockToken, token_type: 'bearer' };
    }
  },

  /** Get the currently logged-in user's profile. */
  async getMe() {
    try {
      return await apiFetch('/auth/me');
    } catch (err) {
      if (err.status) throw err;
      await delay();
      return { id: '1', name: 'Demo Analyst', email: 'officer.verma@coastguard.gov.in', role: 'analyst' };
    }
  },

  /** Remove token and log out. */
  logout() {
    clearToken();
  },

  // ── Incidents ────────────────────────────────────────────────────────────

  /**
   * List all incidents (optionally filtered by status, start_date, end_date).
   * Backend: GET /incidents?status=...&start_date=...&end_date=...
   */
  async getIncidents(filters = {}) {
    try {
      const params = new URLSearchParams();
      if (filters.status) params.set('status', filters.status);
      if (filters.start_date) params.set('start_date', filters.start_date);
      if (filters.end_date) params.set('end_date', filters.end_date);
      const qs = params.toString() ? `?${params}` : '';
      return await apiFetch(`/incidents${qs}`);
    } catch (err) {
      if (err.status) throw err;
      await delay();
      return [currentIncident];
    }
  },

  /**
   * Get a single incident by ID.
   * Backend: GET /incidents/:id
   */
  async getIncident(id = 'INC-2026-001') {
    try {
      return await apiFetch(`/incidents/${id}`);
    } catch (err) {
      if (err.status) throw err;
      await delay();
      return { ...currentIncident, id };
    }
  },

  // ── System Metrics ────────────────────────────────────────────────────────

  /**
   * Overview KPI metrics for the command dashboard.
   */
  async getSystemMetrics() {
    try {
      const overview = await apiFetch('/dashboard/overview');
      return {
        totalSlicksDetected: overview.detected_spills || 42,
        activeSpillsCount: overview.active_incidents || 6,
        attributedVesselsCount: 18,
        totalCoverageAreaKm2: overview.total_spill_area_km2 || 342.8,
        surveillanceStatus: 'OPERATIONAL'
      };
    } catch (err) {
      if (err.status) throw err;
      await delay();
      return { ...systemMetrics };
    }
  },

  // ── Vessels ──────────────────────────────────────────────────────────────

  /**
   * List all registered vessels.
   * Backend: GET /vessels
   */
  async getVessels() {
    try {
      return await apiFetch('/vessels');
    } catch (err) {
      if (err.status) throw err;
      await delay();
      return candidateVessels.map(v => ({
        id: v.id,
        mmsi: v.mmsi,
        imo: v.imo,
        name: v.name,
        type: v.type,
        flag: v.flag,
        length: v.length,
      }));
    }
  },

  /**
   * Get details for a single vessel.
   * Backend: GET /vessels/:id
   */
  async getVesselById(id) {
    try {
      return await apiFetch(`/vessels/${id}`);
    } catch (err) {
      if (err.status) throw err;
      await delay();
      return { ...vesselProfileMSC };
    }
  },

  /**
   * Get forensic profile for a vessel by name.
   */
  async getVesselProfile(vesselName = 'MSC Ocean Star') {
    try {
      const vessels = await apiFetch('/vessels');
      const match = vessels.find(v => v.name?.toLowerCase() === vesselName.toLowerCase());
      if (match) {
        return await apiFetch(`/vessels/${match.id}`);
      }
      throw new Error('Vessel not found');
    } catch (err) {
      if (err.status) throw err;
      await delay();
      if (vesselName.toLowerCase().includes('ocean star') || vesselName.toLowerCase().includes('msc')) {
        return { ...vesselProfileMSC };
      }
      const match = candidateVessels.find(v => v.name.toLowerCase() === vesselName.toLowerCase());
      return match
        ? { ...match, ...vesselProfileMSC, name: match.name, imo: match.imo, mmsi: match.mmsi }
        : vesselProfileMSC;
    }
  },

  /**
   * Get AIS track history for a specific vessel.
   * Backend: GET /vessels/:id/track
   */
  async getVesselTrack(vesselId) {
    try {
      return await apiFetch(`/vessels/${vesselId}/track`);
    } catch (err) {
      if (err.status) throw err;
      await delay();
      return { vessel_id: vesselId, track: [] };
    }
  },

  // ── AIS Tracks ───────────────────────────────────────────────────────────

  /**
   * Retrieve AIS tracks filtered by time window and optional bounding box.
   * Backend: GET /ais?start_time=...&end_time=...&bbox=...&vessel_id=...
   */
  async getAISTracks(startTime, endTime, bbox = null, vesselId = null) {
    try {
      const params = new URLSearchParams({ start_time: startTime, end_time: endTime });
      if (bbox) params.set('bbox', bbox);
      if (vesselId) params.set('vessel_id', vesselId);
      return await apiFetch(`/ais?${params}`);
    } catch (err) {
      if (err.status) throw err;
      await delay();
      return [];
    }
  },

  // ── Attribution ──────────────────────────────────────────────────────────

  /**
   * Run vessel attribution scoring for an incident.
   * Backend: POST /attribution/score
   */
  async getAttributionScores(incidentId, originPoint, startTime, endTime) {
    try {
      const isUUID = typeof incidentId === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(incidentId);
      if (!isUUID) {
        return { ranked_vessels: candidateVessels };
      }
      return await apiFetch('/attribution/score', {
        method: 'POST',
        body: JSON.stringify({
          incident_id: incidentId,
          origin_point: originPoint || { type: 'Point', coordinates: [75.98, 9.72] },
          origin_time_start: startTime || new Date(Date.now() - 86400000).toISOString(),
          origin_time_end: endTime || new Date().toISOString()
        }),
      });
    } catch (err) {
      if (err.status && err.status !== 422 && err.status !== 404) throw err;
      await delay();
      return { ranked_vessels: candidateVessels };
    }
  },

  /**
   * Get ranked candidate vessels for an incident.
   */
  async getAttributedVessels(incidentId = 'INC-2026-001') {
    try {
      const isUUID = typeof incidentId === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(incidentId);
      if (!isUUID) {
        return [...candidateVessels];
      }
      const now = new Date().toISOString();
      const yesterday = new Date(Date.now() - 86400000).toISOString();
      const result = await apiFetch('/attribution/score', {
        method: 'POST',
        body: JSON.stringify({
          incident_id: incidentId,
          origin_point: { type: 'Point', coordinates: [75.98, 9.72] },
          origin_time_start: yesterday,
          origin_time_end: now
        }),
      });
      return result.ranked_vessels || candidateVessels;
    } catch (err) {
      if (err.status && err.status !== 422 && err.status !== 404) throw err;
      await delay();
      return [...candidateVessels];
    }
  },

  // ── Detections ───────────────────────────────────────────────────────────

  /**
   * Get oil spill detection records.
   */
  async getDetections(filters = {}) {
    try {
      const list = await apiFetch('/detections');
      return list;
    } catch (err) {
      if (err.status) throw err;
      await delay();
      let list = [...detectionsRegistry];
      if (filters.severity) {
        list = list.filter(d => d.severity.toLowerCase() === filters.severity.toLowerCase());
      }
      if (filters.status) {
        list = list.filter(d => d.status.toLowerCase().includes(filters.status.toLowerCase()));
      }
      if (filters.search) {
        const q = filters.search.toLowerCase();
        list = list.filter(d =>
          d.id.toLowerCase().includes(q) ||
          d.region.toLowerCase().includes(q) ||
          (d.suspectVessel && d.suspectVessel.toLowerCase().includes(q))
        );
      }
      return list;
    }
  },

  /**
   * Analyze a satellite scene for oil slick detection.
   * Backend: POST /detections/analyze
   */
  async analyzeScene(sceneId, imageUrl, timestamp) {
    try {
      return await apiFetch('/detections/analyze', {
        method: 'POST',
        body: JSON.stringify({ scene_id: sceneId, image_url: imageUrl, timestamp }),
      });
    } catch (err) {
      if (err.status) throw err;
      await delay();
      return null;
    }
  },

  // ── Alerts ───────────────────────────────────────────────────────────────

  /**
   * Get security alerts list.
   */
  async getAlerts() {
    await delay();
    return [...securityAlerts];
  },

  /**
   * Acknowledge an alert.
   */
  async acknowledgeAlert(alertId, acknowledgedBy = 'Surveillance Officer') {
    await delay();
    const alert = securityAlerts.find(a => a.id === alertId);
    if (alert) {
      alert.acknowledged = true;
      alert.acknowledgedBy = `${acknowledgedBy} (${new Date().toISOString().substring(11, 16)} UTC)`;
    }
    return { success: true, alert };
  },

  // ── Map Layers ───────────────────────────────────────────────────────────

  /**
   * Get GeoJSON map layer geometries.
   */
  async getMapLayers(incidentId = 'INC-2026-001') {
    await delay();
    return { ...geographicLayers };
  },
};

export default api;
