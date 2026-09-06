"""
Test suite for dashboard API endpoints.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.core.security import require_analyst
from app.core.database import get_db
from app.schemas.dashboard import (
    DashboardOverviewResponse,
    DashboardIncidentsResponse,
    DashboardSpillsResponse,
    DashboardVesselsResponse,
    DashboardActivityResponse,
    InvestigationDetailResponse
)


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def client(mock_db_session):
    """Create test client with authentication and database overrides."""
    # Override the authentication dependency for testing
    app.dependency_overrides[require_analyst] = lambda: Mock()
    # Override the database dependency for testing
    app.dependency_overrides[get_db] = lambda: mock_db_session
    yield TestClient(app)
    # Clean up after test
    app.dependency_overrides.clear()


def test_dashboard_overview_endpoint(client, mock_db_session):
    """Test the dashboard overview endpoint."""
    # Mock the dashboard service response
    mock_overview = DashboardOverviewResponse(
        total_incidents=10,
        active_incidents=3,
        detected_spills=8,
        total_spill_area_km2=143.7,
        analyses_completed=24,
        analyses_processing=2,
        analyses_failed=1,
        high_confidence_spills=6
    )

    # Patch the dashboard service method
    with patch('app.services.dashboard_service.DashboardService.get_overview',
               return_value=mock_overview):
        response = client.get("/api/v1/dashboard/overview")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_incidents"] == 10
        assert data["active_incidents"] == 3
        assert data["detected_spills"] == 8
        assert data["total_spill_area_km2"] == 143.7
        assert data["analyses_completed"] == 24
        assert data["analyses_processing"] == 2
        assert data["analyses_failed"] == 1
        assert data["high_confidence_spills"] == 6


def test_dashboard_incidents_endpoint(client, mock_db_session):
    """Test the dashboard incidents endpoint."""
    # Mock the dashboard service response
    mock_incidents = DashboardIncidentsResponse(
        items=[
            {
                "incident_id": str(uuid4()),
                "status": "INVESTIGATION_READY",
                "detected_at": "2026-08-29T10:32:00Z",
                "confidence": 0.94,
                "area_km2": 12.4,
                "location": {"type": "Point", "coordinates": [75.98, 9.72]}
            }
        ],
        page=1,
        page_size=20,
        total=1
    )

    # Patch the dashboard service method
    with patch('app.services.dashboard_service.DashboardService.get_incidents',
               return_value=mock_incidents):
        response = client.get("/api/v1/dashboard/incidents?page=1&page_size=20")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 20
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["status"] == "INVESTIGATION_READY"
        assert data["items"][0]["confidence"] == 0.94
        assert data["items"][0]["area_km2"] == 12.4


def test_dashboard_spills_endpoint(client, mock_db_session):
    """Test the dashboard spills endpoint."""
    # Mock the dashboard service response
    mock_spills = DashboardSpillsResponse(
        type="FeatureCollection",
        features=[{
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [75.97, 9.71],
                    [75.99, 9.71],
                    [75.99, 9.73],
                    [75.97, 9.73],
                    [75.97, 9.71]
                ]]
            },
            "properties": {
                "incident_id": str(uuid4()),
                "detection_id": str(uuid4()),
                "confidence": 0.94,
                "area_km2": 12.4,
                "status": "ACTIVE"
            }
        }]
    )

    # Patch the dashboard service method
    with patch('app.services.dashboard_service.DashboardService.get_spills',
               return_value=mock_spills):
        response = client.get("/api/v1/dashboard/spills")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["type"] == "FeatureCollection"
        assert len(data["features"]) == 1
        assert data["features"][0]["type"] == "Feature"
        assert data["features"][0]["geometry"]["type"] == "Polygon"
        assert data["features"][0]["properties"]["confidence"] == 0.94
        assert data["features"][0]["properties"]["area_km2"] == 12.4


def test_dashboard_vessels_endpoint(client, mock_db_session):
    """Test the dashboard vessels endpoint."""
    # Mock the dashboard service response
    mock_vessels = DashboardVesselsResponse(
        items=[
            {
                "vessel_id": str(uuid4()),
                "name": "MSC ELSA III",
                "rank": 1,
                "attribution_score": 0.87,
                "confidence": "HIGH",
                "distance_to_origin_km": 4.2,
                "temporal_match": 0.92
            }
        ],
        page=1,
        page_size=20,
        total=1
    )

    # Patch the dashboard service method
    with patch('app.services.dashboard_service.DashboardService.get_vessel_candidates',
               return_value=mock_vessels):
        response = client.get("/api/v1/dashboard/vessels?page=1&page_size=20")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 20
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "MSC ELSA III"
        assert data["items"][0]["rank"] == 1
        assert data["items"][0]["attribution_score"] == 0.87
        assert data["items"][0]["confidence"] == "HIGH"


def test_dashboard_activity_endpoint(client, mock_db_session):
    """Test the dashboard activity endpoint."""
    # Mock the dashboard service response
    mock_activity = DashboardActivityResponse(
        items=[
            {
                "event": "OIL_SPILL_DETECTED",
                "incident_id": str(uuid4()),
                "timestamp": "2026-08-29T10:32:00Z"
            }
        ]
    )

    # Patch the dashboard service method
    with patch('app.services.dashboard_service.DashboardService.get_activity',
               return_value=mock_activity):
        response = client.get("/api/v1/dashboard/activity")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["event"] == "OIL_SPILL_DETECTED"
        assert data["items"][0]["timestamp"] == "2026-08-29T10:32:00Z"


def test_dashboard_investigations_endpoint_found(client, mock_db_session):
    """Test the dashboard investigations endpoint when investigation exists."""
    # Mock the dashboard service response
    mock_details = InvestigationDetailResponse(
        investigation={
            "id": str(uuid4()),
            "status": "READY"
        },
        detection={
            "detected": True,
            "confidence": 0.94,
            "area_km2": 12.4
        },
        spill_regions=[],
        hindcast={},
        forecast={},
        ais_tracks=[],
        candidate_vessels=[],
        attribution={},
        evidence=[]
    )

    # Patch the dashboard service method
    with patch('app.services.dashboard_service.DashboardService.get_investigation_details',
               return_value=mock_details):
        investigation_id = uuid4()
        response = client.get(f"/api/v1/dashboard/investigations/{investigation_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "investigation" in data
        assert "detection" in data
        assert data["investigation"]["status"] == "READY"
        assert data["detection"]["detected"] == True


def test_dashboard_investigations_endpoint_not_found(client, mock_db_session):
    """Test the dashboard investigations endpoint when investigation does not exist."""
    # Patch the dashboard service method to return None
    with patch('app.services.dashboard_service.DashboardService.get_investigation_details',
               return_value=None):
        investigation_id = uuid4()
        response = client.get(f"/api/v1/dashboard/investigations/{investigation_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND


def test_dashboard_endpoints_require_authentication():
    """Test that all dashboard endpoints require authentication (return 401 without auth token)."""
    unauth_client = TestClient(app)
    endpoints = [
        "/api/v1/dashboard/overview",
        "/api/v1/dashboard/incidents",
        "/api/v1/dashboard/spills",
        "/api/v1/dashboard/vessels",
        "/api/v1/dashboard/activity",
        f"/api/v1/dashboard/investigations/{uuid4()}"
    ]
    for ep in endpoints:
        response = unauth_client.get(ep)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_dashboard_and_admin_security_matrix():
    """
    Test complete security contract:
    - dashboard without token -> 401
    - dashboard with analyst token -> allowed (200)
    - dashboard with admin token -> allowed (200)
    - admin endpoint without token -> 401
    - admin endpoint with analyst token -> 403
    - admin endpoint with admin token -> allowed (200)
    """
    from app.core.security import create_access_token
    from app.core.database import get_db

    app.dependency_overrides.clear()

    mock_db = AsyncMock()
    mock_res = Mock()
    mock_res.scalars.return_value.all.return_value = []
    mock_res.scalars.return_value.first.return_value = None
    mock_res.scalar.return_value = 0
    mock_db.execute.return_value = mock_res
    app.dependency_overrides[get_db] = lambda: mock_db

    analyst_jwt = create_access_token({"sub": "analyst@test.com", "user_id": str(uuid4()), "role": "analyst", "name": "Analyst"})
    admin_jwt = create_access_token({"sub": "admin@test.com", "user_id": str(uuid4()), "role": "admin", "name": "Admin"})

    analyst_headers = {"Authorization": f"Bearer {analyst_jwt}"}
    admin_headers = {"Authorization": f"Bearer {admin_jwt}"}

    client = TestClient(app)

    try:
        # Dashboard without token -> 401
        assert client.get("/api/v1/dashboard/overview").status_code == status.HTTP_401_UNAUTHORIZED

        # Admin endpoint without token -> 401
        assert client.get("/api/v1/admin/users").status_code == status.HTTP_401_UNAUTHORIZED

        # Admin endpoint with analyst token -> 403 Forbidden
        assert client.get("/api/v1/admin/users", headers=analyst_headers).status_code == status.HTTP_403_FORBIDDEN

        # Admin endpoint with admin token -> 200 OK (allowed)
        assert client.get("/api/v1/admin/users", headers=admin_headers).status_code == status.HTTP_200_OK

        # Dashboard with analyst token -> 200 OK (allowed)
        assert client.get("/api/v1/dashboard/overview", headers=analyst_headers).status_code == status.HTTP_200_OK

        # Dashboard with admin token -> 200 OK (allowed)
        assert client.get("/api/v1/dashboard/overview", headers=admin_headers).status_code == status.HTTP_200_OK
    finally:
        app.dependency_overrides.clear()


if __name__ == "__main__":
    pytest.main([__file__])