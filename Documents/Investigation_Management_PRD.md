# PRD — Investigation Management

**Project:** AI-Based Oil Spill Detection, Hindcasting & Vessel Attribution Platform  
**Feature:** Investigation Management  
**Document Type:** Product Requirements Document  
**Status:** Ready for Implementation  
**Priority:** P0 — MVP  
**Primary Owner:** Backend Team

---

## 1. Executive Summary

Investigation Management is the central backend feature that turns an individual oil-spill detection into a trackable forensic investigation.

The system already has the upstream pipeline:

```text
Satellite Image
      ↓
Satellite Ingestion
      ↓
Analysis Orchestration
      ↓
ML Oil-Spill Detection
      ↓
Spill Detection
```

The Investigation Management layer must now provide a persistent object around that detection so that subsequent analysis can be attached to the same case.

The investigation becomes the central entity connecting:

```text
Spill Detection
      ↓
Investigation
      ├── ML results
      ├── Spill geometry
      ├── Drift / Hindcast
      ├── AIS tracks
      ├── Vessel correlation
      ├── Vessel attribution
      ├── Evidence
      ├── Analyst notes
      └── Investigation timeline
```

### MVP objective

An analyst must be able to:

1. Create an investigation from an oil-spill detection.
2. View the investigation and its current status.
3. List and filter investigations.
4. Update investigation metadata/status.
5. View the investigation's chronological activity.
6. Use the investigation ID as the parent reference for future drift, AIS and attribution workflows.

This feature should **not** implement drift, AIS correlation, or vessel attribution itself. It must provide the stable investigation boundary those features will use.

---

# 2. Problem Statement

An ML detection alone is not an investigation.

A detection tells the system that a probable oil spill exists, but operational users need a persistent case through which they can:

- track the incident,
- review the detection,
- run additional analysis,
- attach evidence,
- monitor processing,
- record analyst decisions,
- and eventually identify probable responsible vessels.

Without an investigation entity, downstream services will become loosely connected and difficult to manage.

---

# 3. Goals

## 3.1 Primary Goals

- Create a persistent investigation entity.
- Associate an investigation with a detected spill.
- Maintain investigation lifecycle/status.
- Provide REST APIs for investigation management.
- Provide a chronological investigation timeline.
- Support future linkage to drift, AIS and attribution services.
- Maintain referential integrity with existing domain entities.
- Provide proper validation and error handling.
- Make the feature usable by the existing frontend/dashboard.

## 3.2 Non-Goals

The following are explicitly outside this feature:

- ML model development.
- Satellite image ingestion.
- Drift simulation.
- Hindcasting calculations.
- AIS data acquisition.
- AIS-spill correlation.
- Vessel attribution algorithm.
- User authentication implementation if authentication infrastructure is not already available.
- Final PDF/report generation.

These will consume the investigation created by this feature.

---

# 4. User Story

### Primary user

Maritime/environmental analyst investigating a suspected oil spill.

### User story

> As an analyst, I want to create and manage an investigation around a detected oil spill so that all subsequent analysis and evidence can be associated with one case.

### Acceptance scenario

```text
Given an ML detection exists
When the analyst creates an investigation
Then the backend creates a persistent investigation
And associates it with the detection
And returns an investigation ID
And the investigation can be retrieved later
And downstream services can reference that investigation ID.
```

---

# 5. Investigation Lifecycle

Use an explicit lifecycle.

Recommended states:

```text
OPEN
  ↓
ANALYZING
  ↓
REVIEW
  ↓
RESOLVED
```

Alternative transition for invalid/false detections:

```text
OPEN → DISMISSED
ANALYZING → DISMISSED
REVIEW → DISMISSED
```

### State definitions

| Status | Meaning |
|---|---|
| `OPEN` | Investigation created but detailed analysis has not started |
| `ANALYZING` | One or more analytical workflows are running |
| `REVIEW` | Automated analysis is available and awaiting/undergoing analyst review |
| `RESOLVED` | Investigation has been concluded |
| `DISMISSED` | Investigation determined not to require further action |

The backend must validate state transitions rather than allowing arbitrary status changes.

---

# 6. System Architecture

```text
                    ┌─────────────────────┐
                    │      Frontend       │
                    └──────────┬──────────┘
                               │ REST
                               ▼
                    ┌─────────────────────┐
                    │ Investigation API   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Investigation       │
                    │ Service             │
                    └──────────┬──────────┘
                               │
                 ┌─────────────┼─────────────┐
                 ▼             ▼             ▼
          ┌───────────┐ ┌───────────┐ ┌────────────┐
          │ Detection │ │ Timeline  │ │ Future     │
          │ Service   │ │ Service   │ │ Services   │
          └───────────┘ └───────────┘ └─────┬──────┘
                                             │
                                  ┌──────────┼──────────┐
                                  ▼          ▼          ▼
                               Hindcast     AIS     Attribution
```

The implementation should follow the existing backend architecture instead of introducing a separate microservice.

For MVP, use the existing backend application as a modular monolith.

---

# 7. Data Model

## 7.1 Investigation

Recommended fields:

| Field | Type | Required | Description |
|---|---|---:|---|
| `id` | UUID | Yes | Primary identifier |
| `detection_id` | UUID | Yes | Source spill detection |
| `title` | String | Yes | Human-readable investigation name |
| `status` | Enum | Yes | Investigation lifecycle state |
| `priority` | Enum | Yes | Investigation priority |
| `description` | Text | No | Analyst description |
| `created_at` | DateTime | Yes | Creation timestamp |
| `updated_at` | DateTime | Yes | Last modification timestamp |
| `closed_at` | DateTime | No | Resolution timestamp |
| `created_by` | UUID/String | No* | User creating investigation |

`created_by` should only be implemented if the current authentication/user model supports it.

## 7.2 Priority

Recommended values:

```text
LOW
MEDIUM
HIGH
CRITICAL
```

---

# 8. Relationships

The investigation should have a clear parent/child relationship with the detection.

```text
SlickDetection
      │
      │ 1
      │
      │
      ▼
Investigation
      │
      ├── 1:N InvestigationEvents
      │
      ├── 1:N DriftResults       [future]
      │
      ├── 1:N AISTracks          [future]
      │
      ├── 1:N AttributionScores  [future]
      │
      └── 1:N Evidence           [future]
```

### Important constraint

An investigation must reference an existing valid detection.

The API must reject:

```text
detection_id = non-existent UUID
```

with a `404 Not Found` or appropriate domain error.

---

# 9. Investigation Timeline

The timeline is an important MVP capability because it makes the investigation auditable.

Example:

```text
2026-08-30 10:30
Investigation created

2026-08-30 10:31
ML detection confirmed

2026-08-30 10:35
Analysis started

2026-08-30 10:42
Investigation moved to REVIEW
```

## InvestigationEvent

Recommended fields:

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Event identifier |
| `investigation_id` | UUID | Parent investigation |
| `event_type` | Enum/String | Event classification |
| `message` | Text | Human-readable description |
| `metadata` | JSON | Optional structured data |
| `created_at` | DateTime | Event timestamp |
| `created_by` | UUID/String | Optional actor |

Example event types:

```text
INVESTIGATION_CREATED
STATUS_CHANGED
ANALYSIS_STARTED
ANALYSIS_COMPLETED
ML_DETECTION_CONFIRMED
ML_DETECTION_REJECTED
NOTE_ADDED
INVESTIGATION_RESOLVED
INVESTIGATION_DISMISSED
```

Future services should be able to append their own events.

---

# 10. API Requirements

Base path:

```text
/api/v1/investigations
```

## 10.1 Create Investigation

```http
POST /api/v1/investigations
```

### Request

```json
{
  "detection_id": "uuid",
  "title": "Suspected Oil Spill — Arabian Sea",
  "description": "Investigation initiated from satellite detection",
  "priority": "HIGH"
}
```

### Response — `201 Created`

```json
{
  "id": "uuid",
  "detection_id": "uuid",
  "title": "Suspected Oil Spill — Arabian Sea",
  "description": "Investigation initiated from satellite detection",
  "status": "OPEN",
  "priority": "HIGH",
  "created_at": "2026-08-30T10:30:00Z",
  "updated_at": "2026-08-30T10:30:00Z"
}
```

### Validation

Reject when:

- `detection_id` is missing.
- Detection does not exist.
- Required fields are invalid.
- Priority/status contains unsupported values.
- Business rules prohibit duplicate investigations for the same detection.

If duplicate investigations are not permitted, return:

```http
409 Conflict
```

---

# 11. Get Investigation

```http
GET /api/v1/investigations/{investigation_id}
```

### Response

```json
{
  "id": "uuid",
  "detection_id": "uuid",
  "title": "Suspected Oil Spill — Arabian Sea",
  "status": "ANALYZING",
  "priority": "HIGH",
  "description": "...",
  "created_at": "...",
  "updated_at": "...",
  "closed_at": null
}
```

The endpoint should return the investigation's current state.

Do not make this endpoint responsible for executing expensive ML, AIS or drift operations.

---

# 12. List Investigations

```http
GET /api/v1/investigations
```

Support pagination.

Example:

```http
GET /api/v1/investigations?page=1&page_size=20
```

Recommended filters:

```text
status
priority
detection_id
created_from
created_to
```

Example:

```http
GET /api/v1/investigations?status=ANALYZING&priority=HIGH
```

### Response

```json
{
  "items": [
    {
      "id": "uuid",
      "title": "Suspected Oil Spill — Arabian Sea",
      "status": "ANALYZING",
      "priority": "HIGH",
      "created_at": "..."
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 1
}
```

---

# 13. Update Investigation

```http
PATCH /api/v1/investigations/{investigation_id}
```

### Request

```json
{
  "title": "Updated Investigation Title",
  "description": "Updated analyst notes",
  "priority": "CRITICAL"
}
```

Status updates may either be handled through this endpoint or through a dedicated transition endpoint.

Preferred dedicated endpoint:

```http
PATCH /api/v1/investigations/{investigation_id}/status
```

### Status request

```json
{
  "status": "REVIEW"
}
```

The service must validate the transition.

Example:

```text
OPEN → ANALYZING       ✅
ANALYZING → REVIEW     ✅
REVIEW → RESOLVED      ✅

OPEN → RESOLVED        ⚠️
```

The exact transition policy should be encoded centrally in the domain/service layer.

---

# 14. Investigation Timeline API

```http
GET /api/v1/investigations/{investigation_id}/timeline
```

### Response

```json
{
  "investigation_id": "uuid",
  "events": [
    {
      "id": "uuid",
      "event_type": "INVESTIGATION_CREATED",
      "message": "Investigation created",
      "metadata": {},
      "created_at": "2026-08-30T10:30:00Z"
    },
    {
      "id": "uuid",
      "event_type": "STATUS_CHANGED",
      "message": "Status changed from OPEN to ANALYZING",
      "metadata": {
        "from": "OPEN",
        "to": "ANALYZING"
      },
      "created_at": "2026-08-30T10:35:00Z"
    }
  ]
}
```

Timeline ordering:

```text
created_at DESC
```

or support an explicit `order` parameter if required by the frontend.

---

# 15. Detection Association

When creating an investigation:

```text
POST /investigations
        │
        ▼
Validate detection_id
        │
        ▼
Load SlickDetection
        │
        ▼
Create Investigation
        │
        ▼
Create INVESTIGATION_CREATED event
        │
        ▼
Return investigation
```

The detection should remain the source ML result.

The investigation should not duplicate all detection data.

For example, avoid copying:

```text
confidence
geometry
model_version
area
```

into the investigation unless there is a specific business requirement.

Instead:

```text
Investigation
     │
     └── detection_id
              │
              ▼
        SlickDetection
```

This prevents data divergence.

---

# 16. API Error Handling

Use consistent HTTP status codes.

| HTTP | Meaning |
|---:|---|
| `200` | Successful read/update |
| `201` | Investigation created |
| `400` | Invalid request |
| `404` | Investigation/detection not found |
| `409` | Conflict/invalid duplicate state |
| `422` | Validation error, depending on existing API convention |
| `500` | Unexpected server error |

Recommended error format:

```json
{
  "error": {
    "code": "INVESTIGATION_NOT_FOUND",
    "message": "Investigation does not exist",
    "details": {}
  }
}
```

Follow the existing project's error response conventions if already defined.

---

# 17. Validation Requirements

Validate at the API/schema boundary and enforce business rules in the service/domain layer.

### UUID validation

```text
detection_id
investigation_id
```

must be valid UUIDs if UUIDs are used by the existing project.

### String validation

Prevent:

- empty titles,
- excessive title length,
- invalid status strings,
- invalid priority values.

### Status validation

Do not permit arbitrary lifecycle transitions.

### Foreign key validation

An investigation cannot reference a non-existent detection.

---

# 18. Transactional Requirements

Creation of an investigation and its initial timeline event should occur atomically.

```text
BEGIN TRANSACTION

Create Investigation
       +
Create INVESTIGATION_CREATED event

COMMIT
```

If either operation fails:

```text
ROLLBACK
```

The system must not create an investigation without its initial event.

---

# 19. Future Integration Contract

The investigation ID will become the common reference for downstream features.

### Drift

```json
{
  "investigation_id": "uuid"
}
```

### AIS

```json
{
  "investigation_id": "uuid"
}
```

### Attribution

```json
{
  "investigation_id": "uuid"
}
```

This allows the eventual workflow to be:

```text
Investigation
      │
      ├── Run Hindcast
      │
      ├── Retrieve AIS
      │
      ├── Correlate vessels
      │
      └── Rank candidates
```

---

# 20. Frontend Integration

The frontend should be able to display an investigation page containing:

```text
┌──────────────────────────────────────────┐
│ Investigation                            │
│ Suspected Oil Spill — Arabian Sea       │
│                                          │
│ Status: ANALYZING                        │
│ Priority: HIGH                           │
│                                          │
│ Detection                                │
│ Confidence: 94%                          │
│ Area: 12.43 km²                          │
│                                          │
│ ──────────────────────────────────────── │
│ Timeline                                 │
│                                          │
│ ● Investigation created                 │
│ ● ML detection confirmed                │
│ ● Analysis started                      │
│                                          │
│ ──────────────────────────────────────── │
│ Future Analysis                          │
│                                          │
│ [ Run Hindcast ]                         │
│ [ Analyze AIS ]                          │
└──────────────────────────────────────────┘
```

The frontend should use the investigation ID rather than trying to reconstruct the investigation from individual detection records.

---

# 21. Security Requirements

The feature must follow the security mechanisms already established by the backend.

Requirements:

- Validate all request bodies.
- Validate UUID/path parameters.
- Never construct raw SQL using user input.
- Use ORM/query parameterization.
- Apply existing authentication middleware.
- Apply authorization rules if user/role infrastructure exists.
- Do not expose internal database exceptions.
- Do not expose sensitive infrastructure information in API errors.
- Apply existing CORS policy.
- Apply existing rate limiting if configured globally.

---

# 22. Performance Requirements

For normal CRUD operations:

| Operation | Target |
|---|---:|
| Create investigation | < 500 ms |
| Get investigation | < 300 ms |
| List investigations | < 500 ms |
| Update investigation | < 300 ms |
| Get timeline | < 500 ms |

These are engineering targets for normal database-backed requests, not guaranteed production SLAs.

Timeline queries must use indexes where appropriate.

Recommended indexes:

```text
investigation.id
investigation.detection_id
investigation.status
investigation.created_at

investigation_event.investigation_id
investigation_event.created_at
```

---

# 23. Testing Requirements

## 23.1 Unit Tests

Test:

- investigation creation,
- invalid detection ID,
- duplicate investigation handling,
- status transition rules,
- priority validation,
- update behavior,
- timeline event creation.

Example:

```text
test_create_investigation
test_create_investigation_invalid_detection
test_create_duplicate_investigation
test_valid_status_transition
test_invalid_status_transition
test_update_investigation
test_close_investigation
```

## 23.2 Integration Tests

Test the complete API/database interaction:

```text
POST investigation
        ↓
Database record
        ↓
Timeline event
        ↓
GET investigation
        ↓
GET timeline
```

## 23.3 API Tests

Verify:

- `201` creation,
- `200` retrieval,
- `404` missing investigation,
- `404` missing detection,
- validation errors,
- pagination,
- filtering,
- invalid status transitions.

---

# 24. Observability

Every investigation operation should generate useful structured logs.

Example:

```json
{
  "event": "investigation_created",
  "investigation_id": "uuid",
  "detection_id": "uuid",
  "status": "OPEN",
  "timestamp": "..."
}
```

Status transitions:

```json
{
  "event": "investigation_status_changed",
  "investigation_id": "uuid",
  "from": "OPEN",
  "to": "ANALYZING",
  "timestamp": "..."
}
```

Never log sensitive credentials or authentication tokens.

---

# 25. Implementation Structure

Follow the repository's existing structure.

Recommended conceptual structure:

```text
backend/
└── app/
    ├── api/
    │   └── v1/
    │       └── investigations.py
    │
    ├── models/
    │   ├── investigation.py
    │   └── investigation_event.py
    │
    ├── schemas/
    │   └── investigation.py
    │
    ├── services/
    │   └── investigation_service.py
    │
    └── repositories/
        └── investigation_repository.py
```

Do not create these directories if the repository already follows another pattern. Match the existing architecture.

---

# 26. Database Migration

Create a migration for the investigation tables.

Expected tables:

```text
investigations
investigation_events
```

Foreign key:

```text
investigations.detection_id
        ↓
slick_detections.id
```

And:

```text
investigation_events.investigation_id
        ↓
investigations.id
```

Migration requirements:

- forward migration,
- rollback/down migration if the project's migration system supports it,
- indexes,
- foreign keys,
- appropriate constraints.

---

# 27. Acceptance Criteria

## AC-01 — Create

**Given** a valid detection exists  
**When** the client sends `POST /api/v1/investigations`  
**Then** a new investigation is created and a `201` response is returned.

## AC-02 — Detection association

**Given** an investigation is created  
**Then** it must reference the requested detection.

## AC-03 — Invalid detection

**Given** the detection does not exist  
**When** an investigation is created  
**Then** the API must reject the request.

## AC-04 — Timeline

**Given** an investigation is created  
**Then** an `INVESTIGATION_CREATED` event must exist.

## AC-05 — Retrieval

**Given** a valid investigation ID  
**When** `GET /investigations/{id}` is called  
**Then** the investigation is returned.

## AC-06 — Listing

**Given** multiple investigations exist  
**When** the list endpoint is called  
**Then** paginated results are returned.

## AC-07 — Filtering

**Given** investigations with different statuses/priorities  
**When** filters are supplied  
**Then** only matching investigations are returned.

## AC-08 — Update

**Given** an existing investigation  
**When** valid metadata is updated  
**Then** the updated data is persisted.

## AC-09 — Status transition

**Given** an investigation in a valid state  
**When** a valid transition is requested  
**Then** the transition succeeds and an event is recorded.

## AC-10 — Invalid transition

**Given** an invalid lifecycle transition  
**When** the transition is requested  
**Then** the API rejects it without modifying the investigation.

## AC-11 — Transactionality

**Given** investigation creation succeeds  
**Then** its initial timeline event must also exist.

## AC-12 — Downstream readiness

**Given** an investigation exists  
**Then** its ID can be used by future drift, AIS and attribution services.

---

# 28. Definition of Done

The feature is considered complete only when:

- [ ] Investigation model implemented.
- [ ] Investigation event model implemented.
- [ ] Database migration created.
- [ ] Foreign keys configured.
- [ ] Required indexes created.
- [ ] Create API implemented.
- [ ] Get API implemented.
- [ ] List API implemented.
- [ ] Filtering implemented.
- [ ] Update API implemented.
- [ ] Status transition handling implemented.
- [ ] Timeline API implemented.
- [ ] Validation implemented.
- [ ] Error handling follows existing backend conventions.
- [ ] Authentication/authorization integrated with existing infrastructure where applicable.
- [ ] Unit tests implemented.
- [ ] Integration tests implemented.
- [ ] API tests implemented.
- [ ] Structured logging added.
- [ ] Existing tests still pass.
- [ ] API documentation/OpenAPI updated.
- [ ] Frontend can consume the endpoints.
- [ ] No drift/AIS/attribution logic is incorrectly embedded into this feature.

---

# 29. Recommended Development Order

Implement in this exact order:

```text
1. Inspect existing detection/domain models
                ↓
2. Design Investigation model
                ↓
3. Design InvestigationEvent model
                ↓
4. Create database migration
                ↓
5. Implement schemas
                ↓
6. Implement service/domain logic
                ↓
7. Implement POST endpoint
                ↓
8. Implement GET endpoint
                ↓
9. Implement LIST + filters
                ↓
10. Implement PATCH/update
                ↓
11. Implement status transitions
                ↓
12. Implement timeline
                ↓
13. Add unit tests
                ↓
14. Add integration/API tests
                ↓
15. Update OpenAPI documentation
                ↓
16. Test against frontend
```

---

# 30. MVP End-to-End Flow After This Feature

Once Investigation Management is complete, the backend MVP should support:

```text
┌─────────────────────┐
│ Satellite Image     │
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│ Satellite Ingestion │
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│ Analysis Job        │
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│ ML Detection        │
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│ Spill Detection     │
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│ Investigation       │
└──────────┬──────────┘
           ↓
    ┌──────┴──────┐
    ↓             ↓
Hindcast        AIS
    ↓             ↓
    └──────┬──────┘
           ↓
    Vessel Correlation
           ↓
    Vessel Attribution
```

Investigation Management therefore acts as the **bridge between detection and forensic attribution**.

---

# 31. Future Extensions

After the MVP, the investigation system can be extended with:

- analyst assignment,
- role-based permissions,
- comments/notes,
- evidence attachments,
- investigation tags,
- severity scoring,
- automated alerts,
- investigation export,
- report generation,
- audit history,
- workflow approvals,
- collaboration,
- notification/webhook events.

These should not block the MVP implementation.

---

# 32. Final Engineering Principle

The investigation entity should remain **small, stable and extensible**.

Do not turn it into a container for every piece of oil-spill data.

The correct architecture is:

```text
Investigation
    │
    ├── Detection
    ├── Timeline
    ├── Drift Results
    ├── AIS Data
    ├── Attribution
    └── Evidence
```

rather than:

```text
Investigation
    └── every field from every service
```

The Investigation ID is the stable correlation key across the entire forensic workflow.

**Primary MVP outcome:**

> A detected oil spill can be converted into a persistent investigation that can be tracked, reviewed, and extended with hindcast, AIS correlation, vessel attribution and evidence workflows.
