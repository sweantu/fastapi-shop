from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from app.models.product import ProductBase, ProductStatus
from app.core.validators import ObjectIdParam
from app.services.product import ProductService
from decimal import Decimal
from enum import Enum

router = APIRouter()


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


@router.get("/", response_model=dict)
async def get_products(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Items per page"),
    category: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: Optional[str] = Query(None, description="Field to sort by"),
    sort_order: SortOrder = Query(
        SortOrder.ASC, description="Sort order (asc or desc)"
    ),
    min_price: Optional[Decimal] = Query(None, ge=0, description="Minimum price"),
    max_price: Optional[Decimal] = Query(None, ge=0, description="Maximum price"),
    product_service: ProductService = Depends(),
):
    """
    Get public products list
    Only returns active products
    """
    try:
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
            status=ProductStatus.ACTIVE,  # Only active products for public
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
    product_service: ProductService = Depends(),
):
    """
    Get public product details
    Only returns active products
    """
    return await product_service.get_product_by_id(str(product_id))


@router.get("/categories/", response_model=list[str])
async def get_categories(
    product_service: ProductService = Depends(),
):
    """
    Get all unique product categories
    Only from active products
    """
    return await product_service.get_categories()
