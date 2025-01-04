from fastapi import APIRouter, HTTPException, Depends, Query, Path
from typing import Annotated, List, Optional
from datetime import datetime, timezone
from app.models.product import Product, ProductCreate, ProductUpdate, ProductStatus
from app.core.security import verify_admin
from app.core.validators import ObjectIdParam
from app.db.mongodb import MongoDB
from bson import ObjectId
from math import ceil

router = APIRouter()


@router.post("/", response_model=Product)
async def create_product(
    product_data: ProductCreate, admin: str = Depends(verify_admin)
):
    db = MongoDB.get_db()

    # Check if SKU exists
    if await db.products.find_one({"sku": product_data.sku}):
        raise HTTPException(status_code=400, detail="SKU already exists")

    # Prepare product data
    product_dict = product_data.model_dump()
    product_dict.update(
        {
            "created_at": datetime.now(timezone.utc),
            "updated_at": None,
            "deleted_at": None,
        }
    )

    # Insert product
    result = await db.products.insert_one(product_dict)

    # Get created product
    created_product = await db.products.find_one({"_id": result.inserted_id})
    created_product["id"] = str(created_product.pop("_id"))

    # Convert to Product model
    return Product.model_validate(created_product)


@router.get("/", response_model=dict)
async def get_products(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Items per page"),
    status: Optional[ProductStatus] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: Optional[str] = Query(None, description="Field to sort by"),
    sort_order: Optional[str] = Query("asc", description="Sort order (asc or desc)"),
    admin: str = Depends(verify_admin),
):
    db = MongoDB.get_db()
    query = {"deleted_at": None}  # Exclude soft-deleted products

    # Apply filters
    if status:
        query["status"] = status
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

        print(list(sort_options.items()), "sort_options")

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
async def get_product(product_id: ObjectIdParam, admin: str = Depends(verify_admin)):
    db = MongoDB.get_db()
    product = await db.products.find_one({"_id": ObjectId(product_id)})

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    product["id"] = str(product.pop("_id"))
    return Product.model_validate(product)


@router.put("/{product_id}", response_model=Product)
async def update_product(
    product_id: ObjectIdParam,
    product_data: ProductUpdate,
    admin: str = Depends(verify_admin),
):
    db = MongoDB.get_db()

    # Check if product exists
    product = await db.products.find_one({"_id": ObjectId(product_id)})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Check SKU uniqueness if updating
    if product_data.sku:
        existing = await db.products.find_one(
            {"sku": product_data.sku, "_id": {"$ne": ObjectId(product_id)}}
        )
        if existing:
            raise HTTPException(status_code=400, detail="SKU already exists")

    # Update product
    update_data = product_data.model_dump(exclude_unset=True)
    update_data.update({"updated_at": datetime.now(timezone.utc)})

    result = await db.products.find_one_and_update(
        {"_id": ObjectId(product_id)}, {"$set": update_data}, return_document=True
    )

    result["id"] = str(result.pop("_id"))
    return Product.model_validate(result)


@router.delete("/{product_id}")
async def delete_product(product_id: ObjectIdParam, admin: str = Depends(verify_admin)):
    db = MongoDB.get_db()

    # Soft delete
    result = await db.products.find_one_and_update(
        {"_id": ObjectId(product_id)},
        {
            "$set": {
                "status": ProductStatus.DELETED,
                "deleted_at": datetime.now(timezone.utc),
            }
        },
        return_document=True,
    )

    if not result:
        raise HTTPException(status_code=404, detail="Product not found")

    return {"message": "Product deleted successfully"}
