from app.models.product import ProductBase, ProductCreate, ProductUpdate, ProductStatus
from app.db.mongodb import MongoDB
from fastapi import HTTPException
from datetime import datetime, timezone
from bson import ObjectId, Decimal128
from decimal import Decimal
from typing import List, Optional, Tuple
from math import ceil


class ProductService:
    def __init__(self):
        self.db = MongoDB.get_db()

    async def create_product(self, product_data: ProductCreate) -> ProductBase:
        """Create a new product"""
        # Check existing SKU
        if await self.db.products.find_one({"sku": product_data.sku}):
            raise HTTPException(status_code=400, detail="SKU already exists")

        # Prepare product data
        product_dict = product_data.model_dump()
        product_dict.update(
            {
                "created_at": datetime.now(timezone.utc),
                "updated_at": None,
                "deleted_at": None,
                "price": Decimal128(str(product_dict["price"])),
            }
        )

        # Insert product
        result = await self.db.products.insert_one(product_dict)
        created_product = await self.db.products.find_one({"_id": result.inserted_id})
        created_product["id"] = str(created_product.pop("_id"))

        return ProductBase.model_validate(created_product)

    async def get_product_by_id(self, product_id: str) -> ProductBase:
        """Get product by ID"""
        product = await self.db.products.find_one(
            {
                "_id": ObjectId(product_id),
                "status": ProductStatus.ACTIVE,
                "deleted_at": None,
            }
        )
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        product["id"] = str(product.pop("_id"))
        return ProductBase.model_validate(product)

    async def get_products_by_ids(self, product_ids: List[str]) -> List[ProductBase]:
        """Get products by IDs"""
        cursor = self.db.products.find(
            {"_id": {"$in": [ObjectId(id) for id in product_ids]}}
        )
        products = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            products.append(ProductBase.model_validate(doc))
        return products

    async def update_product(
        self, product_id: str, product_data: ProductUpdate
    ) -> ProductBase:
        """Update product data"""
        update_data = product_data.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="No data to update")

        # Handle price update
        if "price" in update_data:
            update_data["price"] = Decimal128(str(update_data["price"]))

        update_data["updated_at"] = datetime.now(timezone.utc)

        result = await self.db.products.find_one_and_update(
            {"_id": ObjectId(product_id)}, {"$set": update_data}, return_document=True
        )

        if not result:
            raise HTTPException(status_code=404, detail="Product not found")

        result["id"] = str(result.pop("_id"))
        return ProductBase.model_validate(result)

    async def soft_delete_product(self, product_id: str) -> bool:
        """Soft delete a product"""
        result = await self.db.products.find_one_and_update(
            {"_id": ObjectId(product_id)},
            {
                "$set": {
                    "deleted_at": datetime.now(timezone.utc),
                    "status": ProductStatus.DELETED,
                }
            },
            return_document=True,
        )
        return bool(result)

    async def get_products(
        self,
        skip: int = 0,
        limit: int = 50,
        category: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: Optional[str] = "created_at",
        sort_order: Optional[str] = "desc",
        status: Optional[ProductStatus] = ProductStatus.ACTIVE,
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
    ) -> Tuple[List[ProductBase], int]:
        """Get products with pagination and filtering"""
        # Build query
        query = {"deleted_at": None}

        if status:
            query["status"] = status

        if category:
            query["category"] = category

        if search:
            query["$or"] = [
                {"name": {"$regex": search, "$options": "i"}},
                {"description": {"$regex": search, "$options": "i"}},
            ]

        if min_price is not None or max_price is not None:
            price_query = {}
            if min_price is not None:
                price_query["$gte"] = Decimal128(str(min_price))
            if max_price is not None:
                price_query["$lte"] = Decimal128(str(max_price))
            if price_query:
                query["price"] = price_query

        # Handle sort parameters
        sort_field = sort_by if sort_by else "created_at"
        if sort_field == "id":
            sort_field = "_id"
        sort_direction = -1 if sort_order == "desc" else 1

        # Get total count
        total = await self.db.products.count_documents(query)

        # Get products
        cursor = self.db.products.find(query)
        cursor = cursor.sort(sort_field, sort_direction)
        cursor = cursor.skip(skip).limit(limit)

        products = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            products.append(ProductBase.model_validate(doc))

        return products, total

    async def update_stock(
        self, product_id: str, quantity: int, operation: str = "add"
    ) -> ProductBase:
        """Update product stock (add or subtract)"""
        if operation not in ["add", "subtract"]:
            raise ValueError("Invalid operation. Use 'add' or 'subtract'")

        if quantity < 0:
            raise HTTPException(status_code=400, detail="Quantity must be positive")

        # For subtract operation, check if enough stock
        if operation == "subtract":
            product = await self.get_product_by_id(product_id)
            if product.stock < quantity:
                raise HTTPException(status_code=400, detail="Insufficient stock")

        update_result = await self.db.products.find_one_and_update(
            {"_id": ObjectId(product_id)},
            {
                "$inc": {"stock": quantity if operation == "add" else -quantity},
                "$set": {"updated_at": datetime.now(timezone.utc)},
            },
            return_document=True,
        )

        if not update_result:
            raise HTTPException(status_code=404, detail="Product not found")

        update_result["id"] = str(update_result.pop("_id"))
        return ProductBase.model_validate(update_result)

    async def get_categories(self) -> List[str]:
        """Get all unique product categories"""
        categories = await self.db.products.distinct(
            "category", {"status": ProductStatus.ACTIVE, "deleted_at": None}
        )
        return sorted(categories)
