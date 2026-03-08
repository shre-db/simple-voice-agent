# Changelog

All notable changes to this project will be documented in this file.

## [v0.0.3] - 2026-03-08

### Added
- Dockerized runtime for the app with `Dockerfile`.
- `docker-compose.yml` for app + Qdrant orchestration.
- `.dockerignore` for cleaner image builds.
- `scripts/setup.sh` for one-command local setup (start Qdrant, wait, ingest, start app).

### Changed
- Qdrant host/port are now environment-configurable in app and ingestion script.
- README rewritten as a full runbook for Docker setup and Twilio/ngrok webhook wiring.
- `.env.example` now includes `QDRANT_HOST` and `QDRANT_PORT`.

## [v0.0.2] - 2026-03-08

### Added
- Initial `CHANGELOG.md` file for release documentation.

## [v0.0.1] - 2026-03-08

### Added
- Initial project setup with `uv` and Python dependencies.
- Wise FAQ dataset and ingestion flow into Qdrant.
- Retrieval module for FAQ semantic search.
- LLM response generation module using Gemini API.
- Basic retrieval and LLM test scripts.

### Changed
- Twilio voice webhook flow in FastAPI for incoming call handling.
- Twilio `Gather` tuning for improved speech capture in phone-call conditions.

### Fixed
- Wise FAQ source URLs in `data/wise_faq.json`.
