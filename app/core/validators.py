from fastapi import Path, HTTPException, Depends
from bson import ObjectId
import re
from typing import Annotated


def validate_object_id(value: str) -> str:
    # Check if string is 24 characters and hexadecimal
    if not re.match(r"^[0-9a-fA-F]{24}$", value):
        raise HTTPException(
            status_code=400,
            detail="Invalid ID format. Must be a 24-character hexadecimal string",
        )
    return value


# Create reusable parameter type
ObjectIdParam = Annotated[
    str,
    Path(..., description="24-character hexadecimal string"),
    Depends(validate_object_id),
]
