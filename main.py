from fastapi import FastAPI
from app.db.mongodb import MongoDB
from app.api.endpoints import users, health
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    await MongoDB.connect_db()
    yield
    await MongoDB.close_db()

app = FastAPI(lifespan=lifespan)

# Include routers
app.include_router(health.router, prefix="/system", tags=["system"])
app.include_router(users.router, prefix="/users", tags=["users"])


# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Welcome to FastAPI Shop API",
        "docs": "/docs",
        "health": "/system/health",
    }
