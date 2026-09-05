# Production Readiness: What Still Requires External Work

This repository deliberately does not pretend that integrations, trained models, or agricultural advice are complete when their source material is absent.

## Implemented now

| Capability | Current state |
| --- | --- |
| Desktop application UI | Complete: responsive laptop-first dashboard with no seeded domain records. |
| Authentication and profiles | Complete locally: email/password JWT flow and editable stored profile. |
| Market data interface | Complete: server fetches India OGD/AGMARKNET only with a supplied API key. |
| Historical market pipeline | Complete scripts: download, inspect, preprocess, and train paths are provided. |
| Price forecasting | Complete application integration: predictions only run from an on-disk trained model. |
| Crop image screening | Complete application integration: images are checked only by an on-disk trained model. |
| Community posts/comments | Complete core API and UI read/create flow. |
| Sources | Complete: official agricultural resource links are exposed by the API. |

## Required before a real deployment

1. **Government data access** — create a data.gov.in API key, put it in `backend/.env` as `DATA_GOV_API_KEY`, and verify the current resource schema/licence. The app cannot lawfully or reliably invent a replacement feed.
2. **Price model** — acquire a permitted historical market dataset, run the inspection/preprocessing/training scripts, document the exact data range and evaluate error by crop/market before enabling recommendations.
3. **Disease model** — download a permitted dataset, train it, evaluate it against representative Indian field imagery, define supported crops/classes, and obtain agricultural review of the controlled advice text. PlantVillage alone is not enough for field-grade diagnosis.
4. **Weather, maps, notifications, satellite and voice** — select providers, create the relevant API/cloud accounts, approve billing and data-processing terms, then implement the provider adapters. These cannot be genuinely activated without provider credentials and a product/privacy decision.
5. **Agronomy knowledge base** — collect licensed or government-approved regional guidance, establish review ownership, and build retrieval/approval controls. Do not use an unrestricted LLM to prescribe pesticides.
6. **Mandi and buyer matching** — acquire verified mandi coordinates, transport pricing assumptions, buyer consent and listings; then add data models, ranking rules, audit trails and moderation.
7. **Database and security** — migrate SQLite to managed PostgreSQL with PostGIS, use a secrets manager, configure HTTPS, email/OTP delivery, password reset, rate limits, backups, logging, and a security review.
8. **Quality and release** — add frontend tests, integration tests against a non-production database, accessibility testing, Hindi/local-language copy, user research, field pilot feedback, monitoring, CI/CD and incident procedures.

## Suggested order

Start with data governance and the two model evaluations. Then build weather/field/crop-cycle data collection, followed by mandi economics and buyer matching. Treat satellite, voice and autonomous LLM workflows as later features after the core advice is field-validated.
