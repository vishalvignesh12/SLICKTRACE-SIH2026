# National Marine Oil Spill Monitoring System

A mission-critical maritime surveillance and forensic intelligence web application designed for national environmental oversight, oil spill detection, and vessel attribution.

## Overview

This platform transforms satellite SAR observations and AIS tracking data into actionable geospatial investigations and evidentiary dossiers for maritime authorities. The system enables rapid detection of satellite-observed oil slicks, pinpointing of candidate polluting vessels via spatial-temporal-temporal AIS attribution with confidence scoring, and compilation of legally defensible incident dossiers.

## Project Structure

```
oil-spill-platform/
├── frontend/                 # React SPA application
│   ├── src/                  # Source code
│   │   ├── components/       # Reusable UI components
│   │   ├── context/          # React context providers
│   │   ├── services/         # API service layer
│   │   ├── views/            # Page-level components
│   │   └── App.jsx           # Root application component
│   ├── .planning/            # Project planning documents
│   ├── public/               # Static assets
│   ├── index.html            # Entry point HTML
│   ├── package.json          # Dependencies and scripts
│   ├── vite.config.js        # Vite configuration
│   ├── tailwind.config.js    # Tailwind CSS configuration
│   └── postcss.config.js     # PostCSS configuration
└── backend/                  # FastAPI backend (separate repo)
```

## Frontend Architecture

The frontend is built as a modern React 18 Single Page Application (SPA) using Vite for fast development and optimized builds. Key architectural decisions include:

- **State Management**: React Context API for global state (navigation, authentication)
- **Styling**: Tailwind CSS with custom maritime-themed design system
- **GIS Mapping**: Leaflet.js for interactive maritime forensics workspace
- **Data Layer**: Abstracted API service with mock fallback for offline development
- **Component Architecture**: Modular, reusable components with clear separation of concerns

### Current Strengths

- Modular component organization with clear separation of concerns
- Consistent maritime-themed design system implemented via Tailwind CSS
- Effective state management using Context API for global navigation/auth
- Robust service layer with proper API abstraction and mock fallback
- Sophisticated GIS integration with Leaflet and custom naval tactical styling
- Domain-appropriate UI components designed for maritime surveillance workflows

### Planned Improvements

See `.planning/PROJECT.md` for detailed technical architecture improvements and technical debt reduction recommendations, including:

1. **Foundation Improvements**: Shared utilities, custom hooks, component refactoring
2. **Developer Experience**: TypeScript migration, testing infrastructure, Storybook, code quality tooling
3. **Advanced Features**: Performance optimizations, offline capabilities, accessibility enhancements, internationalization

## Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/vishalvignesh12/OIL_SPILL_PROJECT_SIH_2026-PRODUCT-NAME-SHOULD-BE-SELECTED-.git
cd oil-spill-platform/frontend

# Install dependencies
npm install

# Set up environment variables
cp .env.example .env.local
# Edit .env.local with your configuration

# Start development server
npm run dev
```

### Available Scripts

- `npm run dev` - Start development server at http://localhost:3000
- `npm run build` - Build for production
- `npm run preview` - Preview production build

## Core Features

1. **Command & Control Dashboard** - Operational overview with KPI metrics and alert feeds
2. **Detection Registry** - Tabular view of all detected oil slicks with filtering capabilities
3. **GIS Forensics Workspace** - Interactive map with SLAR slick polygons, vessel trajectories, and temporal playback
4. **Vessel Attribution Engine** - Ranked candidate vessels with multi-factor confidence scoring
5. **Vessel Forensic Profiling** - Deep vessel inspection including AIS trajectory, compliance history, and voyage details
6. **Evidence Dossier Generator** - Official legal/compilation reports with chain of custody and cryptographic verification
7. **Security Alerts Management** - Real-time alert monitoring with acknowledgement workflow
8. **System Reports & Configuration** - Administrative console for report generation and system configuration

## Design System

The application implements a maritime-inspired design system with:
- **Primary Colors**: Deep Navy (`#000a1e`), Muted Teal (`#096969`)
- **Semantic Colors**: Error (`#ba1a1a`), Success (teal variants), Warning (amber variants)
- **Typography**: Inter typeface with hierarchical scaling (display, headline, title, body, label)
- **Components**: Reusable UI components (Button, MetricCard, StatusChip, DataTable, etc.)
- **Layout Patterns**: Sidebar navigation, split panels, data grids, cards, and tables

## API Integration

The frontend communicates with a FastAPI backend through a centralized service layer (`src/services/api.js`) that provides:

- Authentication (login/token management)
- Incident and vessel data retrieval
- System metrics and KPI dashboard data
- AIS track and vessel trajectory data
- Vessel attribution scoring
- Oil slick detection and analysis
- Security alerts management
- Geographic layer data (EEZ boundaries, shipping lanes)

The service includes automatic fallback to mock data when the backend is unavailable, enabling offline development and demo capabilities.

## Testing

The project includes:
- End-to-end browser automation tests (Playwright)
- Unit testing framework (Jest + React Testing Library - planned)
- Component documentation and testing (Storybook - planned)

## Deployment

The frontend can be deployed to any static hosting service:
- Build outputs to `/dist` directory
- Configure routing for SPA (all routes to index.html)
- Set appropriate caching headers for assets

## Contributing

Please read `.planning/PROJECT.md` and `.planning/ROADMAP.md` for detailed contribution guidelines and upcoming features.

## License

This project is part of the National Marine Oil Spill Monitoring System initiative.

## Acknowledgments

- Built with React 18, Vite, Tailwind CSS, and Leaflet.js
- Inspired by maritime surveillance and environmental protection systems worldwide
- Dedicated to the professionals working to protect our oceans and marine ecosystems