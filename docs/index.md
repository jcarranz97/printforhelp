# PrintForHelp Documentation

Welcome to the PrintForHelp project documentation.

PrintForHelp is a coordination platform for the 3D printing community to
help people in need. The initial focus is on producing medical splints
(ferulas) for victims of the June 2026 Venezuela earthquake; the
long-term goal is to become a general-purpose hub where the maker
community can match printers to people who need printed parts.

## Project Status

!!! info "Early stage"
    The project is currently in **landing page** stage. Requirements,
    architecture, and feature design will be added here as the project
    grows.

## Planned Features

- **Centros de acopio** — directory of drop-off locations.
- **Print requests** — people in need request specific parts.
- **Print claims** — printers announce what they are printing so the
  community avoids duplicating work.

## Technology Stack

| Component | Technology |
|---|---|
| Backend | FastAPI (Python 3.13) |
| Database | PostgreSQL 15 |
| Frontend | Next.js 15 + React 19 + Tailwind v4 + HeroUI |
| Docs | MkDocs Material |
| Containerization | Docker Compose |
