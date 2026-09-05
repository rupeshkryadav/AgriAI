# FarmerConnect MVP Roadmap

The supplied video establishes the product direction: a low-friction farmer product with three primary destinations. The current implementation adapts that language to a laptop-first desktop workspace, as requested.

| Screen | Current UI | Backend integration next |
| --- | --- | --- |
| Market | Searchable price-card prototype | `GET /api/market/prices`, then live AGMARKNET import/caching |
| Connect | Friends tab and connection interaction | Posts, comments, requirements, and farmer connection model |
| AI Crop Doctor | Image chooser and advisory question flow | `POST /api/disease/predict` and controlled knowledge-base advice |

## MVP milestones

1. **Foundation** — responsive frontend shell, API service, environment configuration, and contribution workflow.
2. **Real data** — scheduled market importer with source/date metadata and graceful empty/error states.
3. **Crop health** — evaluated disease model, supported-crop constraints, and advisory review.
4. **Community** — farmer profiles, posts, comments, requirements, and moderation rules.
5. **Pilot readiness** — Hindi copy, accessibility pass, observability, security review, and field testing.

## Guardrails

- Market cards in the current visual shell are clearly marked prototype data until the API is wired.
- Crop diagnosis must remain a screening aid, not a substitute for a local agronomist.
- Do not let a language model generate pesticide instructions without a reviewed knowledge base.
