# Contributing to FarmerConnect

## First-time setup

1. Create a branch from `main` using `feature/<short-description>` or `fix/<short-description>`.
2. Follow the setup commands in [README.md](README.md).
3. Keep each pull request focused on one feature or fix.
4. Run the relevant checks before opening a pull request.

## Team ownership for the MVP

| Owner | Area | First deliverable |
| --- | --- | --- |
| Teammate 1 | Frontend | Replace prototype market cards with the market API and add loading/error states. |
| Teammate 2 | Backend | Complete authenticated community posts, comments, and farmer connection endpoints. |
| Teammate 3 | ML / AI | Train and validate the crop-disease model; expose clear, controlled advisory output. |
| Teammate 4 | Data / DevOps | Market-data importer, PostgreSQL configuration, deployment, and CI. |

## Definition of done

- Do not commit secrets, datasets, trained model files, `node_modules`, or SQLite databases.
- Add or update tests for backend behaviour.
- Keep agriculture and price claims sourced; label estimates and prototype data clearly.
- Include a short testing note and screenshot in the pull request when changing UI.
