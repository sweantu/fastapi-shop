import boto3
from botocore.exceptions import ClientError
from fastapi import UploadFile, HTTPException
from app.core.config import settings
import uuid
from typing import Optional


class S3Service:
    def __init__(self):
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )
        self.bucket_name = settings.AWS_BUCKET_NAME

    async def upload_file(
        self, file: UploadFile, folder: str = "uploads", filename: Optional[str] = None
    ) -> str:
        """
        Upload a file to S3 bucket

        :param file: File to upload
        :param folder: Folder in bucket
        :param filename: Optional filename (if not provided, will generate UUID)
        :return: URL of uploaded file
        """
        try:
            # Generate unique filename if not provided
            if not filename:
                ext = file.filename.split(".")[-1] if "." in file.filename else ""
                filename = f"{uuid.uuid4()}.{ext}" if ext else str(uuid.uuid4())

            # Create full path
            path = f"{folder}/{filename}"

            # Upload file
            self.s3_client.upload_fileobj(
                file.file,
                self.bucket_name,
                path,
                ExtraArgs={"ContentType": file.content_type},
            )

            # Return file URL
            return f"{settings.AWS_BUCKET_URL}/{path}"

        except ClientError as e:
            raise HTTPException(
                status_code=500, detail=f"Error uploading file to S3: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error uploading file: {str(e)}"
            )

    async def delete_file(self, file_url: str) -> bool:
        """
        Delete a file from S3 bucket

        :param file_url: Full URL of the file to delete
        :return: True if successful
        """
        try:
            # Extract path from URL
            path = file_url.replace(f"{settings.AWS_BUCKET_URL}/", "")

            # Delete file
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=path)
            return True

        except ClientError as e:
            raise HTTPException(
                status_code=500, detail=f"Error deleting file from S3: {str(e)}"
            )
