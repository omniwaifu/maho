from fastapi import APIRouter
from src.api.models import BaseResponse

router = APIRouter(prefix="/test_connection", tags=["health"])

@router.post("", response_model=BaseResponse)
async def test_connection() -> BaseResponse:
    """Test API connection"""
    return BaseResponse(
        success=True,
        message="Connection test successful"
    ) 