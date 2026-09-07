# Backend Development How-To Guides

> Practical guides for common backend development tasks in the Oil Spill Detection Platform

## Table of Contents

- [Adding New API Endpoints](#adding-new-api-endpoints)
- [Creating Service Adapters](#creating-service-adapters)
- [Working with Geospatial Data](#working-with-geospatial-data)
- [Database Migrations](#database-migrations)
- [Testing Strategies](#testing-strategies)
- [Mocking External Services](#mocking-external-services)
- [Handling ML Model Integration](#handling-ml-model-integration)
- [Adding New Attribution Factors](#adding-new-attribution-factors)
- [Performance Optimization](#performance-optimization)

## Adding New API Endpoints

### Step-by-Step Guide

1. **Determine the endpoint purpose and layer placement**
   - API routes should be thin layers that only handle:
     - Request/response validation (via Pydantic schemas)
     - Authentication/authorization dependencies
     - Calling the appropriate service method
     - Returning service results
   - Never put business logic in API routes

2. **Create or update Pydantic schemas**
   - File: `backend/app/schemas/[feature].py`
   - Follow existing patterns for request/response models
   - Use Field() for validation constraints (ge, le, etc.)
   - Include descriptive docstrings

   ```python
   # Example: backend/app/schemas/new_feature.py
   from pydantic import BaseModel, Field
   from typing import Optional, List
   from uuid import UUID
   
   class NewFeatureRequest(BaseModel):
       parameter_one: str = Field(..., min_length=1, max_length=100)
       parameter_two: Optional[List[UUID]] = None
   
   class NewFeatureResponse(BaseModel):
       result_id: UUID
       status: str
       processing_time_ms: int
   ```

3. **Implement the service method**
   - File: `backend/app/services/[feature]_service.py`
   - Contain all business logic, validation, and external calls
   - Follow dependency injection pattern (receive DB session)
   - Handle exceptions appropriately
   - Return domain models or dictionaries (not Pydantic models)

   ```python
   # Example: backend/app/services/new_feature_service.py
   from sqlalchemy.ext.asyncio import AsyncSession
   from app.models.new_feature import NewFeatureModel
   
   async def process_new_feature(
       db: AsyncSession, 
       request: NewFeatureRequest
   ) -> NewFeatureModel:
       """
       Process the new feature request.
       
       Args:
           db: Database session
           request: Validated request data
           
       Returns:
           NewFeatureModel: The processed result
       """
       # Business logic here
       result = NewFeatureModel(
           # ... populate fields
       )
       
       db.add(result)
       await db.commit()
       await db.refresh(result)
       
       return result
   ```

4. **Create API route handler**
   - File: `backend/app/api/v1/[feature].py`
   - Keep it thin - only handle HTTP concerns
   - Use appropriate status codes and response models
   - Include proper error handling that translates to standard envelope

   ```python
   # Example: backend/app/api/v1/new_feature.py
   from fastapi import APIRouter, Depends, status
   from sqlalchemy.ext.asyncio import AsyncSession
   from app.core.database import get_db
   from app.core.security import require_analyst
   from app.schemas.new_feature import NewFeatureRequest, NewFeatureResponse
   from app.services.new_feature_service import process_new_feature
   
   router = APIRouter(
       prefix="/new-feature", 
       tags=["New Feature"], 
       dependencies=[Depends(require_analyst)]
   )
   
   @router.post("/", response_model=NewFeatureResponse, status_code=status.HTTP_201_CREATED)
   async def create_new_feature(
       request: NewFeatureRequest,
       db: AsyncSession = Depends(get_db)
   ):
       """
       Process a new feature request.
       
       Args:
           request: Validated request data
           db: Database session (injected)
           
       Returns:
           NewFeatureResponse: Processing results
       """
       try:
           result = await process_new_feature(db, request)
           
           return NewFeatureResponse(
               result_id=result.id,
               status="completed",
               processing_time_ms=result.processing_time_ms
           )
       except ValueError as e:
           # Handle validation errors
           raise HTTPException(
               status_code=status.HTTP_400_BAD_REQUEST,
               detail={"code": "VALIDATION_ERROR", "message": str(e)}
           )
       except Exception as e:
           # Handle unexpected errors
           raise HTTPException(
               status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
               detail={"code": "INTERNAL_ERROR", "message": "An unexpected error occurred"}
           )
   ```

5. **Register the router**
   - File: `backend/app/api/v1/router.py`
   - Import and include your new router

   ```python
   # In backend/app/api/v1/router.py
   from app.api.v1 import new_feature as new_feature_router
   
   api_router.include_router(new_feature_router.router)
   ```

6. **Add unit tests**
   - File: `backend/tests/test_[feature]_api.py`
   - Test both success and error cases
   - Use mock DB sessions when possible
   - Test the standard error envelope format

### Best Practices

- **Keep API handlers thin**: They should only translate HTTP concerns to service calls
- **Use proper status codes**: 200 for GET, 201 for POST, 204 for DELETE, etc.
- **Always validate input**: Never trust client data - use Pydantic models
- **Handle exceptions**: Convert domain exceptions to appropriate HTTP responses
- **Follow naming conventions**: Use plural nouns for collections (`/vessels`), singular for specific resources (`/vessels/{id}`)
- **Document everything**: Include docstrings that explain purpose, parameters, and return values

## Creating Service Adapters

### When to Create a New Adapter

Create a new integration adapter when:
- You need to call an external third-party API or service
- The integration requires authentication, rate limiting, or special handling
- You want to maintain the ability to swap implementations (fixture ↔ real)
- The integration has distinct failure modes that need handling

### Adapter Interface Pattern

All adapters should follow a common interface to allow easy swapping:

```python
# Example pattern from ML providers
from abc import ABC, abstractmethod
from typing import Dict, Any

class MLInferenceProvider(ABC):
    @abstractmethod
    async def predict(self, scene: SatelliteScene) -> Dict[str, Any]:
        """
        Run ML inference on a satellite scene.
        
        Args:
            scene: Satellite scene to analyze
            
        Returns:
            Prediction dictionary following PRD contract
        """
        pass
```

### Step-by-Step: Creating a New Adapter

1. **Define the interface** (if one doesn't exist)
   - Create abstract base class in `backend/app/interfaces/` or in the service file
   - Define all methods the adapter must implement

2. **Create the adapter implementation**
   - File: `backend/app/integrations/[provider]_adapter.py`
   - Implement all interface methods
   - Handle authentication, error cases, rate limiting
   - Convert external formats to internal formats
   - Include proper logging and timing

   ```python
   # Example: backend/app/integrations/ml_provider.py
   import httpx
   import asyncio
   from typing import Dict, Any
   from app.core.config import settings
   from app.models.satellite_scene import SatelliteScene
   
   class RESTMLProvider:
       def __init__(self, service_url: str, timeout_seconds: int = 30):
           self.service_url = service_url.rstrip('/')
           self.timeout_seconds = timeout_seconds
       
       async def predict(self, scene: SatelliteScene) -> Dict[str, Any]:
           """
           Call external ML REST API for spill detection.
           
           Args:
               scene: Satellite scene to analyze
               
           Returns:
               ML prediction following PRD contract
               {
                   "detected": bool,
                   "confidence": float [0-1],
                   "area_km2": float,
                   "geometry": {GeoJSON Polygon},
                   "model_name": str,
                   "model_version": str
               }
           """
           # Prepare request payload
           payload = {
               "scene_id": scene.scene_id,
               "image_url": scene.url,
               "timestamp": scene.timestamp.isoformat() if scene.timestamp else None
           }
           
           # Make HTTP request with timeout
           async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
               try:
                   response = await client.post(
                       f"{self.service_url}/predict",
                       json=payload
                   )
                   response.raise_for_status()
                   
                   prediction = response.json()
                   
                   # Validate response format
                   self._validate_prediction(prediction)
                   
                   return prediction
               except httpx.TimeoutException:
                   raise TimeoutError(f"ML service timeout after {self.timeout_seconds}s")
               except httpx.HTTPStatusError as e:
                   raise ConnectionError(f"ML service error: {e.response.status_code}")
               except Exception as e:
                   raise RuntimeError(f"ML service failed: {str(e)}")
       
       def _validate_prediction(self, prediction: Dict[str, Any]) -> None:
           """Validate that prediction matches expected PRD format."""
           required_fields = ["detected", "confidence", "area_km2", "geometry", 
                            "model_name", "model_version"]
           
           for field in required_fields:
               if field not in prediction:
                   raise ValueError(f"Missing required field: {field}")
                   
           # Additional validation logic...
   ```

3. **Create a factory/provider selector**
   - File: `backend/app/services/[feature]_service.py` or dedicated provider service
   - Implement logic to select appropriate provider based on configuration
   - Usually based on environment variables

   ```python
   # Example: backend/app/services/ml_inference_service.py
   from app.integrations.ml import MLInferenceProvider, FixtureMLProvider, RESTMLProvider
   from app.core.config import settings
   
   async def get_ml_provider() -> MLInferenceProvider:
       """
       Factory function to get the configured ML provider.
       
       Returns:
           Configured MLInferenceProvider instance
       """
       provider_type = settings.ML_PROVIDER.lower()
   
       if provider_type == "fixture":
           return FixtureMLProvider()
       elif provider_type == "rest":
           return RESTMLProvider(
               service_url=settings.ML_SERVICE_URL,
               timeout_seconds=settings.ML_INFERENCE_TIMEOUT_SECONDS
           )
       else:
           # Default to fixture for safety
           return FixtureMLProvider()
   ```

4. **Use the adapter in your service**
   - Inject the provider rather than instantiating directly
   - Follow the dependency inversion principle

   ```python
   # In your service method
   provider = await get_ml_provider()
   prediction = await provider.predict(scene)
   ```

### Best Practices for Adapters

- **Handle timeouts explicitly**: Use asyncio.timeout or httpx timeout parameters
- **Convert errors to domain exceptions**: Don't leak HTTP or library-specific exceptions
- **Validate all inputs and outputs**: Protect against malformed external responses
- **Log appropriately**: Include timing, success/failure, and key metrics
- **Support fixture mode**: Always provide a fixture implementation for development/testing
- **Keep adapters focused**: Each adapter should handle one external service concern
- **Follow SRPC**: Single Responsibility Principle - one reason to change

## Working with Geospatial Data

### Coordinate Reference Systems

The system standardizes on **SRID 4326** (WGS 84 latitude/longitude) for all PostGIS geometry storage, with exceptions documented when needed.

### Common Geospatial Operations

#### 1. Creating Geometry Objects

```python
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import Point, Polygon
from shapely import wkt

# From Shapely to PostGIS
point = Point(lon, lat)  # Note: Shapely uses (x, y) = (lon, lat)
pg_point = from_shape(point, srid=4326)

# From PostGIS to Shapely  
pg_point = db.query(GeomColumn).first()
point = to_shape(pg_point)

# From WKT string
point = from_shape(wkt.loads("POINT(lon lat)"), srid=4326)
```

#### 2. Distance Calculations

```python
from app.services.geospatial_service import GeospatialService

geo_service = GeospatialService()

# Calculate distance between two points in kilometers
distance_km = geo_service.calculate_distance(point1, point2)

# Calculate buffer around a point
buffer_geom = geo_service.create_buffer(point, distance_meters=1000)

# Check if geometry contains point
contains = geo_service.contains(polygon_geom, point_geom)
```

#### 3. Area Calculations

```python
# Area in square meters from PostGIS geography (more accurate for large areas)
# Area in square degrees from PostGIS geometry (need conversion)

# Using geography type for accurate area calculation on spheroid
area_sq_m = func.ST_Area(geog_column)  # Returns square meters

# Converting from geometry (requires projection to appropriate CRS)
# Better to use geography for area when possible
```

#### 4. Common PostGIS Functions Used

- `ST_Distance(geometry1, geometry2)` - Minimum distance between two geometries
- `ST_Intersects(geometry1, geometry2)` - True if geometries intersect
- `ST_Contains(geometry1, geometry2)` - True if geometry1 completely contains geometry2
- `ST_Within(geometry1, geometry2)` - True if geometry1 is completely within geometry2
- `ST_Buffer(geometry, distance)` - Geometry buffered by distance
- `ST_Centroid(geometry)` - Geometric centroid
- `ST_Area(geometry)` - Area of geometry
- `ST_Length(geometry)` - Length of line string
- `ST_MakePoint(lon, lat, srid)` - Create point from coordinates
- `ST_MakePolygon(linestring)` - Create polygon from closed linestring

### Geospatial Service Layer

Use `backend/app/services/geospatial_service.py` for common operations:

```python
from app.services.geospatial_service import GeospatialService

geo_service = GeospatialService()

# Calculate centroid of a geometry
centroid = geo_service.calculate_centroid(geometry)

# Calculate bounding box
bbox = geo_service.calculate_bounding_box(geometry)

# Calculate distance between two points
distance = geo_service.calculate_distance(point1, point2)

# Check if point is within polygon
is_within = geo_service.contains(polygon, point)
```

### Best Practices for Geospatial Data

- **Always specify SRID 4326** when creating PostGIS geometries unless you have a specific reason not to
- **Use geography type** for distance/area calculations when accuracy over large distances matters
- **Validate geometry objects** before storing - check for validity, simplicity, etc.
- **Use appropriate indexing**: 
  - GiST index for geometry columns: `CREATE INDEX ON table USING GIST (geom_col);`
  - BRIN index for temporal data: `CREATE INDEX ON table USING BRIN (timestamp_col);`
  - Combined SP-GiST for spatiotemporal queries
- **Consider performance**: Complex geometric operations can be expensive - simplify when possible
- **Handle edge cases**: Invalid geometries, empty geometries, NaN coordinates
- **Follow right-hand rule**: Exterior rings counter-clockwise, interior rings clockwise

## Database Migrations

### Using Alembic for Schema Changes

The system uses Alembic for database migration management.

#### Creating a Migration

1. **Make your model changes** in `backend/app/models/`
2. **Generate migration script**:
   ```bash
   cd backend
   alembic revision --autogenerate -m "Description of changes"
   ```
3. **Review the generated script** in `backend/migrations/versions/`
4. **Apply the migration**:
   ```bash
   alembic upgrade head
   ```

#### Migration Best Practices

- **Keep migrations atomic**: Each migration should accomplish one logical change
- **Write descriptive messages**: Explain what and why, not just how
- **Test migrations**: Apply to a copy of production data before running on prod
- **Include data migrations**: When schema changes require data transformation
- **Provide downgrade paths**: Make migrations reversible when possible
- **Avoid destructive operations**: Be careful with dropping columns/tables
- **Use batch operations**: For large table alterations to minimize locking
- **Check for data loss**: Ensure migrations don't inadvertently delete data

#### Example Migration Structure

```python
"""Add vessel risk assessment fields

Revision ID: 1234567890ab
Revises: abcdef123456
Create Date: 2026-09-06 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '1234567890ab'
down_revision = 'abcdef123456'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('vessels', sa.Column('risk_score', sa.Float(), nullable=True))
    op.add_column('vessels', sa.Column('risk_level', sa.String(length=20), nullable=True))
    op.create_index(op.f('ix_vessels_risk_score'), 'vessels', ['risk_score'], unique=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_vessels_risk_score'), table_name='vessels')
    op.drop_column('vessels', 'risk_level')
    op.drop_column('vessels', 'risk_score')
    # ### end Alembic commands ###
```

### Working with Spatial Data in Migrations

When adding spatial columns:

```python
from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry

def upgrade():
    # Add PostGIS extension if not present
    op.execute('CREATE EXTENSION IF NOT EXISTS postgis')
    
    # Add geometry column
    op.add_column('slick_detections',
        sa.Column('geom', Geometry(geometry_type='POLYGON', srid=4326), nullable=True)
    )
    
    # Create spatial index
    op.create_index(
        'ix_slick_detections_geom', 
        'slick_detections', 
        [sa.text('geom')], 
        postgresql_using='GIST'
    )

def downgrade():
    op.drop_index('ix_slick_detections_geom', table_name='slick_detections')
    op.drop_column('slick_detections', 'geom')
```

## Testing Strategies

### Types of Tests

1. **Unit Tests**: Test individual functions/methods in isolation
2. **Integration Tests**: Test API endpoints with test database
3. **Service Tests**: Test service logic with mocked dependencies
4. **Contract Tests**: Verify API request/response formats

### Testing Pyramid Guidance
```
        UI/E2E Tests (few)
           ▲
     Integration Tests (some)
           ▲
      Service/Unit Tests (many)
```

### Setting Up Tests

#### Test Configuration
- Uses `pytest` with `pytest-asyncio` for async tests
- Test database configured in `backend/tests/conftest.py`
- Fixtures for common objects (DB session, test clients, etc.)

#### Running Tests

```bash
# All tests
cd backend
pytest -v

# Specific test file
pytest tests/test_attribution_service.py -v

# Specific test function
pytest tests/test_attribution_service.py::test_calculate_attribution_scores -v

# With coverage
pytest --cov=app tests/

# Watch mode during development
pytest-watch tests/
```

### Writing Effective Tests

#### 1. Unit Test Example (Service)

```python
# backend/tests/test_attribution_service.py
import pytest
from uuid import uuid4
from datetime import datetime, timedelta, UTC
from app.schemas.attribution import ScoreRequest, GeoJSONPoint
from app.services.attribution_service import calculate_attribution_scores

@pytest.mark.asyncio
async def test_calculate_attribution_scores_basic(db_session):
    """Test basic attribution score calculation."""
    # Arrange
    incident_id = uuid4()
    origin_point = GeoJSONPoint(lat=18.412, lng=88.245)
    origin_time_start = datetime(2026, 8, 27, 4, 12, 0, tzinfo=UTC)
    origin_time_end = datetime(2026, 8, 27, 4, 18, 0, tzinfo=UTC)
    
    request = ScoreRequest(
        incident_id=incident_id,
        origin_point=origin_point,
        origin_time_start=origin_time_start,
        origin_time_end=origin_time_end
    )
    
    # Act
    scores = await calculate_attribution_scores(db_session, request)
    
    # Assert
    assert isinstance(scores, list)
    # With fixture data, we should get some results
    assert len(scores) > 0
    
    # Check score properties
    for score in scores:
        assert 0.0 <= score.score <= 1.0
        assert 0.0 <= score.proximity_score <= 1.0
        assert 0.0 <= score.temporality_score <= 1.0
        assert 0.0 <= score.trajectory_score <= 1.0
        assert 0.0 <= score.anomaly_score <= 1.0
        assert isinstance(score.anomaly_flag, bool)
        assert score.explanation is not None
        assert len(score.explanation) > 0
```

#### 2. Integration Test Example (API)

```python
# backend/tests/test_attribution_api.py
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_attribution_score_endpoint():
    """Test the attribution score API endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Arrange
        request_data = {
            "incident_id": "11111111-1111-1111-1111-111111111111",
            "origin_point": {"lat": 18.412, "lng": 88.245},
            "origin_time_start": "2026-08-27T04:12:00Z",
            "origin_time_end": "2026-08-27T04:18:00Z"
        }
        
        # Act
        response = await client.post("/api/v1/attribution/score", json=request_data)
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        
        # Check standard envelope format isn't present (success case)
        assert "error" not in data
        assert "ranked_vessels" in data
        assert isinstance(data["ranked_vessels"], list)
        
        # Check response structure
        if data["ranked_vessels"]:
            vessel = data["ranked_vessels"][0]
            assert "vessel_id" in vessel
            assert "mmsi" in vessel
            assert "name" in vessel
            assert "score" in vessel
            assert 0.0 <= vessel["score"] <= 1.0
```

#### 3. Mocking External Dependencies

```python
# Example: Mocking ML service in tests
from unittest.mock import AsyncMock, patch
import pytest

@pytest.mark.asyncio
async def test_ml_inference_service_with_mock(db_session, sample_satellite_scene):
    """Test ML inference service with mocked provider."""
    # Mock the ML provider to return predictable results
    mock_prediction = {
        "detected": True,
        "confidence": 0.95,
        "area_km2": 15.2,
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[88.23, 18.40], [88.26, 18.41], [88.25, 18.43], [88.22, 18.42], [88.23, 18.40]]]
        },
        "model_name": "test-model",
        "model_version": "1.0.0"
    }
    
    with patch('app.services.ml_inference_service.get_ml_provider') as mock_get_provider:
        mock_provider = AsyncMock()
        mock_provider.predict.return_value = mock_prediction
        mock_get_provider.return_value = mock_provider
        
        # Act
        from app.services.ml_inference_service import process_ml_inference
        result = await process_ml_inference(db_session, sample_satellite_scene)
        
        # Assert
        assert result.oil_spill_detected == True
        assert result.confidence == 0.95
        assert len(result.spill_regions) == 1
        
        # Verify the mock was called
        mock_provider.predict.assert_called_once_with(sample_satellite_scene)
```

### Testing Best Practices

- **Test behavior, not implementation**: Focus on what the code does, not how it does it
- **Use descriptive test names**: `test_[method]_[condition]_[expected_result]`
- **Follow Arrange-Act-Assert pattern**: Clearly separate test phases
- **Test edge cases**: Empty inputs, boundary values, invalid data
- **Test error conditions**: Verify proper error handling and standard envelope format
- **Keep tests independent**: Each test should be able to run in isolation
- **Use fixtures effectively**: Share common setup logic through pytest fixtures
- **Don't over-test**: Focus on public interfaces and critical logic paths
- **Test both success and failure paths**: Equally important
- **Use factories for test data**: Tools like `factory_boy` or custom builders

## Mocking External Services

### Why Mock External Services

- **Cost**: Avoid consuming paid API credits during development/testing
- **Speed**: Eliminate network latency and external service variability
- **Reliability**: Tests shouldn't fail due to external service downtime
- **Control**: Simulate specific scenarios (errors, timeouts, edge cases)
- **Determinism**: Ensure tests produce consistent results

### Mocking Strategies

#### 1. Using `unittest.mock` with AsyncMock

```python
from unittest.mock import AsyncMock, patch
import pytest

@pytest.mark.asyncio
async def test_service_with_mocked_external_call():
    """Test service that calls external API."""
    # Mock the external call
    with patch('app.services.external_service.ExternalClient.call_api') as mock_call:
        mock_call.return_value = {"result": "success"}
        
        # Call service method
        result = await external_service.do_something()
        
        # Verify
        mock_call.assert_called_once_with(expected_params)
        assert result == {"result": "success"}
```

#### 2. Creating Test Doubles/Fakes

```python
# Example: Fake AIS provider for testing
class FakeAISProvider:
    def __init__(self, return_tracks=None):
        self.return_tracks = return_tracks or []
        self.call_count = 0
    
    async def query_ais_tracks(self, start_time, end_time):
        self.call_count += 1
        return self.return_tracks
    
    async def detect_ais_gaps(self, tracks, threshold_hours=2.0):
        return []  # No gaps by default

# Usage in test
fake_ais = FakeAISProvider(return_tracks=[sample_track1, sample_track2])
# Inject fake_ais into service instead of real provider
```

#### 3. Environment-Based Mocking (Fixture vs Real)

The system already supports this pattern through configuration:

```python
# In .env
ML_PROVIDER=fixture  # Uses FixtureMLProvider instead of calling real ML service
GFW_PROVIDER=fixture  # Uses fake GFW data
CMEMS_PROVIDER=fixture  # Uses mocked ocean current data
```

To add a new fixture provider:
1. Create `Fixture[Provider]Provider` class that implements the same interface
2. Return realistic but predictable test data
3. Add to the provider factory logic
4. Set corresponding environment variable to "fixture" in test environment

### Best Practices for Mocking

- **Mock at the right level**: Mock the interface your code directly depends on
- **Don't over-mock**: If you're mocking everything, your test may not be testing real integration
- **Verify interactions**: Use `assert_called_once_with()` to ensure correct calls
- **Test with real implementations occasionally**: Integration tests against real services (in staging)
- **Keep mocks simple**: Don't reproduce complex logic in mocks unless necessary
- **Clear mock state**: Reset mock call counts between tests if reusing instances
- **Test error conditions**: Mock timeouts, HTTP errors, malformed responses

## Handling ML Model Integration

### ML Integration Pattern

The system follows a provider pattern for ML integration:

```
Satellite Scene → ML Inference Service → ML Provider Factory → 
[FixtureMLProvider OR RESTMLProvider] → External ML Service
```

### Adding Support for New ML Models

1. **Validate the model output format** matches the PRD contract:
   ```json
   {
     "detected": boolean,
     "confidence": float [0-1],
     "area_km2": float ≥ 0,
     "geometry": {GeoJSON Polygon},
     "model_name": string,
     "model_version": string
   }
   ```

2. **Update the provider** if needed:
   - For REST providers: May need to adjust request/response mapping
   - For fixture providers: Update the returned test data

3. **Validate predictions** in `ml_inference_service.py`:
   - The `validate_ml_prediction()` function checks all required fields
   - Add any model-specific validation if needed

4. **Update documentation** if the model has special characteristics
   - Processing time expectations
   - Input requirements (image size, bands, etc.)
   - Output limitations or known issues

### Working with the Existing ML Contract

The ML inference service expects predictions in this format:

```python
{
    "detected": True,                                    # Boolean: spill present?
    "confidence": 0.95,                                 # Float [0-1]: model confidence
    "area_km2": 15.2,                                  # Float ≥ 0: spill area in sq km
    "geometry": {                                      # GeoJSON Polygon
        "type": "Polygon", 
        "coordinates": [[
            [88.230, 18.400],
            [88.260, 18.415],
            [88.255, 18.435],
            [88.225, 18.420],
            [88.230, 18.400]
        ]]
    },
    "model_name": "ultralytics-yolov8",                # String: model identifier
    "model_version": "v1.2.3"                          # String: version
}
```

#### Optional Fields (handled gracefully):
- `length_km`: Estimated slick length
- `width_km`: Estimated slick width  
- `orientation_deg`: Slick orientation in degrees
- `age_estimate_hours`: Estimated time since spill occurred
- `age_confidence`: Confidence in age estimate [0-1]
- `mask_uri`: URL to segmentation mask image
- `prediction_uri`: URL to raw prediction output

### Testing ML Integration

```python
# Test ML validation
def test_validate_ml_prediction():
    """Test ML prediction validation."""
    valid_prediction = {
        "detected": True,
        "confidence": 0.95,
        "area_km2": 15.2,
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[88.23, 18.40], [88.26, 18.41], [88.25, 18.43], [88.22, 18.42], [88.23, 18.40]]]
        },
        "model_name": "test-model",
        "model_version": "1.0.0"
    }
    
    # Should not raise
    validate_ml_prediction(valid_prediction)
    
    # Test invalid confidence
    invalid_pred = valid_prediction.copy()
    invalid_pred["confidence"] = 1.5  # Outside [0,1]
    with pytest.raises(ValueError, match="Confidence must be between 0.0 and 1.0"):
        validate_ml_prediction(invalid_pred)
```

## Performance Optimization

### Identifying Bottlenecks

1. **Use profiling tools**:
   - `cProfile` for CPU profiling
   - `memory_profiler` for memory usage
   - `py-spy` for production profiling
   - SQLAlchemy echo/logging for query analysis

2. **Monitor key metrics**:
   - API response times (by endpoint)
   - Database query performance
   - External service latency
   - CPU/memory usage per service

3. **Check slow queries**:
   ```sql
   -- Enable logging slow queries in postgresql.conf
   -- log_min_duration_statement = 500  -- log queries >500ms
   ```

### Common Optimization Techniques

#### 1. Database Query Optimization

```python
# Bad: N+1 query problem
for vessel in vessels:
    tracks = await get_tracks_for_vessel(vessel.id)  # Query per vessel!

# Good: Batch query
all_tracks = await get_tracks_for_vessels([v.id for v in vessels])
# Then group in memory

# Good: Use joins when appropriate
stmt = select(Vessel, AISTrack).join(AISTrack, Vessel.id == AISTrack.vessel_id)
```

#### 2. Geospatial Query Optimization

```python
# Ensure proper indexing
# CREATE INDEX ON ais_tracks USING GIST (geom);
# CREATE INDEX ON ais_tracks USING BRIN (timestamp);

# Use && (bbox) operator for fast filtering before exact intersection
# ST_DWithin for distance-based queries (can use index)

# Avoid functions on indexed columns in WHERE clauses
# Bad: WHERE ST_X(geom) > 0  -- prevents index use
# Good: WHERE geom && ST_MakeEnvelope(0, 0, 180, 90, 4326)
```

#### 3. Caching Strategies

```python
# Consider caching for:
# - Frequently accessed reference data (vessel characteristics)
# - Recent ML model predictions (if deterministic)
# - Aggregated statistics for dashboards
# - External service responses that don't change frequently

# Example using simple cache (consider Redis for production)
from cachetools import TTLCache
from typing import Optional

class VesselCache:
    def __init__(self, ttl_seconds: int = 300):
        self.cache = TTLCache(maxsize=1000, ttl=ttl_seconds)
    
    async def get_vessel_details(self, vessel_id: str) -> Optional[dict]:
        if vessel_id in self.cache:
            return self.cache[vessel_id]
        
        # Fetch from database
        details = await self._fetch_vessel_from_db(vessel_id)
        if details:
            self.cache[vessel_id] = details
        return details
```

#### 4. Asynchronous Optimization

```python
# Good: Run independent operations concurrently
import asyncio

async def get_vessel_data_concurrently(vessel_ids):
    # Create all coroutines
    tasks = [get_vessel_details(vid) for vid in vessel_ids]
    # Run them concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results
    vessels = []
    for i, result in enumerate(results):
        if not isinstance(result, Exception):
            vessels.append(result)
        # Handle exceptions appropriately
    
    return vessels

# Bad: Sequential processing (slower)
async def get_vessel_data_sequential(vessel_ids):
    vessels = []
    for vid in vessel_ids:
        vessel = await get_vessel_details(vid)  # Wait for each
        vessels.append(vessel)
    return vessels
```

#### 5. Response Optimization

```python
# Only fetch needed fields
# Bad: SELECT * FROM vessels when you only need name and mmsi
# Good: SELECT v.name, v.mmsi FROM vessels v

# Use pagination for large result sets
# Implement limit/offset or cursor-based pagination

# Consider response compression for large payloads
# FastAPI has middleware for this
```

### Performance Testing

```python
# Example: Load testing with locust
# locustfile.py
from locust import HttpUser, task, between

class OilSpillUser(HttpUser):
    wait_time = between(1, 3)
    
    @task(3)
    def get_detections(self):
        self.client.get("/api/v1/detections")
    
    @task(2)
    def get_attribution(self):
        self.client.post("/api/v1/attribution/score", json={
            "incident_id": "11111111-1111-1111-1111-111111111111",
            "origin_point": {"lat": 18.412, "lng": 88.245},
            "origin_time_start": "2026-08-27T04:12:00Z",
            "origin_time_end": "2026-08-27T04:18:00Z"
        })
    
    @task(1)
    def health_check(self):
        self.client.get("/api/v1/health")

# Run with: locust -f locustfile.py --host=http://localhost:8000
```

### Monitoring in Production

Consider implementing:
- **Request/response logging** (with sampling to avoid log explosion)
- **Metrics collection** (Prometheus/Grafana for latency, error rates, throughput)
- **Distributed tracing** (OpenTelemetry/Jaeger for microservices-style tracing)
- **Health check endpoints** (liveness, readiness, dependency checks)
- **Alerting** on SLA violations (error rate >1%, p99 latency >2s, etc.)

## Troubleshooting Common Issues

### "DetachedInstanceError" When Accessing Relationships

**Problem**: Accessing a relationship on an object after session closes
**Solution**: 
- Use `joinedload()` or `selectinload()` to eager-load relationships
- Access relationships while session is still open
- Convert to DTOs/Pydantic models before returning from service

### "Multiple exceptions found" During Commit

**Problem**: Multiple instances with same primary key
**Solution**: 
- Check for duplicate object additions
- Use `merge()` instead of `add()` when unsure if object exists
- Ensure proper object lifecycle management

### Geospatial Validation Errors

**Problem**: "Self-intersection at point" or "Invalid geometry"
**Solution**:
- Validate geometries before storing: `if not geom.is_valid: geom = geom.buffer(0)`
- Use `geom.simplify(tolerance)` to remove excessive vertices
- Check coordinate ordering (right-hand rule)
- Ensure polygons are closed (first==last point)

### Performance Degradation Over Time

**Problem**: Slowing queries, increasing response times
**Solution**:
- Check for missing indexes on newly queried columns
- Monitor table bloat and run VACUUM ANALYZE periodically
- Check connection pool exhaustion
- Review query execution plans for table scans
- Consider partitioning large tables (ais_tracks, slick_detections)

### ML Service Timeouts

**Problem**: ML inference taking too long
**Solution**:
- Increase timeout in configuration (temporary fix)
- Optimize ML model input (resize images, reduce bands)
- Consider model quantization or pruning
- Implement async batching for multiple scenes
- Add caching for repeated identical requests
- Consider GPU acceleration for production

---
*Last updated: 2026-09-06*
*Generated as part of backend development documentation initiative*