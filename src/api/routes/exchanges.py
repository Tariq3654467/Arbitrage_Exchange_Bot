"""
Exchange Management Routes
Additional routes for managing exchanges
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from typing import List
from ...api.dependencies import verify_credentials, postgres_db
from ...utils.logger import get_logger

logger = get_logger()
router = APIRouter()


@router.post("/api/exchanges/toggle")
async def toggle_exchange(
    exchange_name: str = Body(...),
    enabled: bool = Body(...),
    username: str = Depends(verify_credentials)
):
    """Enable or disable an exchange"""
    try:
        if not postgres_db:
            raise HTTPException(status_code=500, detail="Database not available")
        
        from ...database.api_keys_manager import APIKeysManager
        keys_manager = APIKeysManager(postgres_db)
        
        # Check if exchange has valid keys
        if enabled and not keys_manager.has_valid_keys(exchange_name):
            return {
                "status": "error",
                "message": f"Cannot enable {exchange_name}: No valid API keys configured"
            }
        
        success = keys_manager.toggle_exchange(exchange_name, enabled)
        
        if success:
            return {
                "status": "success",
                "message": f"{exchange_name} {'enabled' if enabled else 'disabled'}"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to toggle exchange")
    
    except Exception as e:
        logger.error(f"Error toggling exchange: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/exchanges/{exchange_name}")
async def delete_exchange_keys(
    exchange_name: str,
    username: str = Depends(verify_credentials)
):
    """Delete exchange API keys"""
    try:
        if not postgres_db:
            raise HTTPException(status_code=500, detail="Database not available")
        
        from ...database.api_keys_manager import APIKeysManager
        keys_manager = APIKeysManager(postgres_db)
        
        success = keys_manager.delete_exchange(exchange_name)
        
        if success:
            return {
                "status": "success",
                "message": f"API keys deleted for {exchange_name}"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to delete keys")
    
    except Exception as e:
        logger.error(f"Error deleting exchange keys: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/exchanges/status")
async def get_exchanges_status():
    """Get current status of all configured exchanges"""
    try:
        if not postgres_db:
            return {"exchanges": []}
        
        from ...database.api_keys_manager import APIKeysManager
        keys_manager = APIKeysManager(postgres_db)
        
        all_exchanges = keys_manager.get_all_exchanges()
        
        status_list = []
        for ex in all_exchanges:
            has_keys = keys_manager.has_valid_keys(ex['exchange_name'])
            
            status_list.append({
                "name": ex['exchange_name'],
                "type": ex['exchange_type'],
                "enabled": ex['enabled'],
                "configured": has_keys,
                "testnet": ex.get('testnet', False),
                "status": "ready" if (has_keys and ex['enabled']) else "not_ready"
            })
        
        return {"exchanges": status_list}
    
    except Exception as e:
        logger.error(f"Error getting exchange status: {e}")
        return {"exchanges": []}

