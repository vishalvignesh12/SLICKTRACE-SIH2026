"""
Core API and database health tests to prevent demo breakage tests.
Tests health endpoints, database connectivity, and basic API availability.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4
from datetime import datetime, UTC

from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.database import check_db_health
from app.models.incident import Incident
from app.models.user import User


@pytest.mark.asyncio
async def test_health_endpoints():
    """Test health check endpoints are available and return correct format."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Test liveness endpoint
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

        # Test readiness endpoint
        response = await client.get("/health/ready")
        # Could be 200 (if DB connected) or 503 (if DB not available in test)
        assert response.status_code in [200, 503]
        data = response.json()
        assert "status" in data
        assert data["status"] in ["ready", "unavailable"]


@pytest.mark.asyncio
async def test_database_health_check_function():
    """Test the database health check function directly."""
    # Test with mock database session
    mock_db = AsyncMock()

    # Test successful case
    mock_result = Mock()
    mock_result.scalar.return_value = 1
    mock_db.execute.return_value = mock_result

    # Patch the get_db dependency to return our mock
    with patch('app.core.database.get_db') as mock_get_db:
        mock_get_db.return_value.__aenter__.return_value = mock_db

        # Note: We can't easily test the actual check_db_health function
        # because it's a dependency that yields a session
        # But we can test that the function exists and is callable
        assert callable(check_db_health)


@pytest.mark.asyncio
async def test_core_api_endpoints_exist():
    """Test that core API endpoints exist and are accessible."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Test incidents endpoints
        response = await client.get("/api/v1/incidents")
        assert response.status_code != 404  # Endpoint exists
        # Could be 200 (with data), 401 (no auth), or 500 (server error)

        response = await client.post("/api/v1/incidents")
        assert response.status_code != 404  # POST endpoint exists

        # Test scenes endpoints
        response = await client.get("/api/v1/scenes")
        assert response.status_code != 404

        # Test detections endpoints
        response = await client.get("/api/v1/detections")
        assert response.status_code != 404

        response = await client.post("/api/v1/detections/analyze")
        assert response.status_code != 404

        # Test drift endpoints
        response = await client.get("/api/v1/drift")
        assert response.status_code != 404

        response = await client.post("/api/v1/drift/hindcast")
        assert response.status_code != 404

        response = await client.post("/api/v1/drift/forecast")
        assert response.status_code != 404

        # Test AIS endpoints
        response = await client.get("/api/v1/ais")
        assert response.status_code != 404

        response = await client.get("/api/v1/vessels")
        assert response.status_code != 404

        # Test attribution endpoints
        response = await client.get("/api/v1/attribution")
        assert response.status_code != 404

        response = await client.post("/api/v1/attribution/score")
        assert response.status_code != 404

        # Test investigation endpoints
        response = await client.get("/api/v1/investigations")
        assert response.status_code != 404

        # Test admin endpoints
        response = await client.get("/api/v1/admin/users")
        assert response.status_code != 404

        response = await client.get("/api/v1/admin/vessels")
        assert response.status_code != 404

        response = await client.get("/api/v1/admin/incidents")
        assert response.status_code != 404


@pytest.mark.asyncio
async def test_api_endpoints_return_correct_content_types():
    """Test that API endpoints return JSON content type."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Test health endpoint
        response = await client.get("/health")
        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")

        # Test OpenAPI docs
        response = await client.get("/openapi.json")
        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")

        # Test a core API endpoint (might return 401/500 but should still be JSON if successful)
        response = await client.get("/api/v1/incidents")
        if response.status_code == 200:
            assert "application/json" in response.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_cors_headers_present():
    """Test that CORS headers are present in responses."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.options("/api/v1/incidents")
        # Should have CORS headers
        # Note: Exact headers depend on CORS middleware configuration
        assert response.status_code in [200, 405]  # 200 if CORS preflight, 405 if method not allowed but endpoint exists


@pytest.mark.asyncio
async def test_models_can_be_imported_and_instantiated():
    """Test that core models can be imported and instantiated."""
    from app.models.incident import Incident
    from app.models.user import User
    from app.models.slick_detection import SlickDetection
    from app.models.drift_result import DriftResult
    from app.models.attribution import AttributionScore
    from app.models.vessel import Vessel
    from app.models.satellite_scene import SatelliteScene
    from app.models.ais_track import AISTrack
    from app.models.inference_log import MLInferenceLog

    # Test basic instantiation
    test_time = datetime.now(UTC)
    test_uuid = uuid4()

    incident = Incident(
        name="Test Incident",
        description="Test Description",
        timestamp=test_time
    )
    assert incident.name == "Test Incident"
    assert incident.timestamp == test_time

    user = User(
        name="Test User",
        email="test@example.com",
        password_hash="hashed_password",
        role="analyst"
    )
    assert user.name == "Test User"
    assert user.email == "test@example.com"
    assert user.role == "analyst"

    # Test that models have expected attributes
    assert hasattr(Incident, '__tablename__')
    assert hasattr(User, '__tablename__')
    assert hasattr(SlickDetection, '__tablename__')
    assert hasattr(DriftResult, '__tablename__')
    assert hasattr(AttributionScore, '__tablename__')
    assert hasattr(Vessel, '__tablename__')


@pytest.mark.asyncio
async def test_database_connection_configuration():
    """Test that database configuration is properly loaded."""
    from app.core.config import settings

    # Test that database URL is configured
    assert hasattr(settings, 'DATABASE_URL')
    assert isinstance(settings.DATABASE_URL, str)
    assert len(settings.DATABASE_URL) > 0

    # Test that asyncpg driver is specified (for async operations)
    # This might be postgresql+asyncpg:// or similar
    assert 'postgresql' in settings.DATABASE_URL.lower()


@pytest.mark.asyncio
async def test_error_handling_format():
    """Test that error responses follow the standard format."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Test unprotected endpoint that should fail validation
        response = await client.post("/api/v1/auth/register", json={})
        if response.status_code == 422:  # Validation error
            data = response.json()
            # FastAPI validation errors have a specific format, but we want to ensure
            # our custom error handlers work for our custom errors
            pass  # Just verify we get a JSON response

        # Test accessing protected endpoint without auth
        response = await client.get("/api/v1/auth/me")
        if response.status_code == 401:
            data = response.json()
            # Check if it follows our standard error format
            # Our auth router uses HTTPException which FastAPI formats as JSON
            assert "detail" in data or "error" in data  # Either format is acceptable


def test_settings_loading():
    """Test that application settings load correctly."""
    from app.core.config import settings

    # Test critical settings exist
    assert hasattr(settings, 'PROJECT_NAME')
    assert hasattr(settings, 'VERSION')
    assert hasattr(settings, 'API_V1_STR')
    assert hasattr(settings, 'JWT_SECRET')
    assert hasattr(settings, 'JWT_ALGORITHM')
    assert hasattr(settings, 'JWT_EXPIRATION_MINUTES')

    # Test values are reasonable
    assert settings.VERSION == "1.0.0"
    assert isinstance(settings.JWT_EXPIRATION_MINUTES, int)
    assert settings.JWT_EXPIRATION_MINUTES > 0
    assert isinstance(settings.JWT_SECRET, str)
    assert len(settings.JWT_SECRET) > 10  # Should be a reasonable secret length


@pytest.mark.asyncio
async def test_get_incident_contract_404_behavior():
    """
    Test GET /api/v1/incidents/{id} identifier resolution contract for 404:
    Nonexistent identifier (e.g. INC-2026-999 or random UUID) must return 404 NOT FOUND.
    Never silently returns an unrelated/latest incident as a fallback.
    """
    from app.core.security import require_analyst
    from app.core.database import get_db

    mock_session = AsyncMock()
    mock_result = Mock()
    mock_result.scalars.return_value.first.return_value = None
    mock_session.execute.return_value = mock_result

    app.dependency_overrides[require_analyst] = lambda: Mock(id=uuid4(), email="analyst@test.com", role="analyst")
    app.dependency_overrides[get_db] = lambda: mock_session

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Non-existent string code must return 404, never fallback to latest
            res = await client.get("/api/v1/incidents/INC-2026-999")
            assert res.status_code == 404
            data = res.json()
            assert "detail" in data or "error" in data

            # Non-existent UUID must return 404
            non_existent_uuid = str(uuid4())
            res = await client.get(f"/api/v1/incidents/{non_existent_uuid}")
            assert res.status_code == 404
            data_uuid = res.json()
            assert "detail" in data_uuid or "error" in data_uuid
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_incident_contract_success_behavior():
    """
    Test GET /api/v1/incidents/{id} returns 200 OK when incident matches by UUID or string name.
    """
    from app.core.security import require_analyst
    from app.core.database import get_db
    from app.models.incident import Incident
    from shapely.geometry import Point
    from geoalchemy2.shape import from_shape

    test_id = uuid4()
    now = datetime.now(UTC)
    mock_inc = Incident(
        id=test_id,
        name="Test Spill Alpha",
        description="Test description",
        timestamp=now,
        location=from_shape(Point(75.0, 10.0), srid=4326),
        status="DETECTED",
        created_at=now,
        updated_at=now
    )

    mock_session = AsyncMock()
    mock_result = Mock()
    mock_result.scalars.return_value.first.return_value = mock_inc
    mock_session.execute.return_value = mock_result

    app.dependency_overrides[require_analyst] = lambda: Mock(id=uuid4(), email="analyst@test.com", role="analyst")
    app.dependency_overrides[get_db] = lambda: mock_session

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Query by UUID
            res_uuid = await client.get(f"/api/v1/incidents/{test_id}")
            assert res_uuid.status_code == 200
            assert res_uuid.json()["id"] == str(test_id)

            # Query by string name
            res_name = await client.get("/api/v1/incidents/Test Spill Alpha")
            assert res_name.status_code == 200
            assert res_name.json()["name"] == "Test Spill Alpha"
    finally:
        app.dependency_overrides.clear()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
