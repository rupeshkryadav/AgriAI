# FarmerConnect — Smart Farmer Advisory & Market Intelligence

Laptop-first React + FastAPI application for Indian farmers. The interface is a desktop operations workspace for **Market intelligence**, **Price forecasting**, **AI Crop Doctor**, **Farmer community**, and official **Knowledge base** sources. It never ships fabricated market prices, model outputs, farmer posts, or crop diagnoses: the interface displays only API results and explains the prerequisite when a source or model is unavailable.

The team plan and intended API integrations are in [docs/mvp-roadmap.md](docs/mvp-roadmap.md); a transparent production checklist is in [docs/production-readiness.md](docs/production-readiness.md); branch and ownership guidance is in [CONTRIBUTING.md](CONTRIBUTING.md).

## What is deliberately not faked

This repository contains no bundled “live” market records, hard-coded predictions, sample user, community content, or untrained disease result. After the documented real-data download/training, every prediction is from the persisted model. Before then, the API returns an actionable status rather than an invented outcome. The OGD endpoint could not be reached from this build environment, so no dataset was silently substituted; its downloaded schema must be inspected locally before use.

## Setup (PowerShell)

```powershell
Copy-Item .env.example backend/.env
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:DATABASE_URL='sqlite:///./agri_ai.db'
$env:JWT_SECRET='replace-this-for-development'
uvicorn app.main:app --reload
```

Database tables initialize automatically at startup. For PostgreSQL, set `DATABASE_URL=postgresql+psycopg://user:password@host/dbname` and install `psycopg`.

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

## Download, inspect, preprocess and train

Get an OGD API key from [data.gov.in](https://data.gov.in/apis), then from `backend`:

```powershell
$env:DATA_GOV_API_KEY='your-key'
python ml/download_data.py
python ml/inspect_data.py
python ml/preprocess.py
python ml/train_price.py
python ml/download_plantvillage.py
Get-ChildItem data/raw/PlantVillage-Dataset/raw/color -Directory
python ml/train_disease.py
```

Detailed provenance, actual-schema inspection behavior, licenses, and locations: [docs/dataset_sources.md](docs/dataset_sources.md). Run tests with `pytest`; build client with `npm run build`.

## API

FastAPI interactive documentation is available at `http://localhost:8000/docs`. Key routes: `/api/auth/*`, `/api/users/me`, `/api/market/*`, `/api/predictions`, `/api/disease/predict`, `/api/posts`, and `/api/notifications`.

## Limitations and next steps

Historical price estimates cannot guarantee future prices; there is no credentials-free live OGD feed bundled. Crop screening supports only the locally inspected/trained PlantVillage categories and is not field-validated diagnosis. Add an official, year-versioned MSP importer, a PostgreSQL deployment configuration, calibrated prediction intervals, location/weather covariates, and frontend component tests for production.
