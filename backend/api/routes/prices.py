from fastapi import APIRouter, Query, HTTPException
from market_data import MarketDataFetcher

router = APIRouter()

@router.get("/prices")
def get_current_prices(symbols: str = Query(..., description="Comma-separated list of symbols")):
    """
    Get current prices for the requested symbols.
    Example: /api/prices?symbols=BTC/USDT,ETH/USDT
    """
    symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]
    if not symbol_list:
         return {}
    
    fetcher = MarketDataFetcher()
    # Normalize symbols if passed with :USDT suffix (common in some configs)
    # But CCXT usually accepts 'BTC/USDT'. 
    # If fetcher fails, we might need to strip :USDT. 
    # For now assuming symbols match ccxt format or fetcher handles it.
    
    # Try fetching as provided
    prices = fetcher.fetch_current_prices(symbol_list)
    
    # If empty, try stripping :USDT suffix just in case DB has different format
    if not prices and any(":" in s for s in symbol_list):
         clean_list = [s.split(":")[0] for s in symbol_list]
         prices = fetcher.fetch_current_prices(clean_list)
         # Map back to original keys if possible? Or just return what we got.
         # Frontend maps by asset name so returning 'BTC/USDT' when asked for 'BTC/USDT:USDT' might require frontend adjustment.
         # Let's verify what the frontend/DB uses. 
         # SignalCard implementation does: asset.replace('/USDT:USDT', '').replace('/USDT', '')
         # So the DB likely has one of these.
    
    return prices
