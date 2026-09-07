# PRD — Semi-Realtime Sentinel-1 R2 Ingestion Simulator

**Project:** SLICK TRACE  
**Feature:** Cloudflare R2 → Satellite Scene Ingestion API Simulator  
**Priority:** P0  
**Status:** Ready for implementation

## 1. Objective

Build a lightweight Python worker that polls a Cloudflare R2 bucket for new Sentinel-1 SAR images and submits each new scene to the existing ingestion API.

```text
Cloudflare R2
     ↓
Ingestion Simulator
     ↓  POST /api/v1/scenes/ingest
FastAPI Backend
     ↓
satellite_scenes
     ↓
QUEUED
     ↓
ML / Detection Pipeline
```

The worker is an ingestion simulator, not the ML inference service.

## 2. Existing API Contract

The current endpoint is:

```http
POST /api/v1/scenes/ingest
Authorization: Bearer <JWT>
Content-Type: application/json
```

It requires an analyst role and returns `202 Accepted` when the scene is queued. The endpoint accepts `source`, `scene_id`, `satellite`, `sensor`, `product_type`, `polarization`, `acquisition_time`, `processing_time`, `bbox`, `image_url`, `thumbnail_url`, `scene_metadata`, and optional `status`. fileciteturn78file4L305-L344

Example payload:

```json
{
  "source": "cloudflare-r2-replay",
  "scene_id": "S1A_SCENE_001",
  "satellite": "Sentinel-1A",
  "sensor": "SAR",
  "product_type": "GRD",
  "polarization": "VV",
  "acquisition_time": "2023-01-01T00:00:00Z",
  "processing_time": "2023-01-01T00:30:00Z",
  "bbox": {
    "type": "Polygon",
    "coordinates": [[[10,50],[10.5,50],[10.5,50.5],[10,50.5],[10,50]]]
  },
  "image_url": "https://<R2-DOMAIN>/incoming/S1A_SCENE_001/scene.tif",
  "scene_metadata": {
    "storage": "cloudflare-r2",
    "object_key": "incoming/S1A_SCENE_001/scene.tif"
  }
}
```

The backend already handles duplicate `source + scene_id` submissions, making retries safe. fileciteturn78file5L369-L388

## 3. R2 Object Structure

Use a sidecar metadata file because the API requires acquisition time and a GeoJSON bounding polygon.

```text
slicktrace-sar-ingest/
└── incoming/
    ├── S1A_SCENE_001/
    │   ├── scene.tif
    │   └── metadata.json
    ├── S1A_SCENE_002/
    │   ├── scene.tif
    │   └── metadata.json
    └── ...
```

Example `metadata.json`:

```json
{
  "scene_id": "S1A_SCENE_001",
  "satellite": "Sentinel-1A",
  "sensor": "SAR",
  "product_type": "GRD",
  "polarization": "VV",
  "acquisition_time": "2023-01-01T00:00:00Z",
  "processing_time": "2023-01-01T00:30:00Z",
  "bbox": {
    "type": "Polygon",
    "coordinates": [[[10,50],[10.5,50],[10.5,50.5],[10,50.5],[10,50]]]
  },
  "scene_metadata": {
    "orbit_direction": "DESCENDING",
    "resolution": "10m"
  }
}
```

The bbox must be a closed GeoJSON polygon and use `[longitude, latitude]` coordinate order. fileciteturn78file1L87-L109

## 4. Functional Requirements

### FR-01 — Poll R2

Poll the `incoming/` prefix every configurable interval.

```env
R2_POLL_INTERVAL_SECONDS=30
```

Use 10 seconds during the live demo if desired.

### FR-02 — Discover New Objects

The worker must identify new `.tif`, `.tiff`, or other explicitly supported SAR image objects and locate their corresponding `metadata.json`.

If metadata is missing, skip the object and log a warning instead of submitting incomplete data.

### FR-03 — Validate Metadata

Validate:

- scene ID
- satellite
- product type
- acquisition timestamp
- bbox
- image URL
- supported image extension

### FR-04 — Construct Image URL

The worker should send an HTTP-accessible `image_url` to the backend. The current API validates the URL scheme but actual image accessibility is checked later by processing. fileciteturn78file3L236-L240

### FR-05 — Submit Scene

POST the metadata JSON to `/api/v1/scenes/ingest` using an analyst JWT.

### FR-06 — Track State

Maintain a small state file such as:

```text
scripts/ingestion/state/processed.json
```

Track `object_key`, `etag`, `scene_id`, `analysis_id`, status and timestamp.

### FR-07 — Retry

Retry transient errors such as 429, 500, 502, 503, 504 and network timeouts using exponential backoff.

Do not blindly retry 400/401/403/422 responses.

### FR-08 — Duplicate Handling

If the backend returns `is_duplicate=true`, mark the object as processed and continue.

## 5. Recommended Directory Structure

```text
scripts/
└── ingestion/
    ├── r2_ingestor.py
    ├── r2_client.py
    ├── api_client.py
    ├── metadata.py
    ├── config.py
    ├── state.py
    ├── models.py
    ├── logger.py
    ├── requirements.txt
    ├── .env.example
    └── state/
        └── .gitkeep
```

Responsibilities:

| File | Responsibility |
|---|---|
| `r2_ingestor.py` | Main polling loop |
| `r2_client.py` | R2/S3 listing and object access |
| `api_client.py` | FastAPI HTTP client |
| `metadata.py` | Sidecar metadata validation |
| `config.py` | Environment configuration |
| `state.py` | Processed-object tracking |
| `models.py` | Typed metadata structures |
| `logger.py` | Logging |

## 6. Environment Variables

Create `scripts/ingestion/.env` locally:

```env
# Cloudflare R2
R2_ACCOUNT_ID=<cloudflare-account-id>
R2_BUCKET_NAME=slicktrace-sar-ingest
R2_ACCESS_KEY_ID=<r2-access-key>
R2_SECRET_ACCESS_KEY=<r2-secret-key>
R2_ENDPOINT_URL=https://<ACCOUNT_ID>.r2.cloudflarestorage.com
R2_PUBLIC_BASE_URL=https://<r2-custom-domain>
R2_PREFIX=incoming/

# Backend
INGESTION_API_URL=http://localhost:8000/api/v1/scenes/ingest
INGESTION_JWT=<analyst-jwt>

# Simulator
R2_POLL_INTERVAL_SECONDS=30
MAX_RETRIES=5
REQUEST_TIMEOUT_SECONDS=30
LOG_LEVEL=INFO
```

Cloudflare's S3-compatible endpoint is `https://<ACCOUNT_ID>.r2.cloudflarestorage.com`; R2 S3 access uses an Access Key ID and Secret Access Key. citeturn0search2turn0search3

Never commit `.env` or R2 secrets.

## 7. Cloudflare R2 Configuration

### Bucket name

Recommended:

```text
slicktrace-sar-ingest
```

Fallback if a unique name is required:

```text
sih26-slicktrace-sar-ingest
```

### Access

Create a dedicated R2 API token restricted to this bucket. The simulator needs object listing/read access; it should not have administrative permissions or public write access. Cloudflare supports bucket-scoped R2 credentials. citeturn0search3turn0search8

### Public image access

For this MVP, the simplest approach is a **public-read bucket/custom domain** because the backend/detection pipeline needs to retrieve the image after ingestion.

Use:

```text
https://<custom-domain>/incoming/<scene>/scene.tif
```

A Cloudflare `r2.dev` URL is acceptable for development/demo use; a custom domain is preferable for production. citeturn0search5

Do **not** make the bucket publicly writable.

### Alternative: private bucket

A private bucket can use a presigned GET URL, but this introduces an expiry problem if the backend stores the URL and processes the scene after the URL expires. Cloudflare presigned URLs are time-limited bearer URLs. citeturn0search1

Therefore, for this MVP:

**Public read + authenticated write/list through S3 credentials is the recommended design.**

## 8. CORS

CORS is only relevant when a browser/frontend directly requests R2 objects. The Python ingestion worker does not require browser CORS.

If React will display R2 images directly, configure the R2 bucket with:

```json
[
  {
    "AllowedOrigins": [
      "http://localhost:5173",
      "http://localhost:3000"
    ],
    "AllowedMethods": ["GET", "HEAD"],
    "AllowedHeaders": ["*"],
    "ExposeHeaders": ["ETag"],
    "MaxAgeSeconds": 3600
  }
]
```

Production should use only the actual frontend origin:

```json
[
  {
    "AllowedOrigins": ["https://your-frontend-domain.com"],
    "AllowedMethods": ["GET", "HEAD"],
    "AllowedHeaders": ["*"],
    "ExposeHeaders": ["ETag"],
    "MaxAgeSeconds": 3600
  }
]
```

Cloudflare requires origins to match the browser origin and not include a path. citeturn0search0

Remember there are two separate CORS configurations:

```text
React → FastAPI CORS
React → R2 CORS
```

The R2 worker itself does not need CORS.

## 9. Python Dependencies

Keep the simulator lightweight:

```text
boto3
requests
python-dotenv
pydantic
```

Optional:

```text
tenacity
```

Do not add PyTorch, TensorFlow, PostgreSQL drivers, or geospatial libraries to this script unless actually required. The worker only orchestrates ingestion.

## 10. Main Processing Loop

```text
START
  ↓
Load configuration
  ↓
Connect to R2
  ↓
List incoming/ objects
  ↓
Find unprocessed scene
  ↓
Check image + metadata exist
  ↓
Validate metadata
  ↓
Construct public image URL
  ↓
POST /api/v1/scenes/ingest
  ↓
202 Accepted?
  ├── YES → save state → next scene
  └── NO  → retry/log error
  ↓
Sleep
  ↓
Repeat
```

## 11. Security

`.gitignore` must contain:

```gitignore
.env
scripts/ingestion/.env
scripts/ingestion/state/*.json
```

Commit only:

```text
.env.example
```

Never commit:

```text
R2_SECRET_ACCESS_KEY
INGESTION_JWT
```

## 12. Acceptance Criteria

- [ ] R2 bucket exists.
- [ ] `incoming/` prefix exists.
- [ ] At least three test SAR images are uploaded.
- [ ] Every image has valid sidecar metadata.
- [ ] Worker discovers new images automatically.
- [ ] Worker constructs the correct R2 URL.
- [ ] Worker authenticates with an analyst JWT.
- [ ] Worker calls `POST /api/v1/scenes/ingest`.
- [ ] Backend returns `202 Accepted`.
- [ ] Scene appears in `satellite_scenes`.
- [ ] Scene becomes `QUEUED`.
- [ ] `analysis_id` is captured.
- [ ] Duplicate objects do not create duplicate DB records.
- [ ] Transient failures are retried.
- [ ] Worker restart does not break ingestion.
- [ ] Detection pipeline can retrieve the R2 image.

## 13. Demo Flow

1. Open Cloudflare R2.
2. Upload `scene-001/scene.tif` and `metadata.json`.
3. Worker detects it within 10–30 seconds.
4. Worker submits the scene to FastAPI.
5. FastAPI returns `202 / QUEUED`.
6. Scene appears in the dashboard/database.
7. Detection pipeline processes the image.
8. Dashboard displays the resulting oil-slick detection.

This gives the team a visible semi-realtime pipeline instead of manually inserting database records.

## 14. Future Upgrade

Current MVP:

```text
R2 → Polling Worker → FastAPI → DB → ML
```

Future event-driven version:

```text
R2 Object Created Event
        ↓
Queue / Worker
        ↓
FastAPI / Processing Pipeline
        ↓
ML
```

Keep the R2 client and API client separated so the polling mechanism can later be replaced by event-driven notifications without rewriting the ingestion logic.

## 15. Definition of Done

> **A new Sentinel-1 SAR image placed into the Cloudflare R2 `incoming/` prefix must automatically become a `QUEUED` satellite scene in SLICK TRACE without any manual database or API operation.**

### Recommended architecture

```text
                 CLOUD STORAGE
              ┌─────────────────┐
              │ Cloudflare R2   │
              │ SAR TIFF        │
              │ Metadata JSON   │
              └────────┬────────┘
                       │ S3 API
                       ▼
              ┌─────────────────┐
              │ R2 Ingestion    │
              │ Simulator       │
              │ Poll + Validate │
              └────────┬────────┘
                       │ HTTPS + JWT
                       ▼
              ┌─────────────────┐
              │ FastAPI         │
              │ /scenes/ingest  │
              └────────┬────────┘
                       ▼
              ┌─────────────────┐
              │ PostgreSQL      │
              │ + PostGIS       │
              └────────┬────────┘
                       │ QUEUED
                       ▼
              ┌─────────────────┐
              │ ML / Detection  │
              └─────────────────┘
```
