# FarmerConnect — Smart Farmer Advisory & Market Intelligence

FarmerConnect is a mobile-responsive React + FastAPI platform for Indian farmers. The field interface centers on a mandi finder, farmer connections and community needs, and a multilingual AI Crop Doctor with leaf-photo screening, browser voice input, and spoken responses. The backend also retains the existing authenticated price forecasts, market history, and post/comment APIs.

The team plan and intended API integrations are in [docs/mvp-roadmap.md](docs/mvp-roadmap.md); a transparent production checklist is in [docs/production-readiness.md](docs/production-readiness.md); branch and ownership guidance is in [CONTRIBUTING.md](CONTRIBUTING.md).

## Data and model behavior

The mandi finder uses only India OGD / AGMARKNET records. It resolves market and district coordinates through OpenStreetMap Nominatim and stores resolved coordinates in SQLite; no sample market prices or seed community records are included. Configure both `DATA_GOV_API_KEY` and `GEMINI_API_KEY` in `backend/.env`. The AI Doctor sends every photo to Gemini Vision, adding a local MobileNetV3 prediction as a secondary signal when trained weights are present. Gemini uses `gemini-3.8-flash` by default and retries `gemini-3.6-flash` for transient model overload.

## Setup (PowerShell)

```powershell
if (!(Test-Path backend/.env)) { Copy-Item .env.example backend/.env }
python setup.py
cd backend
python -m uvicorn app.main:app --reload
```

Database tables initialize automatically at startup. For PostgreSQL, set `DATABASE_URL=postgresql+psycopg://user:password@host/dbname` and install `psycopg`.

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

`setup.py` installs API dependencies and attempts optional crop-model training. To train, install `backend/ml/requirements-torch.txt` and configure Kaggle credentials (`KAGGLE_USERNAME` and `KAGGLE_KEY`), or place PlantVillage class folders under `backend/data/plantvillage`. Without data or torch, the API still starts and uses Gemini Vision when configured.

## Optional crop model training

From `backend`:

```powershell
pip install -r ml/requirements-torch.txt
$env:KAGGLE_USERNAME='your-kaggle-username'
$env:KAGGLE_KEY='your-kaggle-key'
python ml/setup_and_train.py
```

Detailed provenance, actual-schema inspection behavior, licenses, and locations: [docs/dataset_sources.md](docs/dataset_sources.md). Run tests with `pytest`; build client with `npm run build`.

## API

FastAPI interactive documentation is available at `http://localhost:8000/docs`. Key routes include `/api/ai-doctor`, `/api/ai-doctor/chat`, `/api/market` (mandi board with optional `lat` / `lon`), `/api/community/farmers`, `/api/community/requirements`, `/api/community/posts`, and existing `/api/auth/*`, `/api/predictions`, and `/api/posts` routes.

## Limitations and next steps

Live market availability depends on the data.gov.in service and its API key; the app reports upstream errors rather than inventing prices. GPS requires browser permission and a secure context; district fallback uses live districts or a district/state entered by the farmer. OpenStreetMap coordinate lookup is cached in SQLite and subject to its service availability. Gemini diagnosis is advisory and should be confirmed with local extension guidance.
