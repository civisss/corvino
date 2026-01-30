from fastapi import APIRouter
from config import get_settings

router = APIRouter()

@router.get("/config")
def get_config():
    """
    Get public configuration (supported assets, decimals, etc).
    """
    settings = get_settings()
    
    # Build a config object for frontend
    assets_config = {}
    for asset in settings.supported_assets:
        # Default to 2 decimals if not specified
        assets_config[asset] = {
            "decimals": settings.asset_decimals.get(asset, 2)
        }
        
    return {
        "assets": assets_config,
        "scan_interval": 300 # 5 minutes
    }
