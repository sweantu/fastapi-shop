from fastapi import APIRouter, HTTPException
from app.db.mongodb import MongoDB

router = APIRouter()


@router.get("/health")
async def health_check():
    try:
        # Check MongoDB connection
        client = MongoDB.get_client()
        await client.admin.command("ping")

        return {"status": "healthy", "database": "connected", "version": "1.0.0"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")
