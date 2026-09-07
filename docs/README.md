# National Marine Oil Spill Monitoring System

> **Mission-Critical Maritime Surveillance & Forensic Intelligence Platform**
> 
> Transforming satellite SAR observations and AIS tracking data into actionable geospatial investigations and evidentiary dossiers for maritime authorities.

## Table of Contents

- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Getting Started](#getting-started)
- [Development Guide](#development-guide)
- [API Reference](#api-reference)
- [Deployment](#deployment)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Contributing](#contributing)

## Overview

The National Marine Oil Spill Monitoring System enables maritime surveillance officers to:
- Rapidly detect satellite-observed oil slicks
- Pinpoint candidate polluting vessels via spatial-temporal AIS attribution with confidence scoring
- Compile legally defensible incident dossiers with cryptographic chain of custody

The platform transforms raw satellite and AIS data through a 5-stage pipeline:
**Satellite Imagery → Oil Slick Detection → Characterization → Drift Hindcast → Probable Origin/Time Window → AIS Reconstruction → Spatial+Temporal+Trajectory Correlation → AIS Anomaly Detection → Ranked Candidate Vessels → Evidence Compaction**

## System Architecture

### High-Level Design

The system follows a **3-layer architecture** to separate concerns and ensure reliability:

1. **Directive Layer** - What to do (PRDs, AGENTS.md)
   - Defines goals, API contracts, acceptance criteria
   - Authoritative instructions until changed

2. **Orchestration Layer** - Decision making (Developer/Router)
   - Reads directives, routes API → Service → Integration Adapter
   - Handles errors per standard envelope
   - Never skips layers or takes shortcuts

3. **Execution Layer** - Deterministic Python (Services, Integrations, Scripts)
   - Handles PostGIS queries, drift simulation, AIS correlation math
   - Reliable, testable, fast execution
   - Where complexity lives to keep orchestration layer simple

### Key Architectural Principles

- **Adapter Boundary Mandatory**: API Route → Service → Integration Adapter → External Provider
- **No Naive Nearest-Vessel Matching**: Always uses drift hindcast → probable origin → PostGIS AIS search → multi-factor correlation
- **Expose Uncertainty**: Every intelligence output includes confidence fields (`confidence`, `age_confidence`, `origin_confidence`)
- **AIS Gaps Are Expected**: Dark-vessel/no-AIS-match returns actionable investigation state, not error
- **Backend Geospatial Filtering**: PostGIS, never sending unrestricted datasets to frontend
- **Server-Side RBAC**: Frontend role checks are UX only; every protected route enforces `analyst`/`admin` server-side

### Technology Stack

#### Frontend (React SPA)
- **Framework**: React 18 + Vite
- **Styling**: Tailwind CSS (Maritime Design System)
- **Mapping**: Leaflet.js with custom naval tactical styling
- **State Management**: React Context API
- **GIS Features**: Interactive polygons, vessel trajectories, temporal playback, layer toggling

#### Backend (FastAPI Monolith)
- **Framework**: FastAPI + Python 3.12+
- **Database**: PostgreSQL 16 + PostGIS + SQLAlchemy 2 + GeoAlchemy2
- **Geospatial**: Shapely, GeoPandas, PyProj, OpenDrift/GNOME
- **ML**: Ultralytics YOLO, OpenCV for spill detection
- **Auth**: JWT, Argon2id password hashing
- **Validation**: Pydantic v2 request/response contracts
- **Testing**: Pytest with asyncio support

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ and npm
- Python 3.12+
- PostgreSQL with PostGIS extension (for local dev without Docker)

### Quick Start with Docker Compose

```bash
# Clone repository
git clone https://github.com/vishalvignesh12/OIL_SPILL_PROJECT_SIH_2026-PRODUCT-NAME-SHOULD-BE-SELECTED-.git
cd oil-spill-platform

# Backend setup
cd backend
cp .env.example .env
docker compose up --build

# In another terminal, seed initial data
docker compose exec api python scripts/seed_fixtures.py

# Frontend setup  
cd ../frontend
npm install
cp .env.example .env.local
# Edit .env.local with your configuration
npm run dev
```

The system will be available at:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs (Swagger UI)
- **Alternative API Docs**: http://localhost:8000/redoc (ReDoc)

### Local Development Setup

#### Backend (Virtualenv)
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"

# Ensure PostgreSQL with PostGIS is running
alembic upgrade head
uvicorn app.main:app --reload
```

#### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Development Guide

### Backend Development

#### Service Layer Architecture
All business logic lives in `backend/app/services/` following the adapter pattern:
- **Services**: Orchestration layer (`attribution_service.py`, `drift_service.py`, etc.)
- **Integrations**: Third-party calls (`opendrift_adapter.py`, `gfw_adapter.py`, `ml_provider.py`)
- **Core**: Cross-cutting concerns (`config.py`, `database.py`, `security.py`, `logging.py`)

#### Key Principles
1. **Never call integrations directly from API routes** - always go through services
2. **External calls go through integrations + services** - never from `api/v1/` directly
3. **Geospatial writes use SRID 4326** (or documented exceptions)
4. **Update PRDs when you learn something new** - they're living documents
5. **Handle AIS gaps as data, not failures** - return actionable investigation states

#### Common Backend Tasks
See [Backend How-To Guides](./backend-how-tos.md) for:
- Adding new API endpoints
- Creating new service adapters
- Mocking external providers for development
- Running and writing tests
- Database migrations

### Frontend Development

#### Component Architecture
- **Pages**: View-level components in `src/components/views/` (DashboardView, GISWorkspaceView, etc.)
- **Common Components**: Reusable UI in `src/components/common/` (Header, SideNavBar, MetricCard, etc.)
- **Context**: Global state management in `src/context/` (NavigationContext)
- **Services**: API service layer in `src/services/` with mock fallback
- **Styling**: Tailwind CSS with maritime design tokens

#### Key Conventions
- **Fixed Sidebar Navigation**: Used on all interior pages (`ml-[260px]` margin)
- **Responsive Design**: Works on operational desktop monitors
- **Maritime Design System**: Deep Navy (`#002147`), Muted Teal (`#096969`), Inter typography
- **Component Modularity**: Break large views into focused components (<200 lines ideal)

#### Common Frontend Tasks
See [Frontend How-To Guides](./frontend-how-tos.md) for:
- Adding new views and routes
- Creating reusable components
- Implementing GIS features with Leaflet
- State management patterns
- Styling and theming guidelines

## API Reference

The backend provides a RESTful API at `/api/v1` with the following endpoints:

### Authentication
- `POST /api/v1/auth/login` - Authenticate and get JWT token
- `GET /api/v1/auth/me` - Get current user profile

### Incidents & Detections
- `GET /api/v1/incidents` - List oil spill incidents
- `GET /api/v1/incidents/{id}` - Get incident details
- `GET /api/v1/detections` - List detections with filtering
- `POST /api/v1/detections/analyze` - Analyze satellite scene for spills

### Vessels & AIS
- `GET /api/v1/vessels` - List monitored vessels
- `GET /api/v1/vessels/{id}` - Get vessel forensic profile
- `GET /api/v1/vessels/{id}/track` - Get historical AIS track

### Attribution & Drift
- `POST /api/v1/attribution/score` - Calculate vessel attribution scores
- `POST /api/v1/drift/hindcast` - Calculate drift trajectory to origin
- `POST /api/v1/drift/forecast` - Calculate forecast trajectory
- `GET /api/v1/ais/tracks` - Query AIS vessel tracks

### Investigations & Evidence
- `GET /api/v1/investigations/{id}` - Get consolidated investigation
- `GET /api/v1/evidence/{id}` - Get evidence dossier
- `POST /api/v1/evidence/{id}/export` - Export evidence as PDF

### System & Monitoring
- `GET /api/v1/metrics` - Get operational KPI metrics
- `GET /api/v1/alerts` - Get security alerts
- `GET /api/v1/health` - Liveness check
- `GET /api/v1/health/ready` - Readiness check (database connectivity)

See the interactive API documentation at `http://localhost:8000/docs` for detailed request/response schemas.

## Deployment

### Production Deployment Considerations

#### Backend
- Use gunicorn with uvicorn workers for production: `gunicorn -k uvicorn.workers.UvicornWorker app.main:app`
- Configure proper SSL termination at load balancer
- Set environment variables for production secrets (DATABASE_URL, JWT_SECRET, API keys)
- Monitor database connections and pool size
- Enable structured logging to centralized system

#### Frontend
- Build for production: `npm run build`
- Outputs to `/dist` directory
- Deploy to any static hosting service (Netlify, Vercel, AWS S3+CloudFront, etc.)
- Configure SPA routing: all routes should serve `index.html`
- Set appropriate caching headers for assets
- Configure CDN for global distribution

### Environment Variables

Key environment variables in `.env`:
```
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/oil_spill_db

# Security
JWT_SECRET=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30

# API Keys (when moving from fixtures to real providers)
GFW_API_KEY=your-global-fishing-watch-key
CMEMS_USERNAME=your-copernicus-username
CMEMS_PASSWORD=your-copernicus-password
EAR5_USERNAME=your-era5-username
EAR5_PASSWORD=your-era5-password

# ML Provider Settings
ML_PROVIDER=fixture  # or rest for real ML service
ML_SERVICE_URL=https://your-ml-service.com/predict
ML_INFERENCE_TIMEOUT_SECONDS=30

# CORS
CORS_ORIGINS=["https://your-production-domain.com"]
```

## Testing

### Backend Testing
```bash
# Run all tests
cd backend
pytest -v

# Run specific test suites
pytest tests/test_attribution_service.py -v
pytest tests/test_drift_service.py -v
pytest tests/test_dashboard_api.py -v

# Run with coverage
pytest --cov=app tests/
```

### Frontend Testing
```bash
# Run frontend tests (when implemented)
cd frontend
npm test

# Run specific test files
npm test -- src/components/views/__tests__/DashboardView.test.jsx

# Run tests in watch mode during development
npm run test:watch
```

### Testing Philosophy
- **Unit Tests**: Test individual services and components in isolation
- **Integration Tests**: Test API endpoints with test database
- **End-to-End Tests**: Playwright tests for critical user flows (planned)
- **Mock Strategy**: Use fixtures for external providers during testing to avoid consuming paid API credits
- **Coverage Goal**: 80%+ on new/refactored components

## Project Structure

```
oil-spill-platform/
├── backend/                  # FastAPI backend monolith
│   ├── app/                  # Application core
│   │   ├── api/v1/           # API route handlers (thin layer)
│   │   ├── models/           # SQLAlchemy/SQLModel ORM models
│   │   ├── schemas/          # Pydantic request/response contracts
│   │   ├── services/         # Business logic (orchestration seam)
│   │   ├── integrations/     # Third-party API calls (adapters)
│   │   └── core/             # Config, database, security, logging
│   ├── migrations/           # Alembic database migrations
│   ├── scripts/              # Seed/fixture loaders
│   ├── tests/                # Test suite
│   ├── Dockerfile            # Container definition
│   ├── docker-compose.yml    # Multi-service orchestration
│   ├── pyproject.toml        # Dependencies and metadata
│   └── README.md             # Backend-specific documentation
│
├── frontend/                 # React SPA application
│   ├── src/                  # Source code
│   │   ├── components/       # Reusable UI components and views
│   │   │   ├── common/       # Shared components (Header, Button, etc.)
│   │   │   └── views/        # Page-level components (Dashboard, GIS, etc.)
│   │   ├── context/          # React context providers (Navigation, Auth)
│   │   ├── services/         # API service layer with mock fallback
│   │   ├── App.jsx           # Root application component
│   │   └── main.jsx          # Entry point
│   ├── .planning/            # Project planning documents
│   ├── public/               # Static assets
│   ├── index.html            # Entry point HTML
│   ├── package.json          # Dependencies and scripts
│   ├── vite.config.js        # Vite configuration
│   ├── tailwind.config.js    # Tailwind CSS configuration
│   └── README.md             # Frontend-specific documentation
│
├── ML_MODEL/                 # Machine learning models and notebooks
│   ├── notebooks/            # Jupyter notebooks for ML experimentation
│   ├── reports/              # ML experiment reports and visualizations
│   ├── scripts/              # ML training and inference scripts
│   ├── tests/                # ML unit tests
│   └── README.md             # ML-specific documentation
│
├── .planning/                # GSD project planning and documentation
│   ├── PROJECT.md            # Project vision and requirements
│   ├── REQUIREMENTS.md       # Detailed feature requirements
│   ├── ROADMAP.md            # Implementation roadmap and phases
│   ├── STATE.md              # Current project state and progress
│   └── codebase/             # Technical architecture documentation
│
├── Documents/                # Additional PRDs and specifications
│   ├── oil-spill-backend-prd.md
│   ├── oil-spill-frontend-prd.md
│   ├── AI_ML_Oil_Spill_Detection_PRD.md
│   └── SIH PROBLEM STATEMENT ANALYSIS.md
│
├── AGENTS.md                 # Agent instructions (mirrored in CLAUDE.md)
└── README.md                 # This file
```

## Contributing

We welcome contributions to improve the National Marine Oil Spill Monitoring System!

### How to Contribute

1. **Fork the repository** and create your feature branch
2. **Read the planning documents** in `.planning/` to understand the vision
3. **Follow the development guidelines** in this document
4. **Write tests** for new functionality
5. **Ensure all existing tests pass**
6. **Submit a pull request** with a clear description of changes

### Development Workflow

- **Branching**: Use descriptive branch names (`feature/ais-gap-handling`, `fix/attribution-score-calculation`)
- **Commit Messages**: Follow conventional commits format (`feat: add ais gap handling`, `fix: correct attribution scoring`)
- **Pull Requests**: Include screenshots for UI changes, reference related issues
- **Code Review**: All PRs require approval from at least one maintainer

### Code Quality Standards

- **Backend**: Follow PEP 8, use type hints, write descriptive docstrings
- **Frontend**: Use functional components with hooks, follow accessibility guidelines
- **Documentation**: Update documentation alongside code changes
- **Security**: Never hardcode secrets, validate all inputs, use parameterized queries

### Getting Help

- **Documentation**: Refer to this guide and the planning documents in `.planning/`
- **Code Comments**: Look for `// NOTE:`, `// DESIGN:`, `// WHY:` comments in the codebase
- **Planning Documents**: `.planning/PROJECT.md` contains vision and requirements
- **API Docs**: Interactive documentation at `http://localhost:8000/docs`

---

*Last updated: 2026-09-06*
*Generated as part of project documentation initiative*