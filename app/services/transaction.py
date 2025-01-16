from app.models.transaction import (
    Transaction,
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
        self, user_id: str, transaction_data: TransactionCreate
    ) -> Transaction:
        """Create a new transaction"""

        # Get current user balance
        user = await self.db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        current_balance = Decimal(str(user["balance"]))
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

        try:
            # Update user balance first (atomic operation)
            result = await self.db.users.find_one_and_update(
                {
                    "_id": ObjectId(user_id),
                    "balance": Decimal128(str(current_balance)),  # Optimistic locking
                },
                {
                    "$set": {
                        "balance": Decimal128(str(new_balance)),
                        "updated_at": datetime.now(timezone.utc),
                    }
                },
                return_document=True,
            )

            if not result:
                raise HTTPException(
                    status_code=409, detail="Balance was modified by another operation"
                )

            # Insert transaction
            result = await self.db.transactions.insert_one(transaction)
            transaction["id"] = str(result.inserted_id)

            return Transaction.model_validate(transaction)

        except Exception as e:
            # Log the error here
            raise HTTPException(status_code=500, detail=f"Transaction failed: {str(e)}")

    async def get_user_transactions(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 50,
        transaction_type: Optional[TransactionType] = None,
    ) -> List[Transaction]:
        """Get user's transaction history"""

        # Build query
        query = {"user_id": user_id}
        if transaction_type:
            query["type"] = transaction_type

        # Get transactions
        cursor = self.db.transactions.find(query)
        cursor = cursor.sort("created_at", -1).skip(skip).limit(limit)

        transactions = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            transactions.append(Transaction.model_validate(doc))

        return transactions
