from fastapi import Path, HTTPException
from typing import Annotated


# Create reusable parameter type
ObjectIdParam = Annotated[
    str,
    Path(
        title="Object ID",
        description="24-character hexadecimal string",
        example="507f1f77bcf86cd799439011",
        min_length=24,
        max_length=24,
        pattern="^[0-9a-fA-F]{24}$",
    ),
]
