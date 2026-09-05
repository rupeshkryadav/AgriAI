# Dataset sources and inspection

## AGMARKNET daily mandi prices

- Source: [India Open Government Data catalog](https://www.data.gov.in/catalog/current-daily-price-various-commodities-various-markets-mandi), published by the Directorate of Marketing & Inspection, Ministry of Agriculture & Farmers Welfare.
- Usage: the catalog lists the National Data Sharing and Accessibility Policy / Government Open Data License–India. Check the catalog again before redistribution.
- API resource: `6141ea17-a69d-4713-b600-0a43c8fd9a6c`; an API key is required. Set `DATA_GOV_API_KEY`, then run `python ml/download_data.py` from `backend`.
- Download location: `backend/data/raw/agmarknet.json`; processed location: `backend/data/processed/market_prices.csv`.
- Inspection: `python ml/inspect_data.py` prints the actual record keys, dtypes, missingness and examples before preprocessing. The downloader and preprocessing scripts fail rather than invent a schema when the response lacks the required AGMARKNET keys.
- Used for: historical market table, filtering, chronological price model training and reference price. It is explicitly labelled historical, not live.

## PlantVillage

- Source: [PlantVillage Dataset repository](https://github.com/spMohanty/PlantVillage-Dataset), introduced by Mohanty, Hughes & Salathé (2016); see the repository’s license/citation and the [Hugging Face dataset card](https://huggingface.co/datasets/mohanty/PlantVillage) (CC BY-SA 3.0 indicated there).
- Download location: `backend/data/raw/PlantVillage-Dataset` via `python ml/download_plantvillage.py`. The full clone is large (roughly 2 GB); it is not committed.
- Inspection: inspect the actual class folders with `Get-ChildItem data/raw/PlantVillage-Dataset/raw/color -Directory` before `python ml/train_disease.py`. The trainer derives classes from those folders rather than claiming a fixed label set.
- Used for: a bounded baseline image classifier. It only returns labels actually present in the local downloaded corpus.

## MSP

MSP is not bundled because values vary by marketing season and need a current official notification. The app intentionally does not present market prices as MSP. Add a versioned official CACP/Ministry spreadsheet in a future `data/raw/msp/` importer after recording its notification year and source.
