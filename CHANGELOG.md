# Changelog

All notable changes to this project will be documented in this file.

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
