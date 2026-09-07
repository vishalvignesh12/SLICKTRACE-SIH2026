# Satellite Scene Ingestion API

## Overview
The Satellite Scene Ingestion API endpoint allows users to submit metadata for satellite imagery (including Sentinel-1 SAR imagery) to be processed by the oil spill detection pipeline. This endpoint validates the scene metadata, checks for duplicates, persists the scene information, and queues it for analysis.

**Endpoint:** `POST /api/v1/scenes/ingest`  
**Tag:** Satellite Scenes  
**Authentication:** Requires analyst role (protected by `require_analyst` dependency)  
**Status Code:** `202 Accepted` (when successfully queued for analysis)

## Purpose
This endpoint is the entry point for introducing new satellite imagery into the oil spill detection workflow. It accepts scene metadata including:
- Scene identification information
- Satellite/sensor details
- Acquisition timing
- Spatial bounding box
- Image URL references
- Optional metadata

After validation and persistence, the scene is marked as "QUEUED" and made available for the detection pipeline to process.

## Request Payload

The endpoint expects a JSON payload conforming to the `SceneCreate` schema:

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `source` | string | Yes | Source of the satellite data | `"sentinel-1-replay"` |
| `scene_id` | string | Yes | Unique identifier for the satellite scene | `"S1A_IW_GRDH_1SDV_20230101T000000_20230101T000000_045678_056789_1234"` |
| `satellite` | string | Yes | Satellite name | `"Sentinel-1A"` |
| `sensor` | string | No | Sensor type | `"SAR"` |
| `product_type` | string | Yes | Product type | `"GRD"` |
| `polarization` | string | No | Polarization | `"VV"` |
| `acquisition_time` | datetime (ISO 8601) | Yes | When the image was acquired | `"2023-01-01T00:00:00Z"` |
| `processing_time` | datetime (ISO 8601) | No | When the image was processed | `"2023-01-01T00:30:00Z"` |
| `bbox` | GeoJSON Polygon | Yes | Bounding box of the image | See GeoJSON format below |
| `image_url` | string | Yes | URL to the actual satellite image | `"https://bucket.s3.amazonaws.com/image.tiff"` |
| `thumbnail_url` | string | No | URL to a thumbnail/preview image | `"https://bucket.s3.amazonaws.com/thumb.jpg"` |
| `scene_metadata` | object | No | Additional metadata as key-value pairs | `{"orbit_direction": "DESCENDING"}` |
| `status` | string | No | Status of the scene (defaults to "RECEIVED") | `"RECEIVED"` |

### GeoJSON Bounding Box Format
The `bbox` field must be a valid GeoJSON Polygon object:
```json
{
  "type": "Polygon",
  "coordinates": [[
    [min_lon, min_lat],
    [max_lon, min_lat],
    [max_lon, max_lat],
    [min_lon, max_lat],
    [min_lon, min_lat]  // Closed polygon (first point == last point)
  ]]
}
```

**Validation Rules for BBOX:**
- Must contain at least one coordinate ring
- Each coordinate ring must have at least 4 points
- Each ring must be closed (first point == last point)
- Coordinates must be in [longitude, latitude] order
- Longitude values must be between -180 and 180
- Latitude values must be between -90 and 90
- For each ring: min_lon < max_lon and min_lat < max_lat

### Image URL Validation
The `image_url` must use one of the following schemes:
- `http://`
- `https://`
- `file://`
- `storage://`
- `s3://`
- Or be an absolute path (starting with `/`)

## Example Request

```json
POST /api/v1/scenes/ingest
Authorization: Bearer <jwt-token>
Content-Type: application/json

{
  "source": "sentinel-1-replay",
  "scene_id": "S1A_IW_GRDH_1SDV_20230101T000000_20230101T000000_045678_056789_1234",
  "satellite": "Sentinel-1A",
  "sensor": "SAR",
  "product_type": "GRD",
  "polarization": "VV",
  "acquisition_time": "2023-01-01T00:00:00Z",
  "processing_time": "2023-01-01T00:30:00Z",
  "bbox": {
    "type": "Polygon",
    "coordinates": [[
      [10.0, 50.0],
      [10.5, 50.0],
      [10.5, 50.5],
      [10.0, 50.5],
      [10.0, 50.0]
    ]]
  },
  "image_url": "https://sentinel-1-bucket.s3.amazonaws.com/S1A_IW_GRDH_1SDV_20230101T000000_20230101T000000_045678_056789_1234.tiff",
  "thumbnail_url": "https://sentinel-1-bucket.s3.amazonaws.com/thumbs/S1A_IW_GRDH_1SDV_20230101T000000_20230101T000000_045678_056789_1234_thumb.jpg",
  "scene_metadata": {
    "orbit_direction": "DESCENDING",
    "resolution": "10m",
    "look_count": "5"
  }
}
```

## Response Format

### Success Response (202 Accepted)
```json
{
  "success": true,
  "scene_id": "S1A_IW_GRDH_1SDV_20230101T000000_20230101T000000_045678_056789_1234",
  "analysis_id": "a1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8",
  "status": "QUEUED",
  "message": "Satellite scene successfully ingested and queued for analysis",
  "is_duplicate": false
}
```

### Duplicate Scene Response (202 Accepted)
If a scene with the same `source` and `scene_id` already exists:
```json
{
  "success": true,
  "scene_id": "S1A_IW_GRDH_1SDV_20230101T000000_20230101T000000_045678_056789_1234",
  "analysis_id": "existing_123e4567-e89b-12d3-a456-426614174000",
  "status": "RECEIVED",  // or existing status
  "message": "Satellite scene already exists (duplicate detected)",
  "is_duplicate": true
}
```

### Error Responses
| Status Code | Error Condition | Response Format |
|-------------|-----------------|-----------------|
| `401 Unauthorized` | Missing or invalid authentication | `{"detail": "Not authenticated"}` |
| `403 Forbidden` | User lacks analyst role | `{"detail": "Forbidden"}` |
| `422 Unprocessable Entity` | Validation error | `{"detail": "Validation failed: <specific error messages>"}` |
| `500 Internal Server Error` | Unexpected server error | `{"detail": "Internal server error"}` |

#### Validation Error Example
```json
{
  "detail": "Validation failed: source is required and cannot be empty; scene_id is required and cannot be empty; acquisition_time cannot be more than 1 hour in the future"
}
```

## How It Works

### Processing Flow
1. **Authentication & Authorization** - Verifies user has analyst role
2. **Metadata Validation** - Checks all required fields, formats, and constraints
3. **Duplicate Detection** - Checks if scene with same `source` and `scene_id` exists
4. **Persistence** - Stores scene metadata in database (if not duplicate)
5. **Job Queuing** - Generates unique analysis ID and marks scene as "QUEUED"
6. **Logging** - Records ingestion event for audit trail

### What Happens After Ingestion
1. The scene metadata is stored in the `satellite_scenes` table
2. The scene status is set to `"QUEUED"` indicating it's ready for processing
3. A unique `analysis_id` is generated and associated with the scene
4. The scene becomes available for the detection pipeline to process
5. Users can check scene status via `GET /api/v1/scenes` or `GET /api/v1/scenes/{id}`

### Connection to Detection Pipeline
The ingestion endpoint does not run the AI model directly. Instead, it prepares the scene for processing. Detection can be triggered in two ways:

1. **Automatic Processing** - Background workers monitor for scenes with status `"QUEUED"` and automatically initiate the detection pipeline
2. **Manual Trigger** - Users can manually initiate detection using the `POST /api/v1/detections/analyze` endpoint with the scene's `scene_id`

## Related Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/api/v1/scenes` | List all registered satellite scenes |
| `GET` | `/api/v1/scenes/{id}` | Get details for a specific scene |
| `POST` | `/api/v1/detections/analyze` | Trigger analysis on a scene by `scene_id` |
| `GET` | `/api/v1/detections` | List all detected oil slicks |
| `GET` | `/api/v1/detections/analysis/{analysis_id}` | Get detection by analysis ID |

## Usage Notes

### For Sentinel-1 Specific Usage
When working with Sentinel-1 SAR imagery:
- Set `source` to `"sentinel-1-replay"` or appropriate source identifier
- Use the full Sentinel-1 product ID as `scene_id`
- Set `satellite` to `"Sentinel-1A"` or `"Sentinel-1B"`
- Set `sensor` to `"SAR"`
- Set `product_type` to `"GRD"` (Ground Range Detected) for imagery suitable for oil spill detection
- Set `polarization` to `"VV"`, `"VH"`, `"HH"`, or `"HV"` based on the product
- The `acquisition_time` should match the sensor start time from the product metadata
- The `bbox` should cover the geographical area of the SAR swath
- Provide a publicly accessible `image_url` to the GeoTIFF or JPEG2000 image file

### Idempotency Considerations
The endpoint handles duplicate submissions gracefully:
- If a scene with identical `source` and `scene_id` already exists, it returns information about the existing scene
- The existing scene's `updated_at` timestamp is refreshed to indicate re-receipt
- No duplicate database records are created
- Clients can safely retry ingestion requests without creating duplicates

### Error Handling Tips
1. **Validation Errors** - Check the response detail for specific field validation failures
2. **Authentication Issues** - Ensure your JWT token is valid and has the analyst role
3. **URL Accessibility** - The system validates URL schemes but does not verify that the image_url is actually accessible during ingestion (accessibility is checked during processing)
4. **BBOX Format** - Pay close attention to the GeoJSON polygon format requirements, especially the closed ring requirement

## Integration Examples

### Using cURL
```bash
curl -X POST "http://localhost:8000/api/v1/scenes/ingest" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "source": "sentinel-1-replay",
    "scene_id": "S1A_IW_GRDH_1SDV_20230101T000000_20230101T000000_045678_056789_1234",
    "satellite": "Sentinel-1A",
    "sensor": "SAR",
    "product_type": "GRD",
    "polarization": "VV",
    "acquisition_time": "2023-01-01T00:00:00Z",
    "processing_time": "2023-01-01T00:30:00Z",
    "bbox": {
      "type": "Polygon",
      "coordinates": [[
        [10.0, 50.0],
        [10.5, 50.0],
        [10.5, 50.5],
        [10.0, 50.5],
        [10.0, 50.0]
      ]]
    },
    "image_url": "https://sentinel-bucket.s3.amazonaws.com/S1A_IW_GRDH_1SDV_20230101T000000_20230101T000000_045678_056789_1234.tiff",
    "scene_metadata": {
      "orbit_direction": "DESCENDING"
    }
  }'
```

### Using Python Requests
```python
import requests
import json

url = "http://localhost:8000/api/v1/scenes/ingest"
headers = {
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "Content-Type": "application/json"
}
payload = {
    "source": "sentinel-1-replay",
    "scene_id": "S1A_IW_GRDH_1SDV_20230101T000000_20230101T000000_045678_056789_1234",
    "satellite": "Sentinel-1A",
    "sensor": "SAR",
    "product_type": "GRD",
    "polarization": "VV",
    "acquisition_time": "2023-01-01T00:00:00Z",
    "processing_time": "2023-01-01T00:30:00Z",
    "bbox": {
        "type": "Polygon",
        "coordinates": [[
            [10.0, 50.0],
            [10.5, 50.0],
            [10.5, 50.5],
            [10.0, 50.5],
            [10.0, 50.0]
        ]]
    },
    "image_url": "https://sentinel-bucket.s3.amazonaws.com/S1A_IW_GRDH_1SDV_20230101T000000_20230101T000000_045678_056789_1234.tiff",
    "scene_metadata": {
        "orbit_direction": "DESCENDING"
    }
}

response = requests.post(url, headers=headers, data=json.dumps(payload))
print(response.json())
```