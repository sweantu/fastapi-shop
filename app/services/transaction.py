from app.models.transaction import (
    TransactionBase,
    TransactionCreate,
    TransactionType,
    TransactionStatus,
)
from app.db.mongodb import MongoDB
from fastapi import HTTPException
from datetime import datetime, timezone
from bson import Decimal128, ObjectId
from decimal import Decimal
from typing import List, Optional


class TransactionService:
    def __init__(self):
        self.db = MongoDB.get_db()

    async def create_transaction(
        self,
        transaction_data: TransactionCreate,
        user_id: str,
        current_balance: Decimal,
    ) -> TransactionBase:
        """Create a new transaction"""

        new_balance = current_balance

        # Calculate new balance
        if transaction_data.type in [TransactionType.DEPOSIT, TransactionType.REFUND]:
            new_balance += transaction_data.amount
        elif transaction_data.type in [
            TransactionType.WITHDRAW,
            TransactionType.PAYMENT,
        ]:
            if current_balance < transaction_data.amount:
                raise HTTPException(status_code=400, detail="Insufficient balance")
            new_balance -= transaction_data.amount

        # Create transaction
        transaction = {
            "user_id": user_id,
            "type": transaction_data.type,
            "amount": Decimal128(str(transaction_data.amount)),
            "balance": Decimal128(str(new_balance)),
            "status": TransactionStatus.COMPLETED,
            "description": transaction_data.description,
            "reference_id": transaction_data.reference_id,
            "created_at": datetime.now(timezone.utc),
            "updated_at": None,
        }

        # Insert transaction
        result = await self.db.transactions.insert_one(transaction)
        transaction["id"] = str(result.inserted_id)

        return TransactionBase.model_validate(transaction)

    async def get_user_transactions(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 50,
        transaction_type: Optional[TransactionType] = None,
        sort_by: Optional[str] = "created_at",
        sort_order: Optional[str] = "desc",
        min_amount: Optional[Decimal] = None,
        max_amount: Optional[Decimal] = None,
        status: Optional[TransactionStatus] = None,
    ) -> tuple[List[TransactionBase], int]:
        """Get user's transaction history with pagination, filtering and sorting"""

        # Build query
        query = {"user_id": user_id}
        if transaction_type:
            query["type"] = transaction_type

        if status:
            query["status"] = status

        if min_amount is not None or max_amount is not None:
            amount_query = {}
            if min_amount is not None:
                amount_query["$gte"] = Decimal128(str(min_amount))
            if max_amount is not None:
                amount_query["$lte"] = Decimal128(str(max_amount))
            if amount_query:
                query["amount"] = amount_query

        # Handle sort parameters
        sort_field = sort_by if sort_by is not None else "created_at"
        if sort_field == "id":
            sort_field = "_id"
        sort_direction = -1 if sort_order == "desc" else 1

        # Get total count
        total = await self.db.transactions.count_documents(query)

        # Get transactions
        cursor = self.db.transactions.find(query)
        cursor = cursor.sort(sort_field, sort_direction)
        cursor = cursor.skip(skip).limit(limit)

        transactions = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            transactions.append(TransactionBase.model_validate(doc))

        return transactions, total
