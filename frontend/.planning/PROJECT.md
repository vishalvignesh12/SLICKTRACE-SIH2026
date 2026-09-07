# National Marine Oil Spill Monitoring System

## What This Is

A mission-critical maritime surveillance and forensic intelligence web application designed for national environmental oversight, oil spill detection, and vessel attribution. The platform transforms satellite SAR observations and AIS tracking data into actionable geospatial investigations and evidentiary dossiers for maritime authorities.

## Core Value

Enable maritime surveillance officers to rapidly detect satellite-observed oil slicks, pinpoint candidate polluting vessels via spatial-temporal AIS attribution with confidence scoring, and compile legally defensible incident dossiers.

## Requirements

### Validated

- ✓ [High-fidelity UI prototype across 9 core operational screens] — existing (static HTML mockups)
- ✓ [Standardized maritime oversight design system & design tokens] — existing (`maritime_oversight_response/DESIGN.md`)
- ✓ [Visual layout and styling for incident INC-2026-001 (Bay of Bengal)] — existing

### Active

- [ ] **Modern React Architecture**: Convert static HTML mockups into a clean, modular React application (SPA) with shared layouts, design tokens, and components.
- [ ] **Interactive GIS Forensics Workspace**: Real interactive mapping engine (Leaflet/Mapbox) rendering satellite detection overlays, oil slick polygons, coordinate grids, and interactive layer toggles.
- [ ] **AIS Vessel Attribution & Trajectory Engine**: Visual spatial-temporal vessel tracks, nearest-approach calculations, drift modeling, and probabilistic suspect ranking with confidence breakdown.
- [ ] **Live Operations Dashboard & Detection Registry**: Dynamic operational metrics, filterable oil spill registry, severity categorization, and status workflows (New, Investigating, Attributed, Closed).
- [ ] **Forensic Profiling & Legal Evidence Dossier**: Deep vessel dossier inspection (MMSI, IMO, flag history, voyage logs), verifiable audit trails, and official PDF/report export capabilities.
- [ ] **Mock & Extensible API Integration Layer**: Safe, typed service layer connecting components to mock backend data, ready for seamless switchover to live backend endpoints.

### Out of Scope

- Direct satellite downlink processing in frontend — processed downstream by backend services
- Full real-time radar hardware interfacing — ingested via standard AIS/SAR APIs
- Mobile native application — web-first responsive design targeting desktop operations centers

## Context

- Existing prototype consists of 9 isolated HTML files utilizing Tailwind CDN and Google Fonts.
- Design system follows **Corporate Modernism / Information Density** with deep navy (`#002147`), muted teal (`#096969`), and semantic alert colors.
- The project is equipped with domain skills for React frontend engineering, GIS mapping, technical data visualization, API integration, and security.

## Constraints

- **Tech Stack**: React + Vanilla CSS / Tailwind (consistent design system), HTML5, JavaScript
- **Performance**: Instantaneous client-side filtering and smooth pan/zoom on GIS map layers
- **Security**: Strict isolation of mock credentials, sanitized inputs, and defensible audit log trails

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| React SPA Architecture | Replaces duplicated HTML files and shared config drift with reusable component tree | — Pending |
| Leaflet.js for GIS Mapping | Lightweight, highly extensible, excellent polygon & GeoJSON support for maritime overlays | — Pending |
| Vertical MVP Phased Delivery | Fast operational capability at each increment (Setup → Core Layout → GIS → Attribution → Dossier) | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

## Technical Architecture Improvements & Technical Debt Reduction

Based on codebase analysis conducted on 2026-09-02, the following technical improvements are recommended to enhance maintainability, scalability, and developer experience while preserving the excellent domain-specific UI/UX.

### Current State Assessment

**Strengths:**
- Modular component organization with clear separation of concerns
- Consistent maritime-themed design system implemented via Tailwind CSS
- Effective state management using Context API for global navigation/auth
- Robust service layer with proper API abstraction and mock fallback
- Sophisticated GIS integration with Leaflet and custom naval tactical styling
- Domain-appropriate UI components designed for maritime surveillance workflows

### Recommended Improvements

#### Phase 1: Foundation Improvements (Immediate)

**1.1 Create Shared Utilities**
- Create `frontend/src/utils/` directory with:
  - `dateHelpers.js` - consistent date formatting across components
  - `coordinateHelpers.js` - lat/lng formatting, distance calculations
  - `formatters.js` - number formatting, currency, unit conversions
  - `constants.js` - maritime-specific constants (conversion factors, status codes)

**1.2 Implement Custom Hooks**
- Create `frontend/src/hooks/` directory with:
  - `useApiData.js` - encapsulates common API fetching pattern with loading/error states
  - `useIncidentContext.js` - combines navigation context with incident-specific data
  - `useVesselTracking.js` - handles AIS trajectory data processing
  - `useResponsiveListener.js` - handles resize/orientation changes

**1.3 Refactor Large Components**
Break down monolithic views into smaller, focused components:

**DashboardView.jsx** (415 lines) should be split into:
- `DashboardHeader.jsx` - title, navigation buttons
- `MetricsGrid.jsx` - KPI metric cards layout
- `PrimaryIncidentCard.jsx` - incident banner and details
- `SurveillanceSectors.jsx` - regional surveillance display
- `AlertsFeed.jsx` - priority alerts component

**AttributionView.jsx** (161 lines) should be split into:
- `AttributionHeader.jsx` - incident info and navigation
- `VerdictBanner.jsx` - primary suspect hero section
- `FactorAnalysisPanel.jsx` - FactorBreakdown relocation
- `CandidateList.jsx` - vessel ranking with selection handling

#### Phase 2: Developer Experience (Short-term)

**2.1 TypeScript Migration Strategy**
- Begin with new components using TypeScript
- Convert utility files and hooks first
- Gradually migrate presentational components
- Maintain JavaScript for complex logic components initially

**2.2 Testing Infrastructure**
- Implement Jest and React Testing Library for unit tests
- Add Cypress for end-to-end critical user flows
- Create test mocks for API service layer
- Establish 80%+ coverage target for new components

**2.3 Documentation and Storybook**
- Create Storybook for all reusable components (Button, MetricCard, StatusChip, etc.)
- Document props, usage examples, and accessibility considerations
- Generate automated documentation from JSDoc/PropTypes

**2.4 Code Quality Tooling**
- Configure ESLint with React and accessibility plugins
- Add Prettier for consistent formatting
- Implement husky hooks for pre-commit linting
- Add bundle analyzer to Vite config

#### Phase 3: Advanced Features (Medium-term)

**3.1 Performance Optimizations**
- Implement React.memo for expensive components
- Use useMemo/useCallback for expensive computations
- Implement virtual scrolling for large datasets (vessel lists, AIS trajectories)
- Add skeleton loading states for better perceived performance
- Implement code splitting for route-based components

**3.2 Offline Capabilities**
- Implement service worker for offline map tiles caching
- Add IndexedDB persistence for critical data (recent incidents, vessel profiles)
- Add background sync for audit trail updates when connectivity restored

**3.3 Accessibility Enhancements**
- Ensure WCAG 2.1 AA compliance
- Add keyboard navigation support for all interactive components
- Implement screen reader friendly labels and descriptions
- Add high contrast mode toggle

**3.4 Internationalization**
- Implement i18next or similar for multi-language support
- Start with English and key maritime languages (Spanish, French, Arabic)
- Prepare date/number formatting for locale sensitivity

### Implementation Roadmap

**Sprint 1 (Week 1-2): Foundation**
- [ ] Create utils/hooks directory structure
- [ ] Implement date and coordinate helper utilities
- [ ] Create useApiData custom hook
- [ ] Refactor DashboardView into smaller components
- [ ] Add ESLint and Prettier configuration

**Sprint 2 (Week 3-4): Component Library**
- [ ] Split AttributionView into focused components
- [ ] Create Storybook for common UI components
- [ ] Begin TypeScript conversion of utilities
- [ ] Implement basic unit testing framework
- [ ] Add responsive listener hook

**Sprint 3 (Week 5-6): State & Performance**
- [ ] Implement Redux Toolkit for complex state (optional, based on need)
- [ ] Add React.memo to expensive components
- [ ] Create vessel tracking hook
- [ ] Add virtual scrolling to candidate lists
- [ ] Implement skeleton loading states

**Sprint 4 (Week 7-8): Quality & Testing**
- [ ] Achieve 80% test coverage on new components
- [ ] Complete Storybook documentation
- [ ] Implement accessibility audits and fixes
- [ ] Add bundle analysis and optimization
- [ ] Prepare TypeScript migration plan for remaining components

### Success Metrics

**Technical Metrics:**
- Reduce average component file size by 40%
- Increase test coverage from 0% to 80%+ on new/refactored components
- Decrease bundle size by 25% through code splitting
- Achieve Lighthouse performance score >90
- Zero critical accessibility violations

**Developer Experience Metrics:**
- Decrease average PR review time by 30%
- Reduce bug rate related to prop-types/state by 50%
- Decrease onboarding time for new developers by 40%
- Increase developer satisfaction scores (survey-based)

**Domain-Specific Metrics:**
- Maintain or improve maritime workflow completion times
- Preserve all existing functionality and data accuracy
- Ensure zero regression in critical alerting pathways
- Maintain compatibility with existing backend API contracts

---
*Last updated: 2026-09-02 after technical architecture analysis*
