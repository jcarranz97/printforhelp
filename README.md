# PrintForHelp

A coordination platform for the 3D printing community to help people in
need — starting with medical splints (ferulas) for Venezuela earthquake
relief, and growing into a general-purpose hub for community-driven
3D-printed humanitarian aid.

## What it does (planned)

- **Collection centers** — directory of drop-off locations where
  printers can deliver finished parts so they reach those who need
  them.
- **Print requests** — people in need can request specific parts.
- **Print claims** — printers announce what they are currently printing
  so the community doesn't duplicate work.

## Quick Start

### Prerequisites

- Docker and Docker Compose
- (First run only) `uv` for backend and `npm` for frontend, to generate
  lock files

### First-time setup

```bash
cd backend && uv sync && cd ..
cd frontend && npm install && cd ..
```

### Run with Docker

```bash
docker-compose up --build
```

- **Frontend**: <http://localhost:3001>
- **API**:      <http://localhost:8100>
- **API Docs**: <http://localhost:8100/docs>
- **Docs**:     <http://localhost:2012>

## Tech Stack

- **Backend**: FastAPI (Python 3.13) + SQLAlchemy + PostgreSQL
- **Frontend**: Next.js 15 + React 19 + Tailwind CSS + HeroUI
- **Docs**: MkDocs Material
- **Containerization**: Docker Compose

## License

MIT — see [LICENSE](LICENSE).
