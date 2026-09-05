# Architecture

React/Vite is a responsive single-page client. It uses bearer JWTs for authenticated API calls. FastAPI owns validation, authorization and API documentation (`/docs`). SQLAlchemy persists users, profiles (on User), predictions, posts, comments and notifications in SQLite by default; set a PostgreSQL `DATABASE_URL` for deployment. Data and model artifacts are separate from application code and are generated only by ML scripts.
