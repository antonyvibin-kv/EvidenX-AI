import boto3
import logging
from typing import Optional, BinaryIO
from botocore.exceptions import ClientError, NoCredentialsError
from app.core.config import settings

logger = logging.getLogger(__name__)


class S3Service:
    """S3 service for file operations."""
    
    def __init__(self):
        try:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                region_name=settings.aws_region
            )
            self.bucket_name = settings.s3_bucket_name
        except NoCredentialsError:
            logger.error("AWS credentials not found")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            raise
    
    async def upload_file(
        self, 
        file_obj: BinaryIO, 
        object_name: str,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> dict:
        """Upload a file to S3."""
        try:
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type
            if metadata:
                extra_args['Metadata'] = metadata
            
            self.s3_client.upload_fileobj(
                file_obj, 
                self.bucket_name, 
                object_name,
                ExtraArgs=extra_args
            )
            
            # Generate presigned URL for the uploaded file
            url = self.generate_presigned_url(object_name)
            
            return {
                "success": True,
                "object_name": object_name,
                "url": url,
                "bucket": self.bucket_name
            }
            
        except ClientError as e:
            logger.error(f"Error uploading file to S3: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def download_file(self, object_name: str) -> Optional[bytes]:
        """Download a file from S3."""
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=object_name
            )
            return response['Body'].read()
        except ClientError as e:
            logger.error(f"Error downloading file from S3: {e}")
            return None
    
    def generate_presigned_url(
        self, 
        object_name: str, 
        expiration: int = 3600,
        http_method: str = 'GET'
    ) -> Optional[str]:
        """Generate a presigned URL for S3 object access."""
        try:
            response = self.s3_client.generate_presigned_url(
                ClientMethod='get_object',
                Params={'Bucket': self.bucket_name, 'Key': object_name},
                ExpiresIn=expiration,
                HttpMethod=http_method
            )
            return response
        except ClientError as e:
            logger.error(f"Error generating presigned URL: {e}")
            return None
    
    async def delete_file(self, object_name: str) -> bool:
        """Delete a file from S3."""
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=object_name
            )
            return True
        except ClientError as e:
            logger.error(f"Error deleting file from S3: {e}")
            return False
    
    async def list_files(self, prefix: str = "") -> list:
        """List files in S3 bucket with optional prefix."""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            files = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    files.append({
                        'key': obj['Key'],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'],
                        'etag': obj['ETag']
                    })
            
            return files
        except ClientError as e:
            logger.error(f"Error listing files from S3: {e}")
            return []


# Global S3 service instance
s3_service = S3Service()

