from fastapi import APIRouter
from src.api.models import SettingsResponse
from src.helpers import settings

router = APIRouter(prefix="/settings_get", tags=["settings"])

@router.get("", response_model=SettingsResponse)
async def get_settings() -> SettingsResponse:
    """Get current application settings"""
    settings_output = settings.convert_out(settings.get_settings())
    return SettingsResponse(
        settings={"sections": settings_output.sections},
        message="Settings retrieved successfully"
    )

@router.post("", response_model=SettingsResponse)
async def get_settings_post() -> SettingsResponse:
    """Get current application settings (POST method for compatibility)"""
    settings_output = settings.convert_out(settings.get_settings())
    return SettingsResponse(
        settings={"sections": settings_output.sections},
        message="Settings retrieved successfully"
    )


