from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
from app.models.product import ProductBase, ProductCreate, ProductUpdate, ProductStatus
from app.models.user import UserBase
from app.core.security import get_current_admin
from app.core.validators import ObjectIdParam
from app.services.product import ProductService
from app.core.config import settings
from decimal import Decimal
from enum import Enum

router = APIRouter()


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


@router.post("/", response_model=ProductBase)
async def create_product(
    product_data: ProductCreate,
    admin: UserBase = Depends(get_current_admin),
    product_service: ProductService = Depends(),
):
    """Create a new product"""
    # Validate image URLs
    if product_data.images:
        for image_url in product_data.images:
            if not image_url.startswith(settings.AWS_BUCKET_URL):
                raise HTTPException(
                    status_code=400, detail=f"Invalid image URL: {image_url}"
                )

    return await product_service.create_product(product_data)


@router.get("/", response_model=dict)
async def get_products(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Items per page"),
    status: Optional[ProductStatus] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: Optional[str] = Query(None, description="Field to sort by"),
    sort_order: SortOrder = Query(
        SortOrder.ASC, description="Sort order (asc or desc)"
    ),
    min_price: Optional[Decimal] = Query(None, ge=0, description="Minimum price"),
    max_price: Optional[Decimal] = Query(None, ge=0, description="Maximum price"),
    admin: UserBase = Depends(get_current_admin),
    product_service: ProductService = Depends(),
):
    """Get all products with pagination and filters"""
    try:
        print("sort_by123", sort_by)
        # Convert sort_order to string format expected by service
        sort_order_str = "desc" if sort_order == SortOrder.DESC else "asc"

        # Get products with pagination and filters
        products, total = await product_service.get_products(
            skip=(page - 1) * size,
            limit=size,
            category=category,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order_str,
            status=status,
            min_price=min_price,
            max_price=max_price,
        )

        # Calculate total pages
        total_pages = (total + size - 1) // size

        return {
            "items": products,
            "total": total,
            "page": page,
            "size": size,
            "pages": total_pages,
            "sort_by": sort_by,
            "sort_order": sort_order,
        }

    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=400, detail=f"Invalid sort field: {sort_by}"
            )
        raise HTTPException(
            status_code=500, detail=f"Error fetching products: {str(e)}"
        )


@router.get("/{product_id}", response_model=ProductBase)
async def get_product(
    product_id: ObjectIdParam,
    admin: UserBase = Depends(get_current_admin),
    product_service: ProductService = Depends(),
):
    """Get product by ID"""
    return await product_service.get_product_by_id(str(product_id))


@router.put("/{product_id}", response_model=ProductBase)
async def update_product(
    product_id: ObjectIdParam,
    product_data: ProductUpdate,
    admin: UserBase = Depends(get_current_admin),
    product_service: ProductService = Depends(),
):
    """Update product data"""
    # Validate image URLs if updating
    if product_data.images is not None:
        for image_url in product_data.images:
            if not image_url.startswith(settings.AWS_BUCKET_URL):
                raise HTTPException(
                    status_code=400, detail=f"Invalid image URL: {image_url}"
                )

    return await product_service.update_product(str(product_id), product_data)


@router.delete("/{product_id}")
async def delete_product(
    product_id: ObjectIdParam,
    admin: UserBase = Depends(get_current_admin),
    product_service: ProductService = Depends(),
):
    """Soft delete product"""
    success = await product_service.soft_delete_product(str(product_id))
    if not success:
        raise HTTPException(status_code=404, detail="Product not found")

    return {"message": "Product deleted successfully"}


@router.post("/{product_id}/stock")
async def update_product_stock(
    product_id: ObjectIdParam,
    quantity: int = Query(..., gt=0),
    operation: str = Query(..., regex="^(add|subtract)$"),
    admin: UserBase = Depends(get_current_admin),
    product_service: ProductService = Depends(),
):
    """Update product stock (add or subtract)"""
    updated_product = await product_service.update_stock(
        str(product_id), quantity, operation
    )
    return {
        "message": f"Stock {operation}ed successfully",
        "new_stock": updated_product.stock,
    }
