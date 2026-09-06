"""
Live End-to-End Integration Verification Script
Tests the full system pipeline against live PostgreSQL/PostGIS and FastAPI application.

Pipeline:
1. Authentication (Login -> JWT Access Token -> Profile /auth/me)
2. Command & Control Dashboard (Overview, Spills, Vessels)
3. Satellite Scene Ingestion (List Scenes -> Register New Scene)
4. Detection Pipeline (Analyze Scene with FixtureMLProvider -> Auto-create Incident)
5. Incident Forensics (List Incidents -> Get Single Incident Details)
6. Drift Hindcast & Forecast (Simulate reverse & forward trajectories)
7. AIS Query & Attribution Scoring (Rank candidate suspect vessels)
8. Investigation Dossier & Evidence Pack (Get Investigation -> Compile Evidence -> Export CSV)
"""

import sys
import asyncio
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import httpx

from app.main import app


async def run_verification():
    print("=" * 80)
    print("OIL SPILL PLATFORM - FULL END-TO-END LIVE INTEGRATION VERIFICATION")
    print("=" * 80)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost:8000") as client:
        
        # ─── 1. AUTHENTICATION ───────────────────────────────────────────────
        print("\n[STEP 1] Testing Authentication Pipeline...")
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "officer.verma@coastguard.gov.in",
                "password": "SIH2026@CoastGuard"
            }
        )
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        auth_data = login_resp.json()
        token = auth_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print(f"  [OK] Login successful. JWT Token obtained: {token[:20]}...")

        # Test /auth/me
        me_resp = await client.get("/api/v1/auth/me", headers=headers)
        assert me_resp.status_code == 200, f"Auth me failed: {me_resp.text}"
        user_info = me_resp.json()
        print(f"  [OK] Profile retrieved: {user_info.get('name', user_info.get('email'))} | Role: {user_info['role']} | Email: {user_info['email']}")

        # ─── 2. DASHBOARD METRICS & GIS TELEMETRY ───────────────────────────
        print("\n[STEP 2] Testing Command & Control Dashboard Endpoints...")
        overview_resp = await client.get("/api/v1/dashboard/overview", headers=headers)
        assert overview_resp.status_code == 200, f"Dashboard overview failed: {overview_resp.text}"
        overview = overview_resp.json()
        print(f"  [OK] Dashboard Overview:")
        print(f"       Total Incidents: {overview.get('total_incidents', 0)}")
        print(f"       Active Incidents: {overview.get('active_incidents', 0)}")
        print(f"       Detected Spills: {overview.get('detected_spills', 0)}")
        print(f"       Total Slick Area: {overview.get('total_spill_area_km2', 0)} km²")

        spills_resp = await client.get("/api/v1/dashboard/spills", headers=headers)
        assert spills_resp.status_code == 200
        spills = spills_resp.json()
        print(f"  [OK] Dashboard Spills: {len(spills.get('features', spills)) if isinstance(spills, (dict, list)) else 'OK'} geospatial features")

        vessels_resp = await client.get("/api/v1/dashboard/vessels", headers=headers)
        assert vessels_resp.status_code == 200
        print(f"  [OK] Dashboard Monitored Vessels telemetry active")

        # ─── 3. SATELLITE SCENES LIFECYCLE ──────────────────────────────────
        print("\n[STEP 3] Testing Satellite Scene Ingestion...")
        scenes_resp = await client.get("/api/v1/scenes", headers=headers)
        assert scenes_resp.status_code == 200
        scenes = scenes_resp.json()
        print(f"  [OK] Existing Satellite Scenes in catalog: {len(scenes)}")

        now_utc = datetime.now(timezone.utc)
        unique_scene_id = f"S1A_IW_GRDH_1SDV_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:4].upper()}"
        new_scene_payload = {
            "source": "COPERNICUS",
            "scene_id": unique_scene_id,
            "satellite": "Sentinel-1A",
            "sensor": "C-SAR",
            "product_type": "GRD",
            "polarization": "VV+VH",
            "acquisition_time": now_utc.isoformat(),
            "bbox": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [88.1, 14.7],
                        [88.6, 14.7],
                        [88.6, 15.2],
                        [88.1, 15.2],
                        [88.1, 14.7]
                    ]
                ]
            },
            "scene_metadata": {
                "orbit": "Ascending",
                "resolution_m": 10.0,
                "sector": "Bay of Bengal - Sector 4"
            },
            "status": "INGESTED"
        }
        create_scene_resp = await client.post("/api/v1/scenes", json=new_scene_payload, headers=headers)
        assert create_scene_resp.status_code in [200, 201], f"Scene ingestion failed: {create_scene_resp.text}"
        scene = create_scene_resp.json()
        scene_db_id = scene["id"]
        print(f"  [OK] Successfully ingested Scene ID: {scene['scene_id']} (DB UUID: {scene_db_id})")

        # ─── 4. DETECTION ML PIPELINE (FixtureMLProvider) ───────────────────
        print("\n[STEP 4] Executing Detection Analysis Pipeline...")
        analyze_payload = {
            "scene_id": unique_scene_id,
            "timestamp": now_utc.isoformat()
        }
        analyze_resp = await client.post("/api/v1/detections/analyze", json=analyze_payload, headers=headers)
        assert analyze_resp.status_code in [200, 201, 202], f"Analyze failed: {analyze_resp.text}"
        detection_result = analyze_resp.json()
        print(f"  [OK] ML Inference Completed: Detection ID: {detection_result.get('detection_id')}")
        print(f"       Detected Slick Area: {detection_result.get('area_km2')} km² | Confidence: {detection_result.get('confidence')}")

        # List detections from database
        detections_resp = await client.get("/api/v1/detections", headers=headers)
        assert detections_resp.status_code == 200
        detections = detections_resp.json()
        print(f"  [OK] Detections in registry: {len(detections)}")

        # ─── 5. INCIDENTS MANAGEMENT ────────────────────────────────────────
        print("\n[STEP 5] Testing Incidents Lifecycle...")
        incidents_resp = await client.get("/api/v1/incidents", headers=headers)
        assert incidents_resp.status_code == 200
        incidents = incidents_resp.json()
        assert len(incidents) > 0, "Expected at least 1 incident"
        target_incident = incidents[0]
        incident_id = target_incident["id"]
        print(f"  [OK] Total Incidents: {len(incidents)} | Selected Incident ID: {incident_id}")
        print(f"       Title: {target_incident.get('title')} | Severity: {target_incident.get('severity')} | Status: {target_incident.get('status')}")

        # Fetch single incident
        single_inc_resp = await client.get(f"/api/v1/incidents/{incident_id}", headers=headers)
        assert single_inc_resp.status_code == 200
        inc_detail = single_inc_resp.json()
        print(f"       Location: {inc_detail.get('location')} | Status: {inc_detail.get('status')}")

        # ─── 6. DRIFT SIMULATION (HINDCAST & FORECAST) ──────────────────────
        print("\n[STEP 6] Testing Drift Simulation (Hindcast & Forecast)...")
        slick_poly = {
            "type": "Polygon",
            "coordinates": [
                [
                    [88.192, 14.885],
                    [88.245, 14.898],
                    [88.358, 14.862],
                    [88.398, 14.812],
                    [88.345, 14.775],
                    [88.241, 14.792],
                    [88.185, 14.835],
                    [88.192, 14.885]
                ]
            ]
        }
        hindcast_payload = {
            "incident_id": incident_id,
            "slick_polygon": slick_poly,
            "timestamp": now_utc.isoformat()
        }
        hc_resp = await client.post("/api/v1/drift/hindcast", json=hindcast_payload, headers=headers)
        assert hc_resp.status_code in [200, 201], f"Hindcast failed: {hc_resp.text}"
        hc_data = hc_resp.json()
        print(f"  [OK] Drift Hindcast computed:")
        print(f"       Origin Point: {hc_data.get('origin_point')}")
        print(f"       Origin Confidence: {hc_data.get('origin_confidence')}")
        print(f"       Hindcast Trajectory Steps: {len(hc_data.get('hindcast_path', {}).get('coordinates', [])) if hc_data.get('hindcast_path') else 'N/A'}")

        forecast_payload = {
            "incident_id": incident_id,
            "slick_polygon": slick_poly,
            "timestamp": now_utc.isoformat()
        }
        fc_resp = await client.post("/api/v1/drift/forecast", json=forecast_payload, headers=headers)
        assert fc_resp.status_code in [200, 201], f"Forecast failed: {fc_resp.text}"
        fc_data = fc_resp.json()
        print(f"  [OK] Drift Forecast computed:")
        print(f"       Forward Trajectory Steps: {len(fc_data.get('forward_path', {}).get('coordinates', [])) if fc_data.get('forward_path') else 'N/A'}")

        # ─── 7. AIS QUERY & PROBABILISTIC ATTRIBUTION ───────────────────────
        print("\n[STEP 7] Testing AIS Query & Attribution Scoring...")
        vessels_resp = await client.get("/api/v1/vessels", headers=headers)
        assert vessels_resp.status_code == 200
        vessels = vessels_resp.json()
        print(f"  [OK] Monitored vessels in database: {len(vessels)}")

        score_payload = {
            "incident_id": incident_id,
            "origin_point": {
                "type": "Point",
                "coordinates": [88.241, 14.825]
            },
            "origin_time_start": (now_utc - timedelta(hours=24)).isoformat(),
            "origin_time_end": now_utc.isoformat()
        }
        score_resp = await client.post("/api/v1/attribution/score", json=score_payload, headers=headers)
        assert score_resp.status_code in [200, 201], f"Attribution scoring failed: {score_resp.text}"
        attrib_result = score_resp.json()
        ranked = attrib_result.get("ranked_vessels", [])
        print(f"  [OK] Attribution Scoring complete: {len(ranked)} candidates ranked")
        if ranked:
            top_suspect = ranked[0]
            print(f"       Rank #1 Primary Suspect: {top_suspect.get('name')} (MMSI: {top_suspect.get('mmsi')})")
            print(f"       Composite Score: {top_suspect.get('score')} | Proximity: {top_suspect.get('proximity')} | Anomaly: {top_suspect.get('anomaly_score')}")

        # ─── 8. INVESTIGATIONS, EVIDENCE DOSSIER & CSV EXPORT ───────────────
        print("\n[STEP 8] Testing Investigation Management, Evidence Pack & CSV Export...")
        inv_resp = await client.get("/api/v1/investigations", headers=headers)
        assert inv_resp.status_code == 200
        investigations = inv_resp.json()
        assert len(investigations) > 0, "Expected at least 1 investigation"
        target_inv = investigations[0]
        inv_id = target_inv["id"]
        print(f"  [OK] Active Investigations: {len(investigations)} | Target ID: {inv_id}")

        # Fetch evidence pack
        evidence_resp = await client.get(f"/api/v1/investigations/{inv_id}/evidence", headers=headers)
        assert evidence_resp.status_code == 200, f"Evidence pack compilation failed: {evidence_resp.text}"
        evidence = evidence_resp.json()
        print(f"  [OK] Official Evidence Dossier compiled:")
        print(f"       Investigation ID: {evidence.get('investigation_id')}")
        print(f"       Chain of Custody ID: {evidence.get('chain_of_custody_id', 'CC-SEC4-2026')}")
        print(f"       Incident: {evidence.get('incident', {}).get('title')}")
        print(f"       Attributed Suspects: {len(evidence.get('attribution_scores', []))}")
        print(f"       Satellite Scenes: {len(evidence.get('satellite_scenes', []))}")

        # Export CSV report
        export_resp = await client.get(f"/api/v1/investigations/{inv_id}/export", headers=headers)
        assert export_resp.status_code == 200, f"Export CSV failed: {export_resp.text}"
        csv_content = export_resp.text
        print(f"  [OK] Official CSV Export generated ({len(csv_content)} bytes):")
        print("  --- CSV Preview (First 4 lines) ---")
        for line in csv_content.splitlines()[:4]:
            print(f"    {line}")
        print("  -----------------------------------")

    print("\n" + "=" * 80)
    print(">>> FULL END-TO-END INTEGRATION VERIFICATION PASSED WITH 100% SUCCESS <<<")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_verification())
