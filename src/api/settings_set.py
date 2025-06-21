from fastapi import APIRouter
from src.api.models import SettingsRequest, SettingsResponse
from src.helpers import settings
from typing import Any

router = APIRouter(prefix="/settings_set", tags=["settings"])

@router.post("", response_model=SettingsResponse)
async def set_settings(request: SettingsRequest) -> SettingsResponse:
    """Update application settings"""
    set = settings.convert_in(request.settings)
    settings.set_settings(set)
    # Return the updated settings via convert_out with proper structure
    updated_settings = settings.convert_out(settings.get_settings())
    return SettingsResponse(
        settings={"sections": updated_settings.sections},
        message="Settings updated successfully"
    )
