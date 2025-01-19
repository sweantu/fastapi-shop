from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.mongodb import MongoDB
from app.api.endpoints import (
    files,
    orders,
    transactions,
    users,
    health,
    products,
    carts,
)
from app.api.endpoints.admin import users as admin_users, products as admin_products
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    await MongoDB.connect_db()
    yield
    await MongoDB.close_db()


app = FastAPI(lifespan=lifespan)

# Configure CORS


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Include routers
app.include_router(health.router, prefix="/system", tags=["system"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(admin_users.router, prefix="/admin/users", tags=["admin-users"])
app.include_router(products.router, prefix="/products", tags=["products"])
app.include_router(
    admin_products.router, prefix="/admin/products", tags=["admin-products"]
)
app.include_router(transactions.router, prefix="/transactions", tags=["transactions"])
app.include_router(carts.router, prefix="/carts", tags=["carts"])
app.include_router(orders.router, prefix="/orders", tags=["orders"])
app.include_router(files.router, prefix="/files", tags=["files"])


# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Welcome to FastAPI Shop API",
        "docs": "/docs",
        "health": "/system/health",
    }
