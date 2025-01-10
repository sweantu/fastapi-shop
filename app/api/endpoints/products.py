from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.models.product import Product, ProductStatus
from app.core.validators import ObjectIdParam
from app.db.mongodb import MongoDB
from bson import ObjectId
from math import ceil

router = APIRouter()


@router.get("/", response_model=dict)
async def get_products(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Items per page"),
    category: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: Optional[str] = Query(None, description="Field to sort by"),
    sort_order: Optional[str] = Query("asc", description="Sort order (asc or desc)"),
):
    """
    Get public products list
    Only returns active products
    """
    db = MongoDB.get_db()

    # Base query: only active products
    query = {"status": ProductStatus.ACTIVE, "deleted_at": None}

    # Apply filters
    if category:
        query["category"] = category
    if search:
        query["$text"] = {"$search": search}

    try:
        # Get total count
        total = await db.products.count_documents(query)

        # Calculate pagination
        total_pages = ceil(total / size)
        skip = (page - 1) * size

        # Prepare sort
        sort_options = {}
        if sort_by:
            if sort_by == "id":
                sort_by = "_id"
            sort_options[sort_by] = 1 if sort_order == "asc" else -1
        else:
            sort_options["created_at"] = -1  # Default sort

        # Get products
        cursor = db.products.find(query)
        if sort_options:
            cursor = cursor.sort(list(sort_options.items()))
        cursor = cursor.skip(skip).limit(size)

        products = []
        async for product in cursor:
            product["id"] = str(product.pop("_id"))
            products.append(Product.model_validate(product))

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
        raise HTTPException(
            status_code=500, detail=f"Error fetching products: {str(e)}"
        )


@router.get("/{product_id}", response_model=Product)
async def get_product(product_id: ObjectIdParam):
    """
    Get public product details
    Only returns active products
    """
    db = MongoDB.get_db()

    product = await db.products.find_one(
        {
            "_id": ObjectId(product_id),
            "status": ProductStatus.ACTIVE,
            "deleted_at": None,
        }
    )

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    product["id"] = str(product.pop("_id"))
    return Product.model_validate(product)


@router.get("/categories/", response_model=list[str])
async def get_categories():
    """
    Get all unique product categories
    Only from active products
    """
    db = MongoDB.get_db()

    categories = await db.products.distinct(
        "category", {"status": ProductStatus.ACTIVE, "deleted_at": None}
    )

    return sorted(categories)
