from fastapi import APIRouter, Query
from ..mandi_service import commodity_options, district_options, market_catalog, market_rates, state_options

router = APIRouter(prefix="/api/market", tags=["Mandi finder"])

@router.get("/districts")
def districts(state: str | None = Query(None)):
    return district_options(state)

@router.get("/states")
def states():
    return state_options()

@router.get("/commodities")
def commodities():
    return commodity_options()

@router.get("/catalog")
def catalog():
    return market_catalog()

@router.get("")
def mandis(lat: float | None = Query(None, ge=-90, le=90), lon: float | None = Query(None, ge=-180, le=180), commodity: str | None = None, district: str | None = None, state: str | None = None):
    return market_rates(lat,lon,commodity,district,state)
