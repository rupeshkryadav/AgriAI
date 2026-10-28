from fastapi import APIRouter, Query
from ..mandi_service import commodity_options, district_options, market_catalog, market_rates

router = APIRouter(prefix="/api/market", tags=["Mandi finder"])

@router.get("/districts")
def districts():
    return district_options()

@router.get("/commodities")
def commodities():
    return commodity_options()

@router.get("/catalog")
def catalog():
    return market_catalog()

@router.get("")
def mandis(lat: float | None = Query(None, ge=-90, le=90), lon: float | None = Query(None, ge=-180, le=180), commodity: str | None = None, district: str | None = None, state: str | None = None):
    return market_rates(lat,lon,commodity,district,state)
