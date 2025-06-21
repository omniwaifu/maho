from fastapi import APIRouter

router = APIRouter(prefix="/test_connection", tags=["test"])

@router.post("")
async def test_connection() -> dict:
    """Test API connection"""
    return {
        "status": "success",
        "message": "Connection test successful"
    } 