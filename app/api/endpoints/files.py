from fastapi import APIRouter, File, HTTPException, UploadFile, Depends
from typing import List
from app.core.security import get_token
from app.dependencies.s3 import get_s3_service
from app.services.s3 import S3Service

router = APIRouter()

# Constants for file validation
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB per file
MAX_TOTAL_SIZE = 20 * 1024 * 1024  # 20MB total
MAX_FILES = 10  # Maximum number of files
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": [".jpg", ".jpeg"],
    "image/png": [".png"],
    "image/webp": [".webp"],
    "image/gif": [".gif"],
}


def validate_image(file: UploadFile) -> int:
    """
    Validate image file size and type
    Returns file size in bytes
    """

    # Check file size
    file.file.seek(0, 2)  # Seek to end of file
    size = file.file.tell()  # Get file size
    file.file.seek(0)  # Reset file pointer

    if size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File size ({size/1024/1024:.2f}MB) exceeds maximum allowed size (5MB)",
        )

    # Check file type
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file.content_type} not allowed. Allowed types: {', '.join(ALLOWED_IMAGE_TYPES.keys())}",
        )

    # Check file extension
    file_ext = (
        f".{file.filename.split('.')[-1].lower()}" if "." in file.filename else ""
    )
    if not any(file_ext in exts for exts in ALLOWED_IMAGE_TYPES.values()):
        raise HTTPException(
            status_code=400, detail=f"File extension {file_ext} not allowed"
        )

    return size


@router.post("/upload/images", response_model=List[str])
async def upload_images(
    files: List[UploadFile] = File(...),
    s3: S3Service = Depends(get_s3_service),
    token: str = Depends(get_token),
):
    """
    Upload multiple image files

    - Maximum file size: 5MB per file
    - Maximum total size: 20MB
    - Maximum files: 10
    - Allowed types: JPEG, PNG, WebP, GIF
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    if len(files) > MAX_FILES:
        raise HTTPException(
            status_code=400, detail=f"Too many files. Maximum allowed: {MAX_FILES}"
        )

    # Check total size before processing files
    total_size = 0
    for file in files:
        try:
            size = validate_image(file)
            total_size += size

            if total_size > MAX_TOTAL_SIZE:
                raise HTTPException(
                    status_code=400,
                    detail=f"Total file size ({total_size/1024/1024:.2f}MB) exceeds maximum allowed size (20MB)",
                )
        except Exception:
            # Make sure to close files if validation fails
            for f in files:
                await f.close()
            raise

    image_urls = []

    for file in files:
        try:
            # Upload to S3
            file_url = await s3.upload_file(file=file, folder="public/images")

            image_urls.append(file_url)

        except HTTPException as e:
            # Re-raise HTTP exceptions with file name
            raise HTTPException(
                status_code=e.status_code,
                detail=f"Error with file {file.filename}: {e.detail}",
            )
        except Exception as e:
            # Handle unexpected errors
            raise HTTPException(
                status_code=500,
                detail=f"Error processing file {file.filename}: {str(e)}",
            )
        finally:
            # Always close the file
            await file.close()

    return image_urls


@router.delete("/images/{filename}")
async def delete_image(
    filename: str,
    s3: S3Service = Depends(get_s3_service),
    token: str = Depends(get_token),
):
    """Delete an image from storage"""
    try:
        await s3.delete_file(f"public/images/{filename}")
        return {"message": "File deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")
