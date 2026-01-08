from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.database import get_db
from app.auth.dependencies import require_admin
from app.providers.registry import get_registry, ProviderType

router = APIRouter(
    prefix="/api/v1/providers",
    tags=["providers"]
)

@router.get("")
async def get_all_providers(
    current_user = Depends(require_admin),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Get all provider configurations"""

    registry = get_registry()
    providers = []

    # Get CRM providers
    for name, provider in registry.get_all_providers(ProviderType.CRM).items():
        providers.append({
            "id": f"crm_{name}",
            "name": name,
            "type": "crm",
            "is_active": registry.get_active_provider(ProviderType.CRM) == provider,
            "config": {
                "api_url": getattr(provider, 'api_url', ''),
                "api_key": "***" if hasattr(provider, 'api_key') else "",
            }
        })

    # Get Billing providers
    for name, provider in registry.get_all_providers(ProviderType.BILLING).items():
        providers.append({
            "id": f"billing_{name}",
            "name": name,
            "type": "billing",
            "is_active": registry.get_active_provider(ProviderType.BILLING) == provider,
            "config": {
                "api_url": getattr(provider, 'api_url', ''),
                "api_key": "***" if hasattr(provider, 'api_key') else "",
            }
        })

    return providers

@router.get("/{provider_id}")
async def get_provider(
    provider_id: str,
    current_user = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get a specific provider configuration"""

    registry = get_registry()

    # Parse provider ID
    if provider_id.startswith("crm_"):
        provider_type = ProviderType.CRM
        provider_name = provider_id[4:]
    elif provider_id.startswith("billing_"):
        provider_type = ProviderType.BILLING
        provider_name = provider_id[8:]
    else:
        raise HTTPException(status_code=404, detail="Provider not found")

    # Get provider
    providers = registry.get_all_providers(provider_type)
    if provider_name not in providers:
        raise HTTPException(status_code=404, detail="Provider not found")

    provider = providers[provider_name]

    return {
        "id": provider_id,
        "name": provider_name,
        "type": provider_type.value,
        "is_active": registry.get_active_provider(provider_type) == provider,
        "config": {
            "api_url": getattr(provider, 'api_url', ''),
            "api_key": "***" if hasattr(provider, 'api_key') else "",
        }
    }

@router.post("/{provider_id}/switch")
async def switch_active_provider(
    provider_id: str,
    current_user = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Switch the active provider"""

    registry = get_registry()

    # Parse provider ID
    if provider_id.startswith("crm_"):
        provider_type = ProviderType.CRM
        provider_name = provider_id[4:]
    elif provider_id.startswith("billing_"):
        provider_type = ProviderType.BILLING
        provider_name = provider_id[8:]
    else:
        raise HTTPException(status_code=404, detail="Provider not found")

    # Switch active provider
    success = registry.set_active_provider(provider_type, provider_name)
    if not success:
        raise HTTPException(status_code=404, detail="Provider not found")

    return {"message": f"Switched active {provider_type.value} provider to {provider_name}"}

@router.get("/{provider_id}/health")
async def check_provider_health(
    provider_id: str,
    current_user = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Check provider health status"""

    registry = get_registry()

    # Parse provider ID
    if provider_id.startswith("crm_"):
        provider_type = ProviderType.CRM
        provider_name = provider_id[4:]
    elif provider_id.startswith("billing_"):
        provider_type = ProviderType.BILLING
        provider_name = provider_id[8:]
    else:
        raise HTTPException(status_code=404, detail="Provider not found")

    # Get provider
    providers = registry.get_all_providers(provider_type)
    if provider_name not in providers:
        raise HTTPException(status_code=404, detail="Provider not found")

    provider = providers[provider_name]

    # Check health (for now, mock providers are always healthy)
    return {
        "status": "healthy",
        "provider": provider_name,
        "type": provider_type.value,
        "message": "Provider is operational"
    }